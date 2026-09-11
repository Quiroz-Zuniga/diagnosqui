# Avance Fase 3 — Empaquetado PyInstaller

Fecha: 10/09/2026. Estado: completada.

## Qué se agregó

| Archivo | Propósito |
|---|---|
| `build_exe.spec` | Windows: `diagnosqui.exe` (terminal, consola) y `DiagnosQui-Escritorio.exe` (escritorio sin consola), onefile, con icono. Incluye datos del paquete GUI (QSS + iconos) y todos los subpaquetes. |
| `build_bin.spec` | Linux: `dist/diagnosqui` y `dist/diagnosqui-gui`, onefile ELF. |
| `tools/make_icon.py` | Genera `assets/icon.ico` con solo stdlib (PNG comprimido dentro de ICO). Sin binarios en el repositorio. |
| `tools/build.sh` / `tools/build.ps1` | Automatizan: icono → PyInstaller → reporte de `dist/`. |
| `docs/empaquetado.md` | Comandos, diferencia `.py` vs binario y notas por SO. |

## Verificación

- `assets/icon.ico` generado (1740 bytes) y con estructura ICO válida
  (cabecera, 1 imagen, offset correcto).
- `python -m py_compile tools/make_icon.py` → OK.
- `bash -n tools/build.sh` → OK.
- Los `.spec` se escribieron con la API estable de PyInstaller
  (`collect_data_files` / `collect_submodules`) y `SPECPATH` con rutas
  absolutas para no depender del directorio actual.

## Limitaciones

- PyInstaller no instalado en `requirements.txt` (dependencia de build
  opcional; `tools/build.sh`/`build.ps1` lo instalan si falta).
- No se ejecutó PyInstaller aquí; es un paso de build que se valida en el
  equipo de destino (Windows 10/11 y Linux con escritorio).