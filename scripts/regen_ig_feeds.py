#!/usr/bin/env python3
"""
regen_ig_feeds.py

Regenera APENAS as capas Instagram Feed (1080×1080) de todos os posts em
perspectivas-data.json. Use depois de mexer no layout da ig-feed em capas.py
(safe zone para o "novo grid" 4:5 do Instagram).

Os outros formatos (hero, og, ig-story) NÃO são tocados por este script.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "site" / "perspectivas-data.json"
CAPAS_PY = ROOT / "scripts" / "capas.py"


def main() -> int:
    if not DATA_PATH.exists():
        print(f"❌ {DATA_PATH} não encontrado", file=sys.stderr)
        return 1

    posts = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    slugs = [p["slug"] for p in posts]

    print(f"\n→ Regenerando capas ig-feed de {len(slugs)} posts:\n")

    erros: list[str] = []
    for slug in slugs:
        try:
            proc = subprocess.run(
                [sys.executable, str(CAPAS_PY), "--slug", slug, "--only", "ig-feed"],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=60,
            )
            if proc.returncode == 0:
                print(f"  ✓ {slug}")
            else:
                erros.append(slug)
                print(f"  ✗ {slug}\n    {proc.stderr.strip()}")
        except Exception as e:
            erros.append(slug)
            print(f"  ✗ {slug}: {e}")

    if erros:
        print(f"\n⚠️  Falhou em {len(erros)} posts: {', '.join(erros)}")
        return 1

    print(f"\n✓ {len(slugs)} ig-feeds regeneradas em site/assets/capas/")
    print("\nPróximos passos:")
    print("  1. Confere uma ig-feed nova (ex: contratar-gente-engajada-pequenas-e-medias-empresas_ig-feed.png)")
    print("  2. Se gostou, posta no Instagram pra validar como aparece no grid")
    print("  3. git add site/assets/capas/*_ig-feed.png && git commit && git push")
    return 0


if __name__ == "__main__":
    sys.exit(main())
