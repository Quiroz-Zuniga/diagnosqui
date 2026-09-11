# Checklist contra la rúbrica

Mapa entre los criterios de la rúbrica (25 pts) y su implementación real en el
repositorio. Verificado con la suite completa en verde (99 pruebas).

| Criterio | Pts | Dónde se cubre | Verificación |
|---|---|---|---|
| Investigación bibliotecas | 2 | `psutil`, `subprocess`, `platform`, `rich`, `textual`, `prompt_toolkit`, `PySide6`, `wmi`/`pywin32`, `PyInstaller` documentadas | `docs/informe_apa7.md` §2 y referencias; README |
| Menú | 2 | Terminal con menú numerado, historial y autocompletado | `cli.py`, `ui/terminal.py`; `tests/test_ui_workflow.py` |
| CPU/RAM | 2 | Recolección real + reglas | `core/cpu.py`, `core/memoria.py`, `analisis/reglas.py`, `analisis/recomendaciones.py` |
| Almacenamiento | 2 | Recolección real + reglas | `core/almacenamiento.py`, `analisis/recomendaciones.py` |
| USB/periféricos | 3 | Árbol de decisión del caso 3 | `core/usb.py`, `tests/test_casos_integradores.py::caso_usb_no_reconocido` |
| PCI/PCIe | 3 | Caso integrador 2 | `core/pci.py`, `tests/test_casos_integradores.py::caso_pcie_dispositivo_error` |
| Red | 3 | Conectividad + caso integrador 1 (APIPA) | `core/red.py`, `core/conectividad.py`, `tests/test_casos_integradores.py::caso_apipa` |
| GPU/controladores | 2 | Tarjetas, GPU y controladores (incl. `driverquery`) | `core/gpu.py`, `core/controladores.py` |
| Motor de análisis/recomendaciones | 2 | Umbrales 70/90, regla PnP, certeza baja, semáforo | `analisis/{reglas,recomendaciones,general}.py`; `tests/test_casos_integradores.py` (14) |
| Reportes | 1 | JSON/CSV/HTML y `.txt` | `core/reporte.py`, `core/report_exports.py`, pestaña GUI "Reportes" |
| Ejecutable | 1 | PyInstaller onefile terminal + GUI | `build_exe.spec`, `build_bin.spec`, `docs/empaquetado.md`, `assets/icon.ico` |
| Documentación APA 7 | 1 | Plantilla de informe | `docs/informe_apa7.md` |
| Presentación | 1 | Demo con menú + monitor tipo Task Manager | `docs/diagnosqui-desktop.png`, `docs/diagnosqui-monitor.png` |

## Módulo de optimización (bonificación en el plan)

| Ruleta del plan v2 (§8) | Implementación |
|---|---|
| Verificación Administrador | `optimizacion/safety.py` (`es_administrador`) |
| Confirmación `s/n` por acción | `optimizacion/safety.py::confirmar`; menú `optimizacion/menu_optimizacion.py` |
| Modo `--dry-run` | `optimizacion/temporales.py::limpiar_temporales`, `telemetria.py::aplicar_telemetria` |
| Log auditable | `logs/optimizacion.log` (`safety.py::registrar_log`) |
| Análisis de temporales `%TEMP%`, Windows\Temp, SoftwareDistribution | `optimizacion/temporales.py` |
| Telemetría reversible (AllowTelemetry, tareas, DiagTrack) y `revertir_*()` | `optimizacion/telemetria.py` |
| Pruebas | `tests/test_optimizacion.py` (13), todas con mocks (sin tocar Windows) |

## Evidencia de regresión

- `QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests` → 99 OK.
- `ruff check --select F,ISC` → sin errores.