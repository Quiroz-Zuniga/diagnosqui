# Plan de fases pendientes — DiagnosQui

Complementa `PLAN_DIAGNOSQUI_v2.md` (§11) con las etapas que aún no existían en el código.
Cada fase termina con su documento de avance en `docs/avance-fase-<n>.md` y se refleja en el README.

> **Estado final (10/09/2026): las 4 fases están completas y la suite
> completa pasa en verde (99 pruebas).**

## Estado inicial (contexto tomado el 10/09/2026)

- Recolección real en `core/` (CPU, memoria, discos, red+conectividad, USB, PCI, controladores, problemas, GPU, sistema) vía backends Windows/Linux. ✓
- GUI PySide6 con proveedores reales y monitor tipo Task Manager (Textual). ✓
- CLI de terminal con fixtures (contrato de 6 claves) y monitor en vivo real. ✓
- Reporte JSON/CSV/HTML (GUI). ✓

Pendientes detectados:

| # | Pendiente | Plan v2 § |
|---|---|---|
| 1 | Motor de reglas + recomendaciones (`analisis/`) y casos integradores | §5, §6, fase 2 |
| 2 | Módulo de optimización de Windows (`optimizacion/`) | §8, fase 4 |
| 3 | Empaquetado PyInstaller (specs + icono) | §9, fase 6 |
| 4 | Documentación (README, informe APA 7, checklist rúbrica) | fase 7 |
| 5 | Corregir 1 prueba GUI existente que falla (timers al cambiar tema) | — |

## Fase 1 — Motor de reglas y recomendaciones (`analisis/`)

- `analisis/reglas.py`: `analizar_estado(valor, tipo="porcentaje")` con umbrales 70/90 y regla PnP (OK/Warning/Unknown/Error). Puro, sin dependencias de `core`.
- `analisis/recomendaciones.py`: una función por dominio (cpu, memoria, disco, usb, pci, red, gpu, controladores, problemas, conectividad) que devuelve `{deteccion, diagnostico, certeza, recomendacion[]}` y `analizar_contrato()` que enriquece un contrato (nunca "sistema sin problemas" si hay síntoma → certeza baja, Caso 5).
- `analisis/general.py`: semáforo general a partir de contratos (`diagnostico_semaforo`) + manejo explícito del síntoma reportado por el usuario.
- `tests/test_casos_integradores.py`: los 5 casos integradores del enunciado + cobertura de `reglas`.
- CLI: comando `recomendaciones` (13) pasa por el motor (sobre fixtures, sin consultar hardware).

## Fase 2 — Optimización de Windows (`optimizacion/`)

- `optimizacion/safety.py`: verificación de Administrador, confirmaciones `s/n`, modo `--dry-run`, log auditable `logs/optimizacion.log`.
- `optimizacion/temporales.py`: escaneo y limpieza de `%TEMP%`, `C:\Windows\Temp`, SoftwareDistribution (opcional), papelera (confirmación aparte); siempre reversible y con dry-run.
- `optimizacion/telemetria.py`: estado actual + acciones oficiales reversibles (AllowTelemetry, tareas programadas, servicio DiagTrack) con `revertir_*()`.
- `optimizacion/menu_optimizacion.py`: flujo interactivo (escanear → resumen → confirmar → aplicar → registrar). Conectado a la opción 16 solo en Windows.
- `tests/test_optimizacion.py` (dry-run y limpieza con directorios temporales; telemetría con mocks).

## Fase 3 — Empaquetado PyInstaller

- `build_exe.spec` (Windows) y `build_bin.spec` (Linux): onefile para terminal y GUI.
- `assets/icon.ico` generado por `tools/make_icon.py` (solo stdlib, sin binarios en git).
- `docs/empaquetado.md` con los comandos y diferencia `.py` vs binario.
- README actualizado.

## Fase 4 — Documentación y cierre  ✅

- `docs/informe_apa7.md`: plantilla de informe académico (sección 38). ✅
- `docs/checklist-rubrica.md`: mapa rúbrica → implementación real. ✅
- README actualizado (opción 16 real, motor, empaquetado, estado de pruebas). ✅
- Corregir la prueba GUI de timers que falla y volver a correr la suite completa. ✅
  (Causa: `QTimer` interno de `QStatusBar` recreado por Qt al cambiar paleta;
  el test cuenta ahora solo temporizadores de `Controller`/`MainWindow`.)
- Suite completa: 72 → 99 pruebas, todas en verde. ✅