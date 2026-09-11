#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="${DIAGNOSQUI_VENV:-$HOME/.diagnosqui-venv}"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: instala Python 3.9 o posterior."
    exit 1
fi
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else "Se requiere Python 3.9 o posterior")'

echo "Configurando DiagnosQui (escritorio y terminal) en $VENV_PATH..."
python3 -m venv "$VENV_PATH"
"$VENV_PATH/bin/python" -m pip install --upgrade pip
"$VENV_PATH/bin/python" -m pip install -e "$SCRIPT_DIR"

BIN_DIR="/usr/local/bin"
for launcher in diagnosqui diagnosqui-gui; do
    if [ -w "$BIN_DIR" ]; then
        ln -sf "$VENV_PATH/bin/$launcher" "$BIN_DIR/$launcher"
    elif command -v sudo >/dev/null 2>&1; then
        sudo ln -sf "$VENV_PATH/bin/$launcher" "$BIN_DIR/$launcher" ||
            echo "Puedes ejecutar directamente: $VENV_PATH/bin/$launcher"
    fi
done

echo "Instalación completada."
echo "Escritorio: $VENV_PATH/bin/diagnosqui-gui"
echo "Escritorio independiente de terminal: $VENV_PATH/bin/diagnosqui-gui --detach"
echo "Terminal: $VENV_PATH/bin/diagnosqui"
