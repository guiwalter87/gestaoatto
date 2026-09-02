#!/usr/bin/env python3
"""
seo_internal_links.py

Mantém a malha de links internos das Perspectivas em HTML ESTÁTICO
(o que o Googlebot lê sem depender de JS).

Motivação (auditoria SEO 2026-09-02): os posts criados a partir de junho/2026
saíram sem o bloco `.post-nav` e o fallback estático do grid em
site/perspectivas.html ficou congelado em maio. Resultado: 4 posts ficaram
"Detectada, mas não indexada" no Search Console por falta de links internos
estáticos apontando para eles.

Este script é idempotente e faz duas coisas:

  1. rebuild_post_nav()
     Para todos os posts publicados (data <= hoje BRT) em perspectivas-data.json,
     garante que exista `<div class="post-nav">` no post-footer e recalcula
     "← Post anterior / Próximo post →" pela ordem cronológica.

  2. render_static_feed()
     Regenera o bloco <!-- POSTS:FEED_START --> ... <!-- POSTS:FEED_END --> em
     site/perspectivas.html com TODOS os posts publicados (mais recente primeiro),
     com a mesma marcação que assets/perspectivas-grid.js produz no cliente.
     O JS continua sobrescrevendo o bloco em runtime; o estático é o que o
     crawler vê primeiro.

Uso:
  python3 scripts/seo_internal_links.py            # usa data de hoje (BRT)
  python3 scripts/seo_internal_links.py 2026-09-02 # simula data específica

Também é chamado ao final de scripts/publish_scheduled.py.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SITE = REPO_ROOT / "site"
PERSPECTIVAS_HTML = SITE / "perspectivas.html"
PERSPECTIVAS_DIR = SITE / "perspectivas"
DATA_JSON = SITE / "perspectivas-data.json"

FEED_MARK_START = "<!-- POSTS:FEED_START -->"
FEED_MARK_END = "<!-- POSTS:FEED_END -->"

MESES_PT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
            "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

# Mesmo mapeamento visual usado nos cards estáticos originais.
TAG_CLASS = {
    "Performance": "img-blue",
    "Direção": "img-dark",
    "Governança": "img-teal",
    "M&A": "img-roxo",
    "M&amp;A": "img-roxo",
    "Pessoas": "img-paper",
    "Sucessão": "img-warm",
    "Indústria": "img-teal",
}

AUTHOR_RE = re.compile(r'<meta name="author" content="([^"]+)"')
POST_NAV_RE = re.compile(r'<div class="post-nav">.*?</div>', re.DOTALL)
NOINDEX_RE = re.compile(r'<meta name="robots" content="noindex')


def today_brt(argv: list[str]) -> date:
    if len(argv) > 1:
        return datetime.strptime(argv[1], "%Y-%m-%d").date()
    return (datetime.now(timezone.utc) - timedelta(hours=3)).date()


def load_published(today: date) -> list[dict]:
    """Posts com data <= hoje, cujo HTML existe e não está com noindex agendado.
    Ordenados do mais antigo para o mais recente."""
    data = json.loads(DATA_JSON.read_text(encoding="utf-8"))
    out = []
    for p in data:
        if not p.get("slug") or not p.get("data"):
            continue
        if datetime.strptime(p["data"], "%Y-%m-%d").date() > today:
            continue
        path = PERSPECTIVAS_DIR / f"{p['slug']}.html"
        if not path.exists():
            continue
        html = path.read_text(encoding="utf-8")
        if NOINDEX_RE.search(html):
            continue
        p = dict(p)
        m = AUTHOR_RE.search(html)
        p["autor"] = p.get("autor") or (f"Por {m.group(1)}" if m else "")
        out.append(p)
    return sorted(out, key=lambda x: x["data"])


def esc(s: str) -> str:
    return str(s or "").replace('"', "&quot;")


def html_amp(s: str) -> str:
    """Escapa & solto (não parte de entidade) para &amp;."""
    return re.sub(r"&(?![a-zA-Z#][a-zA-Z0-9]*;)", "&amp;", str(s or ""))


# ---------------------------------------------------------------------------
# 1) post-nav
# ---------------------------------------------------------------------------
def build_nav(prev: dict | None, nxt: dict | None) -> str:
    if prev:
        prev_html = (f'<a href="{prev["slug"]}.html">'
                     f'<span class="lab">← Post anterior</span>'
                     f'<span class="t">{html_amp(prev["titulo"])}</span></a>')
    else:
        prev_html = "<span></span>"
    if nxt:
        next_html = (f'<a href="{nxt["slug"]}.html">'
                     f'<span class="lab">Próximo post →</span>'
                     f'<span class="t">{html_amp(nxt["titulo"])}</span></a>')
    else:
        next_html = "<span></span>"
    return f'<div class="post-nav">{prev_html}{next_html}</div>'


def ensure_nav_placeholder(html: str) -> tuple[str, bool]:
    """Insere um post-nav vazio logo após o author-block do post-footer,
    caso o post tenha saído do template sem ele."""
    if POST_NAV_RE.search(html):
        return html, False
    # Fim do author-block: primeiro </div>\n    </div> após 'class="author-block"'
    idx = html.find('class="author-block"')
    if idx == -1:
        return html, False
    # Encontra o fechamento do author-block (div aberto -> 3 níveis internos)
    # Estratégia simples e segura: procurar o próximo "\n      </div>\n" após idx
    m = re.compile(r'\n      </div>\n', re.DOTALL).search(html, idx)
    if not m:
        return html, False
    insert_at = m.end()
    placeholder = '      <div class="post-nav"><span></span><span></span></div>\n'
    return html[:insert_at] + placeholder + html[insert_at:], True


def rebuild_post_nav(posts: list[dict]) -> list[str]:
    changed: list[str] = []
    for i, post in enumerate(posts):
        prev = posts[i - 1] if i > 0 else None
        nxt = posts[i + 1] if i + 1 < len(posts) else None
        path = PERSPECTIVAS_DIR / f"{post['slug']}.html"
        html = path.read_text(encoding="utf-8")
        original = html
        html, _ = ensure_nav_placeholder(html)
        html, n = POST_NAV_RE.subn(build_nav(prev, nxt), html, count=1)
        if n == 0:
            print(f"AVISO: sem post-footer/author-block em {post['slug']}, nav não inserido",
                  file=sys.stderr)
            continue
        if html != original:
            path.write_text(html, encoding="utf-8")
            changed.append(post["slug"])
    return changed


# ---------------------------------------------------------------------------
# 2) fallback estático do grid
# ---------------------------------------------------------------------------
def render_card(p: dict) -> str:
    y, m, _ = p["data"].split("-")
    month_year = f"{MESES_PT[int(m) - 1]} · {y}"
    tag_class = p.get("tag_class") or TAG_CLASS.get(p.get("categoria", ""), "img-teal")
    autor = p.get("autor", "")
    return (
        f'      <a href="perspectivas/{p["slug"]}.html" class="persp-card" data-publish-date="{esc(p["data"])}">\n'
        f'        <div class="persp-card-img {tag_class}" style="background-image:url(\'assets/capas/{p["slug"]}_hero.png\');'
        f'background-size:cover;background-position:center"><span class="tag">{html_amp(p["categoria"])}</span></div>\n'
        f'        <div class="persp-card-meta"><span>{html_amp(p.get("leitura", ""))}</span><span>{month_year}</span></div>\n'
        f'        <h3>{html_amp(p["titulo"])}</h3>\n'
        f'        <p>{html_amp(p.get("excerpt", ""))}</p>\n'
        + (f'        <span class="author">{html_amp(autor)}</span>\n' if autor else "")
        + '      </a>\n'
    )


def render_static_feed(posts: list[dict]) -> bool:
    text = PERSPECTIVAS_HTML.read_text(encoding="utf-8")
    start = text.find(FEED_MARK_START)
    end = text.find(FEED_MARK_END)
    if start == -1 or end == -1:
        raise RuntimeError("Marcadores POSTS:FEED_START/END não encontrados em perspectivas.html")
    newest_first = sorted(posts, key=lambda x: x["data"], reverse=True)
    block = (
        f"{FEED_MARK_START}\n"
        "      <!-- ⚠️ FONTE ÚNICA: cards renderizados por assets/perspectivas-grid.js a partir\n"
        "           de perspectivas-data.json. O bloco abaixo é o fallback ESTÁTICO (o que o\n"
        "           Googlebot lê primeiro) e é regenerado por scripts/seo_internal_links.py\n"
        "           a cada publicação. Não editar à mão. -->\n"
        + "".join(render_card(p) for p in newest_first)
        + "      "
    )
    new_text = text[:start] + block + text[end:]
    if new_text != text:
        PERSPECTIVAS_HTML.write_text(new_text, encoding="utf-8")
        return True
    return False


def run(today: date | None = None) -> None:
    today = today or today_brt(sys.argv)
    posts = load_published(today)
    changed = rebuild_post_nav(posts)
    feed_changed = render_static_feed(posts)
    print(f"[seo_internal_links] posts publicados: {len(posts)} | "
          f"post-nav atualizado em {len(changed)} | "
          f"fallback estático {'regenerado' if feed_changed else 'sem mudança'}")
    for s in changed:
        print(f"  nav: {s}")


if __name__ == "__main__":
    run()
