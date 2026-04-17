#!/usr/bin/env bash
# Sincroniza o conteúdo de /site deste repo para o repo gestaoatto-preview
# que alimenta a URL https://guiwalter87.github.io/gestaoatto-preview/
#
# Uso: bash scripts/sync_preview.sh "mensagem do commit"
# (se omitir a mensagem, usa data/hora)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREVIEW="${ROOT}/../gestaoatto-preview"

if [ ! -d "$PREVIEW/.git" ]; then
  echo "✗ Repo de preview não encontrado em $PREVIEW"
  echo "  Clone-o primeiro: git clone https://github.com/guiwalter87/gestaoatto-preview.git $PREVIEW"
  exit 1
fi

MSG="${1:-Sincronizacao $(date '+%d/%m/%Y %H:%M')}"

echo "→ Espelhando $ROOT/site/ em $PREVIEW/"
# --exclude CNAME: pra preview não redirecionar pro WIX
# --delete: remove arquivos que não existem mais no origem
rsync -a --delete \
  --exclude='.git/' \
  --exclude='.DS_Store' \
  --exclude='CNAME' \
  "$ROOT/site/" "$PREVIEW/"

# Garante que README e .git/ do preview não sejam apagados
cd "$PREVIEW"
git add -A

if git diff --cached --quiet; then
  echo "· Nada pra sincronizar (preview já está igual ao main)"
  exit 0
fi

git commit -m "$MSG"
git push origin main
echo "✓ Preview atualizado: https://guiwalter87.github.io/gestaoatto-preview/"
