#!/usr/bin/env python3
"""
Migra o site da Atto de gtag.js direto para Google Tag Manager + Consent Mode v2.

Para cada página viva (com o snippet gtag) em site/:
  1. Substitui o bloco gtag por: data layer da página (page_family, vertical_atto,
     article_section, article_author) + consent default (denied) + leitura da
     escolha salva + snippet GTM.
  2. Garante <noscript> do GTM logo após <body>.
  3. Garante <script defer> de atto-events.js e atto-consent.js.
  4. Adiciona link "Cookies" (data-cookie-prefs) no rodapé legal.

Idempotente: pode rodar de novo sem duplicar nada.
Uso:  python3 scripts/migrar_gtm.py [--dry-run]
"""
import re
import sys
from pathlib import Path

GTM_ID = "GTM-N495GLWN"
ROOT = Path(__file__).resolve().parent.parent / "site"
DRY = "--dry-run" in sys.argv

GTAG_BLOCK = re.compile(
    r"(?:<!--\s*Google tag \(gtag\.js\)\s*-->\s*)?"
    r"<script async src=\"https://www\.googletagmanager\.com/gtag/js\?id=G-PTS41WC8HS\"></script>\s*"
    r"<script>.*?gtag\('config',\s*'G-PTS41WC8HS'\);\s*</script>\s*",
    re.S,
)
EVENTS_TAG = re.compile(r"<script defer src=\"(\.\./)?assets/atto-events\.js\"></script>\s*")
CONSENT_TAG = re.compile(r"<script defer src=\"(\.\./)?assets/atto-consent\.js\"></script>\s*")
DL_BLOCK = re.compile(r"<!-- Atto · Data Layer -->.*?<!-- End Google Tag Manager -->\s*", re.S)
NOSCRIPT = re.compile(r"\s*<!-- Google Tag Manager \(noscript\) -->.*?<!-- End Google Tag Manager \(noscript\) -->", re.S)


def js_str(s):
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


def classify(rel):
    """Retorna (page_family, vertical_atto) a partir do caminho relativo."""
    p = rel.replace("\\", "/")
    name = p.split("/")[-1].replace(".html", "")
    if p.startswith("perspectivas/"):
        return "perspectiva", "Perspectivas"
    fam = {
        "index": "home",
        "404": "erro",
        "contato": "conversao",
        "metodo": "metodo", "atuacao": "metodo",
        "diagnostico-90-dias": "servico", "rotina-mensal": "servico", "rqs": "servico",
        "direcao-estrategica": "servico", "performance-financeira": "servico",
        "pessoas-lideranca": "servico", "governanca-ma": "servico",
        "contratacao-estrategica": "servico",
        "industria-manufatura": "setor", "comercio-distribuicao": "setor",
        "sobre": "institucional", "time": "institucional", "clientes": "institucional",
        "perspectivas": "editorial", "newsletter": "editorial",
        "trabalhe-conosco": "carreiras", "vagas": "carreiras",
        "politica-privacidade": "legal", "termos-uso": "legal",
    }.get(name, "outro")
    n = name.lower()
    if re.search(r"direcao|metodo|atuacao|diagnostico|rotina", n):
        vert = "Direção"
    elif re.search(r"performance|rqs", n):
        vert = "Performance Financeira"
    elif re.search(r"pessoas|lideranca", n):
        vert = "Gente & Gestão"
    elif re.search(r"governanca|m-?a$", n):
        vert = "Governança & M&A"
    elif "contratacao" in n:
        vert = "Contratação Estratégica"
    elif n in ("perspectivas", "newsletter"):
        vert = "Perspectivas"
    else:
        vert = None
    return fam, vert


def meta(html, name):
    m = re.search(r'<meta\s+(?:name|property)="' + re.escape(name) + r'"\s+content="([^"]*)"', html)
    return m.group(1).strip() if m else None


def head_block(rel, html):
    fam, vert = classify(rel)
    section = meta(html, "article:section")
    author = meta(html, "article:author")
    slug = rel.split("/")[-1].replace(".html", "") if rel.startswith("perspectivas/") else None
    pairs = ["page_family: " + js_str(fam)]
    if vert:
        pairs.append("vertical_atto: " + js_str(vert))
    if section:
        pairs.append("article_section: " + js_str(section))
    if author:
        pairs.append("article_author: " + js_str(author))
    if slug:
        pairs.append("article_slug: " + js_str(slug))
    dl = ", ".join(pairs)
    return f"""<!-- Atto · Data Layer -->
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){{dataLayer.push(arguments);}}
gtag('consent', 'default', {{analytics_storage:'denied', ad_storage:'denied', ad_user_data:'denied', ad_personalization:'denied', functionality_storage:'granted', security_storage:'granted', wait_for_update:500}});
gtag('set', 'ads_data_redaction', true);
try {{ var c = JSON.parse(localStorage.getItem('atto_consent') || 'null'); if (c && c.ts && (Date.now() - c.ts) < 31536000000 && c.analytics === 'granted') {{ gtag('consent', 'update', {{analytics_storage:'granted'}}); }} }} catch (e) {{}}
dataLayer.push({{{dl}}});
</script>
<!-- Google Tag Manager -->
<script>(function(w,d,s,l,i){{w[l]=w[l]||[];w[l].push({{'gtm.start':
new Date().getTime(),event:'gtm.js'}});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
}})(window,document,'script','dataLayer','{GTM_ID}');</script>
<!-- End Google Tag Manager -->
"""


def noscript_block():
    return (f'\n<!-- Google Tag Manager (noscript) -->\n<noscript><iframe src="https://www.googletagmanager.com/ns.html?id={GTM_ID}" '
            f'height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>\n'
            f'<!-- End Google Tag Manager (noscript) -->')


def migrate(path):
    rel = str(path.relative_to(ROOT))
    html = path.read_text(encoding="utf-8")
    orig = html
    prefix = "../" if rel.startswith("perspectivas/") else ""

    # 1. head: remove blocos antigos e insere o novo antes de </head>
    html = DL_BLOCK.sub("", html)
    html = GTAG_BLOCK.sub("", html)
    html = EVENTS_TAG.sub("", html)
    html = CONSENT_TAG.sub("", html)
    scripts = (f'<script defer src="{prefix}assets/atto-events.js"></script>\n'
               f'<script defer src="{prefix}assets/atto-consent.js"></script>\n')
    html = html.replace("</head>", head_block(rel, html) + scripts + "</head>", 1)

    # 2. noscript após <body>
    html = NOSCRIPT.sub("", html)
    html = re.sub(r"(<body[^>]*>)", lambda m: m.group(1) + noscript_block(), html, count=1)

    # 3. rodapé legal: corrige links quebrados (href="#") e adiciona link de cookies
    html = html.replace('<a href="#">Política de privacidade</a>', f'<a href="{prefix}politica-privacidade.html">Política de privacidade</a>')
    html = html.replace('<a href="#">Termos</a>', f'<a href="{prefix}termos-uso.html">Termos</a>')
    if "data-cookie-prefs" not in html:
        html = re.sub(
            r'(<a href="(?:\.\./)?termos-uso\.html">[^<]*</a>)',
            r'\1 · <a href="#" data-cookie-prefs>Cookies</a>',
            html, count=1,
        )

    changed = html != orig
    if changed and not DRY:
        path.write_text(html, encoding="utf-8")
    return changed


def main():
    files = sorted(p for p in ROOT.rglob("*.html")
                   if "_to_delete" not in p.parts and not re.search(r" [23](\.html|/)", str(p)))
    live = [p for p in files if "G-PTS41WC8HS" in p.read_text(encoding="utf-8", errors="ignore")
            or "<!-- Atto · Data Layer -->" in p.read_text(encoding="utf-8", errors="ignore")]
    n = 0
    for p in live:
        if migrate(p):
            n += 1
            print(("[dry] " if DRY else "✓ ") + str(p.relative_to(ROOT)))
    print(f"\n{n}/{len(live)} páginas {'seriam' if DRY else 'foram'} atualizadas.")


if __name__ == "__main__":
    main()
