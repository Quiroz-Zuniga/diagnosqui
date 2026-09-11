#!/usr/bin/env bash
# Empaqueta DiagnosQui como binarios ELF (PyInstaller onefile).
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="${DIAGNOSQUI_VENV:-$HOME/.diagnosqui-venv}"
PYTHON="$VENV_PATH/bin/python"

if [ ! -x "$PYTHON" ]; then
    PYTHON="python3"
fi

if [ ! -x "$SCRIPT_DIR/../.venv/bin/python" ]; then
    echo "Aviso: no se encontró .venv/.; se usará $PYTHON"
else
    PYTHON="$SCRIPT_DIR/../.venv/bin/python"
fi

"$PYTHON" -m pip show pyinstaller >/dev/null 2>&1 || {
    echo "Instalando PyInstaller..."
    "$PYTHON" -m pip install pyinstaller
}

"$PYTHON" "$SCRIPT_DIR/make_icon.py"
"$PYTHON" -m PyInstaller --clean --noconfirm "$SCRIPT_DIR/../build_bin.spec"

echo "Binarios generados en dist/:"
ls -1 "$SCRIPT_DIR/../dist/" 2>/dev/null || true