# Avance Fase 1 — Motor de reglas y recomendaciones

Fecha: 10/09/2026. Estado: completada.

## Qué se agregó

Nuevo paquete `diagnosqui/analisis/`, autocontenido (solo stdlib, sin
dependencias de la capa de recolección para poder usarse desde la terminal
sin cargar hardware):

| Archivo | Responsabilidad |
|---|---|
| `analisis/reglas.py` | Umbrales centrales 70/90 (`analizar_estado`), regla PnP Windows (`clasificar_pnp`), severidad combinada (`estado_mas_severo`), limpieza de alias (`traducir_estado`). |
| `analisis/recomendaciones.py` | Una función por dominio (`recomendacion_cpu`, `_memoria`, `_disco`, `_usb`, `_pci`, `_red`, `_conectividad`, `_gpu`, `_controladores`, `_problemas`), patrón DETECCIÓN → DIAGNÓSTICO → SOLUCIÓN, con campo `certeza`. `analizar_contrato()` enriquece un contrato conservando las 6 claves; `analizar_conjunto()` para listas. |
| `analisis/general.py` | `diagnostico_semaforo()` (semáforo general) y `generar_json_general()` (estructura de la sección 30 del enunciado). |

Reglas de certeza implementadas:
- Indicadores OK + síntoma del usuario → `certeza: baja` y petición de
  diagnóstico adicional (caso integrador 5). Nunca declara "sin problemas".
- Error reportado por PnP → `certeza: alta`.
- Inferencia por umbrales → `certeza: media`.

## Integración en CLI

`cli.diagnostic_provider()` ahora enruta los comandos **1 (general)** y
**13 (recomendaciones)** por el motor con `analizar_conjunto` sobre los
fixtures (sin consultar hardware; la CLI conserva su diseño de datos de
prueba). Esto no rompe la restricción de no importar `core` en el flujo de
la terminal (`tests/test_ui_workflow.py::test_cli_import_and_fixture_command_do_not_load_core`).

## Pruebas

- `tests/test_casos_integradores.py`: 14 pruebas, todas pasan. Cubre:
  - **Caso 1** (APIPA/DHCP): estado CRÍTICO, certeza alta, sugiere
    `ipconfig /release` y `/renew` (solo imprime el comando, no lo ejecuta).
  - **Caso 2** (tarjeta PCIe con error): falla aislada al dispositivo, no
    "falla general del sistema".
  - **Caso 3** (USB no reconocido): árbol conexión → controlador → disco,
    recomendación probar otro puerto/cable.
  - **Caso 4** (CPU 97 %, RAM 91 %): semáforo CRÍTICO, 2 errores
    detectados, recomendación de revisar procesos.
  - **Caso 5** (ambiguo): indicadores OK + síntoma → certeza baja y
    diagnóstico adicional solicitado.
  - Reglas unitarias (umbrales 70/90, PnP, severidad).

## Verificación

- `python -m unittest tests.test_casos_integradores` → OK (14).
- `python -m unittest tests.test_ui tests.test_ui_workflow` → OK (32).
- `diagnosqui --command recomendaciones` muestra recomendaciones del motor.
- `ruff --select F,ISC` → sin errores en los archivos nuevos.

## Pendiente / notas

- El paso a proveedores reales desde la CLI queda reservado al
  `diagnostic_provider`; la GUI ya usa los recolectores reales.