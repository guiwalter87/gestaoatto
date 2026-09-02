#!/usr/bin/env python3
"""
publish_scheduled.py

Ativa posts da pasta site/perspectivas/ cuja publish_date no
scripts/scheduled_posts.json seja menor ou igual à data corrente (BRT).
O script é idempotente: posts já publicados são ignorados em execuções
subsequentes.

Operações por post ativado:
  1. Remove `<meta name="robots" content="noindex,nofollow"><!-- SCHEDULED:DATE -->`
     do HTML do post em site/perspectivas/<slug>.html. (libera indexação)
  2. Garante que o HTML carrega `assets/atto-events.js` (tracker GA4 custom).
     Sem isso, scroll-90 / whatsapp_click / cta_agendar não são medidos.
  3. Insere URL no site/sitemap.xml dentro do bloco
     <!-- SCHEDULED-SITEMAP-START --> ... <!-- SCHEDULED-SITEMAP-END -->.
  4. Atualiza todos os <lastmod> do sitemap para a data de hoje
     (evita lastmod stale, fresh signals para o Google).
  5. Atualiza a navegação cronológica (post-nav) entre o post atual e o anterior.
  6. Atualiza o bloco "Em destaque" (POSTS:FEATURE) em site/perspectivas.html.

⚠️ A inserção do card no grid de perspectivas.html foi REMOVIDA.
O grid agora é renderizado dinamicamente por assets/perspectivas-grid.js
a partir de perspectivas-data.json (mesma fonte da home), o que elimina
o descompasso histórico quando o cron desta action atrasava ou falhava.

Uso:
  python3 scripts/publish_scheduled.py            # usa data de hoje
  python3 scripts/publish_scheduled.py 2026-05-16 # simula data específica

Saída:
  - imprime "Published: <slug>" para cada post ativado
  - imprime "No changes." se nada mudou
  - exit 0 sempre (workflow decide se commita pelo git status)
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent  # raiz do repo
SITE = REPO_ROOT / "site"                            # subpasta de deploy
PERSPECTIVAS_HTML = SITE / "perspectivas.html"
SITEMAP = SITE / "sitemap.xml"
PERSPECTIVAS_DIR = SITE / "perspectivas"
DATA_JSON = SITE / "perspectivas-data.json"
REGISTRY = REPO_ROOT / "scripts" / "scheduled_posts.json"

SITEMAP_MARK_START = "<!-- SCHEDULED-SITEMAP-START"
SITEMAP_MARK_END = "<!-- SCHEDULED-SITEMAP-END -->"
FEATURE_MARK_START = "<!-- POSTS:FEATURE_START -->"
FEATURE_MARK_END = "<!-- POSTS:FEATURE_END -->"

NOINDEX_RE = re.compile(
    r'\n<meta name="robots" content="noindex,nofollow"><!-- SCHEDULED:[\d\-]+ -->\n'
)

# SEO hygiene: garantir que toda perspectiva carrega o tracker custom
ATTO_EVENTS_SCRIPT = '<script defer src="../assets/atto-events.js"></script>'
ATTO_EVENTS_SENTINEL = 'atto-events.js'
GTAG_CONFIG_LINE = "gtag('config', 'G-PTS41WC8HS');"

# Mapeamento categoria → mês curto (também em scheduled_posts.json)
MES_CURTO = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
             7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}


def today_brt() -> date:
    if len(sys.argv) > 1:
        try:
            return datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
        except ValueError:
            print(f"Argumento inválido (use YYYY-MM-DD): {sys.argv[1]}", file=sys.stderr)
            sys.exit(2)
    brt = timezone(timedelta(hours=-3))
    return datetime.now(brt).date()


def load_registry() -> list[dict]:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return data["scheduled"]



def sitemap_url_html(post: dict) -> str:
    return (
        "  <url>\n"
        f"    <loc>https://www.gestaoatto.com.br/perspectivas/{post['slug']}.html</loc>\n"
        f"    <lastmod>{post['publish_date']}</lastmod>\n"
        "    <priority>0.7</priority>\n"
        "  </url>"
    )



def is_sitemap_present(sitemap_text: str, slug: str) -> bool:
    return f"perspectivas/{slug}.html" in sitemap_text



def insert_sitemap(sitemap_text: str, post: dict) -> str:
    start_idx = sitemap_text.find(SITEMAP_MARK_START)
    if start_idx == -1:
        raise RuntimeError("SITEMAP_MARK_START não encontrado em site/sitemap.xml")
    eol = sitemap_text.find("\n", start_idx)
    block = sitemap_url_html(post)
    return (
        sitemap_text[: eol + 1]
        + block
        + "\n"
        + sitemap_text[eol + 1 :]
    )


def remove_noindex(post_html: str) -> str:
    return NOINDEX_RE.sub("\n", post_html, count=1)


def ensure_atto_events_js(post_html: str) -> tuple[str, bool]:
    """Garante que o HTML carrega o atto-events.js logo após o snippet do GA4.

    Retorna (html_atualizado, foi_alterado).
    """
    if ATTO_EVENTS_SENTINEL in post_html:
        return post_html, False
    # Site migrado para GTM (ago/2026): insere após o snippet do GTM.
    # Mantém fallback para o snippet gtag antigo, se algum post legado aparecer.
    scripts = ATTO_EVENTS_SCRIPT + '\n<script defer src="../assets/atto-consent.js"></script>\n<script defer src="../assets/atto-whatsapp.js"></script>\n'
    if "<!-- End Google Tag Manager -->" in post_html:
        new_html = post_html.replace("<!-- End Google Tag Manager -->", "<!-- End Google Tag Manager -->\n" + scripts, 1)
        return new_html, True
    pattern = re.compile(
        r"(\s*gtag\('config',\s*'G-PTS41WC8HS'\);\s*\n</script>\s*\n)",
        re.IGNORECASE,
    )
    new_html, count = pattern.subn(r"\1" + scripts, post_html, count=1)
    return new_html, count > 0


def bump_sitemap_lastmod(sitemap_text: str, today_iso: str) -> str:
    """Atualiza o lastmod APENAS das páginas que realmente mudam quando um
    post é publicado: a home (feed) e perspectivas.html (grid/destaque).

    Auditoria 2026-09-02: o bump global anterior marcava todas as 44 URLs
    com a mesma data a cada publicação. O Google documenta que passa a
    ignorar <lastmod> quando ele não reflete mudança real de conteúdo, o que
    anulava o sinal justamente para os posts novos. Agora o sinal é seletivo.
    """
    def _bump(url: str, text: str) -> str:
        pat = re.compile(
            r"(<loc>" + re.escape(url) + r"</loc>\s*<lastmod>)\d{4}-\d{2}-\d{2}(</lastmod>)"
        )
        return pat.sub(rf"\g<1>{today_iso}\g<2>", text)

    for url in ("https://www.gestaoatto.com.br/",
                "https://www.gestaoatto.com.br/perspectivas.html"):
        sitemap_text = _bump(url, sitemap_text)
    return sitemap_text


def find_previous_published(slug: str) -> dict | None:
    """Encontra o post publicado anterior ao slug atual, baseado em
    perspectivas-data.json (que está ordenado mais recente → mais antigo).

    O post anterior é o IMEDIATAMENTE seguinte no JSON (porque está em ordem
    descendente), excluindo posts que ainda têm noindex.
    """
    if not DATA_JSON.exists():
        return None
    data = json.loads(DATA_JSON.read_text(encoding="utf-8"))
    found_idx = None
    for i, p in enumerate(data):
        if p["slug"] == slug:
            found_idx = i
            break
    if found_idx is None:
        return None
    # Procura o próximo no JSON (que é cronologicamente anterior)
    for p in data[found_idx + 1:]:
        post_path = PERSPECTIVAS_DIR / f"{p['slug']}.html"
        if post_path.exists() and "SCHEDULED:" not in post_path.read_text(encoding="utf-8"):
            return p
    return None


def update_post_nav(slug: str, prev_slug: str | None, prev_title: str | None,
                    next_slug: str | None, next_title: str | None) -> bool:
    """Atualiza o post-nav de um post HTML existente.

    `<a><...prev_slug...>` para o anterior; `<span></span>` se não houver next.
    """
    post_path = PERSPECTIVAS_DIR / f"{slug}.html"
    if not post_path.exists():
        return False
    html = post_path.read_text(encoding="utf-8")

    # Constrói o novo post-nav
    if prev_slug and prev_title:
        prev_html = (
            f'<a href="{prev_slug}.html">'
            f'<span class="lab">← Post anterior</span>'
            f'<span class="t">{prev_title}</span></a>'
        )
    else:
        prev_html = "<span></span>"
    if next_slug and next_title:
        next_html = (
            f'<a href="{next_slug}.html">'
            f'<span class="lab">Próximo post →</span>'
            f'<span class="t">{next_title}</span></a>'
        )
    else:
        next_html = "<span></span>"

    new_nav = f'<div class="post-nav">{prev_html}{next_html}</div>'

    # Substitui o bloco
    pattern = re.compile(r'<div class="post-nav">.*?</div>', re.DOTALL)
    new_html, n = pattern.subn(new_nav, html, count=1)
    if n == 0:
        return False
    if new_html != html:
        post_path.write_text(new_html, encoding="utf-8")
        return True
    return False


def update_feature_block(text: str, post: dict) -> str:
    """Atualiza o bloco POSTS:FEATURE_START..END em site/perspectivas.html
    para destacar o post mais recente. Recebe e retorna o texto em memória
    (não escreve em disco) para não conflitar com inserções pendentes do card.
    """
    start = text.find(FEATURE_MARK_START)
    end = text.find(FEATURE_MARK_END)
    if start == -1 or end == -1:
        return text

    pdate = datetime.strptime(post["publish_date"], "%Y-%m-%d").date()
    mes_curto = MES_CURTO[pdate.month]
    ano = pdate.year
    slug = post["slug"]
    titulo = post["h3"]
    excerpt = post["summary"]
    cat = post["tag"]
    minutes = post["minutes"]

    new_block = (
        f"{FEATURE_MARK_START}\n"
        f'    <div class="persp-feature-grid">\n'
        f'      <div class="persp-feature-body">\n'
        f'        <div class="kicker" style="font-family:\'JetBrains Mono\',monospace;font-size:11px;letter-spacing:.15em;text-transform:uppercase">Em destaque · {mes_curto} · {ano}</div>\n'
        f'        <div class="meta">\n'
        f'          <span>{cat}</span>\n'
        f'          <span>{mes_curto} · {ano}</span>\n'
        f'          <span>{minutes} min de leitura</span>\n'
        f'        </div>\n'
        f'        <h2>{titulo}</h2>\n'
        f'        <p class="excerpt">{excerpt}</p>\n'
        f'        <a href="perspectivas/{slug}.html" class="btn-primary" style="display:inline-flex;align-items:center">Ler a tese completa <span class="arrow" style="margin-left:12px">→</span></a>\n'
        f'      </div>\n'
        f'      <a href="perspectivas/{slug}.html" style="display:block">\n'
        f'        <div class="persp-feature-img" style="background-image:url(\'assets/capas/{slug}_hero.png\')"></div>\n'
        f'      </a>\n'
        f'    </div>\n'
        f'    '
    )
    new_text = text[:start] + new_block + text[end:]
    return new_text


def main() -> int:
    today = today_brt()
    registry = load_registry()

    perspectivas_text = PERSPECTIVAS_HTML.read_text(encoding="utf-8")
    sitemap_text = SITEMAP.read_text(encoding="utf-8")

    published: list[str] = []
    skipped: list[str] = []

    # Ordenar por data crescente, para que cards inseridos na sequência fiquem
    # com o mais recente no topo (cada inserção empurra o anterior pra baixo).
    for post in sorted(registry, key=lambda p: p["publish_date"]):
        slug = post["slug"]
        pdate = datetime.strptime(post["publish_date"], "%Y-%m-%d").date()
        post_path = PERSPECTIVAS_DIR / f"{slug}.html"

        if pdate > today:
            skipped.append(f"{slug} (agendado para {pdate})")
            continue

        if not post_path.exists():
            print(f"AVISO: arquivo {post_path} não existe — pulando {slug}", file=sys.stderr)
            continue

        # NOTE: já não verificamos `already_in_index` (card no grid) porque o
        # grid passou a ser renderizado dinamicamente. O critério de publicação
        # agora depende apenas do sitemap + remoção do noindex.
        already_in_sitemap = is_sitemap_present(sitemap_text, slug)
        post_html = post_path.read_text(encoding="utf-8")
        has_noindex = bool(NOINDEX_RE.search(post_html))

        if already_in_sitemap and not has_noindex:
            skipped.append(f"{slug} (já publicado)")
            continue

        # 1. Remove noindex do post + garante higiene SEO (atto-events.js)
        html_alterado = False
        if has_noindex:
            post_html = remove_noindex(post_html)
            html_alterado = True
        post_html, events_added = ensure_atto_events_js(post_html)
        if events_added:
            html_alterado = True
        if html_alterado:
            post_path.write_text(post_html, encoding="utf-8")

        # 2. Insere URL no sitemap (a inserção do card foi removida —
        # agora o grid é dinâmico via assets/perspectivas-grid.js)
        if not already_in_sitemap:
            sitemap_text = insert_sitemap(sitemap_text, post)

        # 3. Atualiza navegação cronológica:
        #    a) Post atual: prev = post publicado anterior, next = nenhum
        #    b) Post anterior: ganha "Próximo post → post atual"
        prev = find_previous_published(slug)
        if prev:
            update_post_nav(
                slug,
                prev_slug=prev["slug"],
                prev_title=prev.get("titulo", ""),
                next_slug=None,
                next_title=None,
            )
            # Atualiza o post anterior para apontar próximo = este
            # (mantém o prev dele intacto)
            prev_path = PERSPECTIVAS_DIR / f"{prev['slug']}.html"
            if prev_path.exists():
                prev_html = prev_path.read_text(encoding="utf-8")
                # Extrai o prev atual do post anterior pra preservar
                m = re.search(
                    r'<div class="post-nav"><a href="([^"]+)\.html"><span class="lab">← Post anterior</span><span class="t">([^<]+)</span></a>',
                    prev_html,
                )
                pp_slug = m.group(1) if m else None
                pp_title = m.group(2) if m else None
                update_post_nav(
                    prev["slug"],
                    prev_slug=pp_slug,
                    prev_title=pp_title,
                    next_slug=slug,
                    next_title=post.get("h3", ""),
                )

        # 4. Atualiza o bloco "Em destaque" para o post mais recente.
        # update_feature_block agora opera só em memória — a persistência
        # acontece no bloco final, junto com o card e o sitemap.
        perspectivas_text = update_feature_block(perspectivas_text, post)

        published.append(slug)

    # Persiste sempre que houve qualquer publicação
    if published:
        # Higiene SEO: bump em todos os <lastmod> para a data corrente,
        # garantindo que o Google receba "fresh signals" do site inteiro.
        sitemap_text = bump_sitemap_lastmod(sitemap_text, today.isoformat())
        PERSPECTIVAS_HTML.write_text(perspectivas_text, encoding="utf-8")
        SITEMAP.write_text(sitemap_text, encoding="utf-8")

        # 5. Malha de links internos ESTÁTICA (post-nav de todos os posts +
        #    fallback estático do grid). Sem isso, posts novos só ficam
        #    linkados via JS e o Google demora a indexar (auditoria 2026-09-02).
        try:
            sys.path.insert(0, str(REPO_ROOT / "scripts"))
            import seo_internal_links  # noqa: E402
            seo_internal_links.run(today)
        except Exception as exc:  # não derruba a publicação por causa disso
            print(f"AVISO: seo_internal_links falhou: {exc}", file=sys.stderr)

        for slug in published:
            print(f"Published: {slug}")
    else:
        print("No changes.")

    if skipped:
        for s in skipped:
            print(f"Skipped:   {s}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
