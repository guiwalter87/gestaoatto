#!/usr/bin/env python3
"""
Injeta scroll-progress + site.js em todas as páginas que usam assets/site.css.
Idempotente: se já tem, pula.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"

PROGRESS_DIV = '<div class="scroll-progress" aria-hidden="true"></div>'

def inject(path: Path):
    html = path.read_text(encoding="utf-8")
    changed = False

    # Calcula caminho relativo do site.js (subpastas precisam de ../)
    depth = len(path.relative_to(SITE).parts) - 1
    js_path = ("../" * depth) + "assets/site.js"
    script_tag = f'<script src="{js_path}" defer></script>'

    # 1. Scroll progress — injeta logo após <body>
    if 'class="scroll-progress"' not in html:
        html_new = re.sub(
            r'(<body[^>]*>)',
            r'\1\n\n' + PROGRESS_DIV,
            html,
            count=1
        )
        if html_new != html:
            html = html_new
            changed = True

    # 2. site.js — injeta antes de </body>
    if 'src="' + js_path + '"' not in html and 'site.js' not in html.split('</body>')[0]:
        html_new = html.replace(
            '</body>',
            script_tag + '\n</body>',
            1
        )
        if html_new != html:
            html = html_new
            changed = True

    if changed:
        path.write_text(html, encoding="utf-8")
        print(f"  ✓ {path.relative_to(ROOT)}")
    else:
        print(f"  · {path.relative_to(ROOT)} (ja tinha)")

def main():
    files = [p for p in SITE.rglob("*.html") if 'assets/site.css' in p.read_text(encoding="utf-8")]
    # Pula o index.html — já tem tudo inline
    files = [p for p in files if p.name != "index.html"]
    print(f"→ Injetando em {len(files)} arquivos\n")
    for p in files:
        inject(p)
    print(f"\n✓ Concluido.")

if __name__ == "__main__":
    main()
