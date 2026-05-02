#!/bin/bash
# Atto Studio launcher (macOS)
#
# Você pode dar duplo-clique aqui ou em qualquer cópia deste arquivo
# (ex: na sua Desktop). Os caminhos abaixo são absolutos, então funciona
# mesmo movido. Se você um dia mudar a pasta do projeto, edite a linha
# STUDIO_DIR abaixo.

set -e

# === LOCALIZAÇÃO CANÔNICA DO ATTO STUDIO ====================================
# (caminho absoluto — sobrevive a cópias / atalhos)
STUDIO_DIR="/Users/guilhermewalter/Documents/Claude/Projects/Site da Atto/site/scripts/atto_studio"
REPO_ROOT="/Users/guilhermewalter/Documents/Claude/Projects/Site da Atto/site"
# ============================================================================

# Banner
clear
cat <<'EOF'

   █████╗ ████████╗████████╗ ██████╗
  ██╔══██╗╚══██╔══╝╚══██╔══╝██╔═══██╗
  ███████║   ██║      ██║   ██║   ██║   Studio · Perspectivas
  ██╔══██║   ██║      ██║   ██║   ██║   ────────────────────
  ██║  ██║   ██║      ██║   ╚██████╔╝   versão 1.0.1
  ╚═╝  ╚═╝   ╚═╝      ╚═╝    ╚═════╝

EOF

# Sanity check
if [[ ! -f "$STUDIO_DIR/app.py" ]]; then
  echo "❌ Não achei o Atto Studio em:"
  echo "    $STUDIO_DIR/app.py"
  echo ""
  echo "Esse caminho está hardcoded no início deste arquivo."
  echo "Se você moveu o projeto, edite a linha STUDIO_DIR no script."
  echo ""
  read -p "Pressione Enter para fechar."
  exit 1
fi

echo "Pasta do repo:  $REPO_ROOT"
echo "Atto Studio:    $STUDIO_DIR"
echo

cd "$REPO_ROOT"

# Acha o python disponível
if command -v python3 &>/dev/null; then
  PY=python3
elif command -v python &>/dev/null; then
  PY=python
else
  echo "❌ Python 3 não encontrado. Instale via Homebrew (brew install python) ou App Store."
  read -p "Pressione Enter para fechar."
  exit 1
fi
echo "Python:         $($PY --version)"

# Verifica/instala dependências
echo
echo "Verificando dependências..."
if ! $PY -c "import flask, markdown" 2>/dev/null; then
  echo "  Instalando flask + markdown..."
  $PY -m pip install --user --quiet flask markdown 2>&1 | tail -3 || {
    echo "  Tentativa com --break-system-packages..."
    $PY -m pip install --user --break-system-packages --quiet flask markdown 2>&1 | tail -3
  }
fi
echo "  OK."

# Sobe o servidor e abre o Safari
PORT=8765
URL="http://127.0.0.1:$PORT"

echo
echo "Subindo servidor em $URL ..."
echo "(Ctrl+C aqui para parar)"
echo

# Abre o browser depois de 2s
( sleep 2 && open "$URL" ) &

# Roda Flask em foreground — Ctrl+C aqui derruba tudo
exec "$PY" "$STUDIO_DIR/app.py"
