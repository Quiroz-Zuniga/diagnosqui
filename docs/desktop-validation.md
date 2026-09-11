# Validación del escritorio DiagnosQui

Fecha: 10 de septiembre de 2026. Entorno: Linux, Python 3.14.6, PySide6 6.11.2.

## Resultados comprobados

| Comprobación | Resultado |
| --- | --- |
| Estado inicial | 44 pruebas: 41 aprobadas y 3 errores anteriores en adaptadores de prueba de core |
| Suite final | 60 pruebas aprobadas, 8.013 segundos |
| GUI headless | Construcción, 15 páginas, navegación, procesos, gráficas y errores controlados |
| Trabajo en segundo plano | Se comprueba ejecución fuera del hilo principal, controles durante tareas y cierre con una lectura pendiente |
| Reportes | JSON, CSV y HTML; origen fixture explícito, escape HTML, errores de exportación y conservación del resumen |
| Ventana real en Linux | Apertura a 1280×720 y 1360×900; 10 proveedores consultados; 5 muestras en la última captura; salida 0 |
| Procesos con psutil | 4 procesos accesibles en la prueba aislada; 4 muestras; salida 0 |
| Lanzador gráfico instalado | Ejecutado en offscreen, con cierre programado; salida 0 |
| Terminal instalada | `diagnosqui --command cpu` muestra su fixture y termina con salida 0 |
| Paquetes | Wheels de ambos pyproject.toml construidos sin descargar dependencias; QSS y tres entry points comprobados |
| Nombres de ejecutables | Sin colisiones al ignorar mayúsculas, como ocurre normalmente en Windows |
| Dependencias | `pip check`: sin dependencias incompatibles |
| Código | Ruff F: sin errores; sintaxis Python 3.9 comprobada en los 28 archivos Python de implementación nuevos |
| Instalador Linux | `bash -n install.sh`: correcto; no se ejecutó la instalación global |
| Diferencias | `git diff --check`: sin errores de espacios |

Las 16 pruebas nuevas se encuentran en `tests/test_gui.py`. Los avisos de asyncio emitidos por Textual durante las pruebas no son fallos. El mensaje sobre no poder guardar el estado de inicio corresponde a una prueba de error intencionado de la terminal.

## Decisiones

- La GUI consume los recolectores existentes mediante un servicio; no duplica diagnósticos ni llama a funciones `show_*()`.
- La telemetría se extrajo del monitor Textual a `core/telemetry.py`, preservando las importaciones públicas anteriores. Ambos monitores comparten cálculo de tasas y CPU por proceso.
- Se usan dos pools acotados: diagnóstico/exportación y telemetría. Las tareas se cancelan cooperativamente al cerrar, esperando la lectura en curso sin destruir sus widgets antes de tiempo.
- Las gráficas se dibujan con QPainter y almacenan como máximo 60 muestras. No se añadió pyqtgraph.
- El pyproject de la raíz es el canónico. El de la subcarpeta mantiene instalación alternativa compatible, con las mismas dependencias, extras y entry points.
- El alias gráfico es `DiagnosQui-Escritorio`: el nombre propuesto `DiagnosQui.exe` colisiona con `diagnosqui.exe` en Windows. Se preserva `diagnosqui` para terminal y `diagnosqui-gui` como lanzador gráfico principal.
- Se actualizaron los adaptadores de tres pruebas antiguas de core que llamaban a una firma inexistente de la matriz. Se conservan sus escenarios y aserciones.

## Alcance y limitaciones

Windows 10/11 y Python 3.9 son objetivos de compatibilidad, pero no se ejecutaron en este entorno. La comprobación de sintaxis e importaciones no sustituye esas pruebas de ejecución. El instalador PowerShell y el comportamiento del lanzador sin consola requieren validación en Windows. Tampoco se verificó una matriz de escalados de pantalla o compositores Linux.

Las capturas usan datos reales. El estado crítico mostrado procede de las incidencias devueltas por el backend existente; no constituye una confirmación independiente de avería. Las limitaciones de permisos y disponibilidad se presentan como resultados parciales. La CLI conserva sus fixtures de diagnóstico.

Los instaladores se revisaron sin modificar la instalación global del usuario. Las wheels de prueba se construyeron en directorios temporales que se eliminaron al terminar. No se hicieron commits ni se alteraron los cambios que ya estaban preparados en Git.

## Reproducir la suite

Desde la raíz del repositorio, con el paquete instalado:

```bash
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v
python -m pip check
diagnosqui --command cpu
diagnosqui-gui --help
```

Consulta el [README](../README.md) para la instalación y el inicio en Linux y Windows.

## Capturas

- [Inicio](diagnosqui-desktop.png)
- [Monitor](diagnosqui-monitor.png)

## Archivos creados

- `diagnosqui/src/diagnosqui/gui/__init__.py`
- `diagnosqui/src/diagnosqui/gui/app.py`
- `diagnosqui/src/diagnosqui/gui/controller.py`
- `diagnosqui/src/diagnosqui/gui/main_window.py`
- `diagnosqui/src/diagnosqui/gui/pages/__init__.py`
- `diagnosqui/src/diagnosqui/gui/pages/component_page.py`
- `diagnosqui/src/diagnosqui/gui/pages/dashboard_page.py`
- `diagnosqui/src/diagnosqui/gui/pages/monitor_page.py`
- `diagnosqui/src/diagnosqui/gui/pages/problems_page.py`
- `diagnosqui/src/diagnosqui/gui/pages/processes_page.py`
- `diagnosqui/src/diagnosqui/gui/pages/reports_page.py`
- `diagnosqui/src/diagnosqui/gui/pages/settings_page.py`
- `diagnosqui/src/diagnosqui/gui/services/__init__.py`
- `diagnosqui/src/diagnosqui/gui/services/contracts.py`
- `diagnosqui/src/diagnosqui/gui/services/diagnostic_service.py`
- `diagnosqui/src/diagnosqui/gui/services/telemetry_service.py`
- `diagnosqui/src/diagnosqui/gui/styles/dark.qss`
- `diagnosqui/src/diagnosqui/gui/theme.py`
- `diagnosqui/src/diagnosqui/gui/widgets/__init__.py`
- `diagnosqui/src/diagnosqui/gui/widgets/chart_widget.py`
- `diagnosqui/src/diagnosqui/gui/widgets/common.py`
- `diagnosqui/src/diagnosqui/gui/widgets/diagnostic_table.py`
- `diagnosqui/src/diagnosqui/gui/widgets/metric_card.py`
- `diagnosqui/src/diagnosqui/gui/widgets/sidebar_button.py`
- `diagnosqui/src/diagnosqui/gui/widgets/status_badge.py`
- `diagnosqui/src/diagnosqui/gui/workers.py`
- `diagnosqui/src/diagnosqui/gui_cli.py`
- `diagnosqui/src/diagnosqui/core/telemetry.py`
- `diagnosqui/src/diagnosqui/core/report_exports.py`
- `tests/test_gui.py`
- `docs/diagnosqui-desktop.png`
- `docs/diagnosqui-monitor.png`
- `docs/desktop-validation.md`

## Archivos modificados en esta implementación gráfica

- `README.md`
- `pyproject.toml`
- `diagnosqui/pyproject.toml`
- `requirements.txt`
- `install.sh`
- `install.ps1`
- `diagnosqui/src/diagnosqui/backends/windows_backend.py`
- `diagnosqui/src/diagnosqui/core/reporte.py`
- `diagnosqui/src/diagnosqui/ui/monitor_tui.py`
- `tests/test_core.py`
