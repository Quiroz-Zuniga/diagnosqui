# Empaquetado como ejecutable (PyInstaller)

DiagnosQui se entrega también como binario autocontenido (onefile) para
Windows y Linux. Esto cumple el requisito de "ejecutable" del enunciado:
el `.exe` / binario ELF ya trae el intérprete de Python y las dependencias
empaquetadas, y no requiere un entorno virtual ni instalación previa de
paquetes.

## Diferencia entre `python` y el binario

| Uso | Requiere | Resultado |
|---|---|---|
| `python -m diagnosqui.cli` / `diagnosqui` (script pip) | Python ≥ 3.9 y paquetes instalados | Ejecuta desde el código fuente |
| `dist/diagnosqui` / `dist/diagnosqui.exe` | Nada (autocontenido) | Binario generado por PyInstaller |

## Requisito previo

Instalar PyInstaller en el entorno virtual:

```bash
source .venv/bin/activate
python -m pip install pyinstaller
```

## Linux (binarios ELF)

```bash
tools/build.sh
# o manualmente:
python tools/make_icon.py
pyinstaller --clean --noconfirm build_bin.spec
```

Genera en `dist/`:
- `diagnosqui` (terminal)
- `diagnosqui-gui` (escritorio PySide6)

```bash
./dist/diagnosqui --command cpu
./dist/diagnosqui-gui
```

## Windows (`.exe`)

```powershell
.\tools\build.ps1
# o manualmente:
python tools/make_icon.py
pyinstaller --clean --noconfirm build_exe.spec
```

Genera en `dist\`:
- `diagnosqui.exe` (terminal, consola)
- `DiagnosQui-Escritorio.exe` (escritorio, sin consola; `gui-scripts`)

```powershell
.\dist\diagnosqui.exe --command cpu
Start-Process .\dist\DiagnosQui-Escritorio.exe
```

## Icono

`assets/icon.ico` se genera con `tools/make_icon.py` (solo la biblioteca
estándar de Python: código PNG + empaquetado ICO, sin Pillow). El repositorio
no requiere binarios: puede regenerarse con `python tools/make_icon.py`.

## Especificaciones

- `build_exe.spec` — Windows (terminal + escritorio, onefile, con icono).
- `build_bin.spec` — Linux (terminal + escritorio, onefile, con icono).
- `tools/build.sh` / `tools/build.ps1` — automatizan icono + PyInstaller.

Notas:
- Ambos `.spec` empaquetan `diagnosqui.gui` (QSS e iconos SVG) mediante
  `collect_data_files` e incluyen todos los subpaquetes con
  `collect_submodules("diagnosqui")` (incluye `analisis` y `optimizacion`).
- El empaquetado en Windows debe validarse en un equipo Windows 10/11;
  la construcción Linux se puede verificar con el propio entorno del proyecto.