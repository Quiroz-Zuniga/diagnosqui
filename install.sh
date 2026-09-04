#!/usr/bin/env bash
set -e

echo "=========================================="
echo "      Instalador de DiagnosQui (Linux)     "
echo "=========================================="

VENV_PATH="$HOME/.diagnosqui-venv"

if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 no está instalado."
    exit 1
fi

echo "-> Configurando entorno virtual en $VENV_PATH..."
python3 -m venv "$VENV_PATH"

echo "-> Actualizando pip e instalando dependencias..."
"$VENV_PATH/bin/pip" install --upgrade pip
"$VENV_PATH/bin/pip" install -e .

BIN_DIR="/usr/local/bin"
if [ -w "$BIN_DIR" ]; then
    ln -sf "$VENV_PATH/bin/diagnosqui" "$BIN_DIR/diagnosqui"
    echo "-> Enlace creado en $BIN_DIR/diagnosqui"
else
    echo "-> Intentando crear enlace simbólico con sudo..."
    sudo ln -sf "$VENV_PATH/bin/diagnosqui" "$BIN_DIR/diagnosqui" || {
        echo "Aviso: Agrega $VENV_PATH/bin a tu variable PATH si no deseas usar sudo."
    }
fi

echo ""
echo "¡Instalación completada exitosamente!"
echo "Ejecuta: diagnosqui"
