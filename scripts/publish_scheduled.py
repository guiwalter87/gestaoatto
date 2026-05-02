#!/usr/bin/env python3
"""
publish_scheduled.py

Ativa posts da pasta site/perspectivas/ cuja publish_date no
scripts/scheduled_posts.json seja menor ou igual à data corrente (BRT).
O script é idempotente: posts já publicados são ignorados em execuções
subsequentes.

Operações por post ativado:
  1. Remove `<meta name="robots" content="noindex,nofollow"><!-- SCHEDULED:DATE -->`
     do HTML do post em site/perspectivas/<slug>.html.
  2. Insere card no site/perspectivas.html dentro do bloco
     <!-- SCHEDULED-POSTS-START --> ... <!-- SCHEDULED-POSTS-END -->
     (em ordem cronológica reversa: post mais novo no topo).
  3. Insere URL no site/sitemap.xml dentro do bloco
     <!-- SCHEDULED-SITEMAP-START --> ... <!-- SCHEDULED-SITEMAP-END -->.

O cartão segue o padrão da grade publicada (âncora com background-image
apontando pra capa hero gerada por scripts/capas.py).

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
REGISTRY = REPO_ROOT / "scripts" / "scheduled_posts.json"

CARD_MARK_START = "<!-- SCHEDULED-POSTS-START"
CARD_MARK_END = "<!-- SCHEDULED-POSTS-END -->"
SITEMAP_MARK_START = "<!-- SCHEDULED-SITEMAP-START"
SITEMAP_MARK_END = "<!-- SCHEDULED-SITEMAP-END -->"

NOINDEX_RE = re.compile(
    r'\n<meta name="robots" content="noindex,nofollow"><!-- SCHEDULED:[\d\-]+ -->\n'
)


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


def card_html(post: dict) -> str:
    """Gera o cartão no formato da grade publicada (âncora com background-image
    apontando pra capa hero gerada por scripts/capas.py).
    """
    slug = post["slug"]
    return (
        f'      <a href="perspectivas/{slug}.html" class="persp-card" '
        f'data-publish-date="{post["publish_date"]}">\n'
        f'        <div class="persp-card-img {post["tag_class"]}" '
        f"style=\"background-image:url('assets/capas/{slug}_hero.png');"
        f'background-size:cover;background-position:center"><span class="tag">{post["tag"]}</span></div>\n'
        f'        <div class="persp-card-meta"><span>{post["minutes"]} min</span><span>{post["month"]} · {post["year"]}</span></div>\n'
        f'        <h3>{post["h3"]}</h3>\n'
        f'        <p>{post["summary"]}</p>\n'
        f'        <span class="author">{post["author"]}</span>\n'
        f"      </a>"
    )


def sitemap_url_html(post: dict) -> str:
    return (
        "  <url>\n"
        f"    <loc>https://www.gestaoatto.com.br/perspectivas/{post['slug']}.html</loc>\n"
        f"    <lastmod>{post['publish_date']}</lastmod>\n"
        "    <priority>0.7</priority>\n"
        "  </url>"
    )


def is_card_present(perspectivas_text: str, slug: str) -> bool:
    return f"perspectivas/{slug}.html" in perspectivas_text


def is_sitemap_present(sitemap_text: str, slug: str) -> bool:
    return f"perspectivas/{slug}.html" in sitemap_text


def insert_card(perspectivas_text: str, post: dict) -> str:
    """Insere o card logo após a linha do START marker (post mais novo no topo)."""
    start_idx = perspectivas_text.find(CARD_MARK_START)
    if start_idx == -1:
        raise RuntimeError("CARD_MARK_START não encontrado em site/perspectivas.html")
    eol = perspectivas_text.find("\n", start_idx)
    block = card_html(post)
    return (
        perspectivas_text[: eol + 1]
        + block
        + "\n"
        + perspectivas_text[eol + 1 :]
    )


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

        already_in_index = is_card_present(perspectivas_text, slug)
        already_in_sitemap = is_sitemap_present(sitemap_text, slug)
        post_html = post_path.read_text(encoding="utf-8")
        has_noindex = bool(NOINDEX_RE.search(post_html))

        if already_in_index and already_in_sitemap and not has_noindex:
            skipped.append(f"{slug} (já publicado)")
            continue

        # 1. Remove noindex do post
        if has_noindex:
            post_html = remove_noindex(post_html)
            post_path.write_text(post_html, encoding="utf-8")

        # 2. Insere card
        if not already_in_index:
            perspectivas_text = insert_card(perspectivas_text, post)

        # 3. Insere URL no sitemap
        if not already_in_sitemap:
            sitemap_text = insert_sitemap(sitemap_text, post)

        published.append(slug)

    # Persiste sempre que houve qualquer publicação
    if published:
        PERSPECTIVAS_HTML.write_text(perspectivas_text, encoding="utf-8")
        SITEMAP.write_text(sitemap_text, encoding="utf-8")
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
