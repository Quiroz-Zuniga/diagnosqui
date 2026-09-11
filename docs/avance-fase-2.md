# Avance Fase 2 — Optimización de Windows

Fecha: 10/09/2026. Estado: completada.

## Qué se agregó

Nuevo paquete `diagnosqui/optimizacion/`:

| Archivo | Responsabilidad |
|---|---|
| `optimizacion/safety.py` | Privilegios (`es_administrador`), confirmaciones `s/n` (`confirmar`), directorio de estado por usuario, log auditable `logs/optimizacion.log` (`registrar_log`), y `procesos_consumidores` como referencia de procesos de alto consumo. |
| `optimizacion/temporales.py` | `escanear_temporales`, `resumen_temporales`, `limpiar_temporales(dry_run=...)` y `contrato_estado`. Rutas: `%TEMP%`, `C:\Windows\Temp`, `SoftwareDistribution\Download`. En Linux usa `/tmp` y `~/.cache` (para pruebas/verificación, no modifica Windows). Nunca fuerza archivos en uso o sin permisos (se omiten y se reportan). |
| `optimizacion/telemetria.py` | `consultar_estado`, `aplicar_telemetria(dry_run)`, `revertir_telemetria(dry_run)`. Mecanismos oficiales y reversibles: registro `AllowTelemetry` (0 Seguridad), tareas programadas Compatibility Appraiser y CEIP Consolidator, servicio `DiagTrack`. Cada acción tiene su comando de reversión. Fuera de Windows: solo lectura ("No disponible"), nunca ejecuta. |
| `optimizacion/menu_optimizacion.py` | Flujo interactivo seguro: verifica Windows + Administrador, muestra resumen de temporales, tabla de telemetría, pide confirmación por acción y registra en el log. |

## Reglas de seguridad respetadas (plan §8)

1. Nada se ejecuta automáticamente; todo inicia desde la opción 16.
2. Requiere Administrador; si no lo está, avisa y termina sin intentar cambios.
3. Antes de cambiar algo se muestra el plan y se pide `s/n`.
4. Cada acción queda en `logs/optimizacion.log` con fecha y resultado.
5. Toda acción de telemetría tiene su `revertir_*` documentado e implementado.

## Integración CLI

La opción **16** ahora ejecuta `diagnosqui.optimizacion.menu_optimizacion` en
Windows (antes era solo un fixture). Se añadió el parámetro inyectable
`optimization_runner` a `dispatch_command`/`run_interactive_shell` (mismo
patrón que `monitor_runner`) para pruebas herméticas. En Linux conserva el
aviso "Optimización disponible solo en Windows".

## Pruebas

- `tests/test_optimizacion.py`: 13 pruebas, todas pasan.
  - Safety: ruta de log configurable, log auditable, confirmaciones s/n.
  - Temporales: escaneo, resumen, dry-run sin borrar, limpieza efectiva,
    contrato con las 6 claves.
  - Telemetría: solo lectura fuera de Windows; dry-run en Windows simulado
    con mocks (no ejecuta PowerShell).
  - Menú: rechazo sin administrador y fuera de Windows; dispatch 16 Linux vs
    Windows con runner inyectado.

## Verificación

- `python -m unittest tests.test_optimizacion tests.test_ui` → OK (37).
- `ruff --select F,ISC` → sin errores.

## Notas y limitaciones

- La rama Windows real (PowerShell/registro/tareas) no pudo ejecutarse en
  este entorno Linux; la lógica está cubierta con mocks y pendiente de
  validación en Windows 10/11.
- `menu_optimizacion` depende de `psutil` para la referencia de procesos.