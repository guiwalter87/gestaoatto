#!/bin/bash
# Cópia rápida do launcher Atto Studio para a Área de Trabalho do usuário.
# Execute uma única vez, dando duplo-clique nele.

set -e

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/Atto Studio.command"
DEST_DIR="$HOME/Desktop"
DEST="$DEST_DIR/Atto Studio.command"

if [[ ! -f "$SRC" ]]; then
  echo "❌ Não achei o launcher em $SRC"
  read -p "Pressione Enter para fechar."
  exit 1
fi

cp "$SRC" "$DEST"
chmod +x "$DEST"

# macOS marca arquivos baixados como suspeitos; remove o atributo de quarentena
xattr -d com.apple.quarantine "$DEST" 2>/dev/null || true

cat <<EOF

✅ Pronto. O atalho foi copiado para a sua Área de Trabalho.

   $DEST

A partir de agora basta dar duplo-clique no "Atto Studio" da Desktop
para abrir a central de Perspectivas.

EOF

read -p "Pressione Enter para fechar."
