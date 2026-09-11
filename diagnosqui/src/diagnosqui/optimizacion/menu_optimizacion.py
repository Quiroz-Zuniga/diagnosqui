"""
Menú interactivo de optimización de Windows (opción 16).

Flujo seguro:
1. Verifica plataforma y privilegios de Administrador.
2. Escanea temporales y muestra el resumen (cantidad y tamaño).
3. Muestra tabla de telemetría (acción / estado actual / estado propuesto).
4. Pide confirmación ``s/n`` antes de cada acción.
5. Registra cada acción en ``logs/optimizacion.log``.

Inyectables de prueba: ``confirmar_fn`` y ``output`` (Rich Console).
"""
from __future__ import annotations

from typing import Callable, Optional

from rich.table import Table

from diagnosqui.optimizacion.safety import (
    confirmar,
    es_administrador,
    estado_del_sistema,
    procesos_consumidores,
    registrar_log,
)
from diagnosqui.optimizacion.telemetria import aplicar_telemetria, consultar_estado
from diagnosqui.optimizacion.temporales import limpiar_temporales, resumen_temporales
from diagnosqui.ui.theme import (
    CRITICAL_STYLE,
    NORMAL_STYLE,
    WARNING_STYLE,
    console,
    print_header,
)


def _formatear_bytes(total: int) -> str:
    for unidad in ("B", "KB", "MB", "GB"):
        if total < 1024 or unidad == "GB":
            return f"{total:.2f} {unidad}" if unidad != "B" else f"{total} {unidad}"
        total /= 1024
    return f"{total:.2f} GB"


def _tabla_telemetria(filas) -> Table:
    tabla = Table(title="[bold white]Telemetría: cambios previstos[/bold white]", border_style="bright_blue")
    tabla.add_column("ACCIÓN", style="bold cyan")
    tabla.add_column("ESTADO ACTUAL", ratio=2)
    tabla.add_column("ESTADO PROPUESTO", ratio=2)
    for fila in filas:
        aplicable = fila.get("aplicable", False)
        actual = str(fila.get("estado_actual", "N/D"))
        propuesto = str(fila.get("estado_propuesto", "N/D"))
        if not aplicable:
            actual += " · [muted](no aplica en este equipo)[/muted]"
        tabla.add_row(fila.get("accion", "N/D"), actual, propuesto)
    return tabla


def run_optimizacion(
    *,
    confirmar_fn: Optional[Callable[[str], bool]] = None,
    output=None,
) -> int:
    """Ejecuta el flujo interactivo de optimización; devuelve 0 si terminó."""
    pantalla = output or console
    pantalla.print()
    print_header("Optimización de Windows", "Módulo 16 / Temporales + Telemetría")

    sistema = estado_del_sistema()
    if sistema["plataforma"] != "Windows":
        pantalla.print(
            "La optimización de Windows solo está disponible en Windows.",
            style=WARNING_STYLE,
        )
        return 1

    if not es_administrador():
        pantalla.print(
            "Se requiere ejecutar DiagnosQui como Administrador para optimizar. "
            "No se intentará ningún cambio.",
            style=CRITICAL_STYLE,
        )
        return 1

    aceptar = confirmar_fn or confirmar

    # 1. Temporales
    resumen = resumen_temporales()
    total = resumen["total_archivos"]
    pantalla.print(f"[bold]Temporales[/bold] · {total:,} archivos ({_formatear_bytes(resumen['bytes_totales'])}).")
    if resumen["por_ruta"]:
        tabla = Table(box=None, padding=(0, 2))
        tabla.add_column("Carpeta", style="cyan")
        tabla.add_column("Tamaño", justify="right")
        for carpeta, tamano in sorted(resumen["por_ruta"].items(), key=lambda item: item[1], reverse=True):
            tabla.add_row(carpeta, _formatear_bytes(tamano))
        pantalla.print(tabla)

    if total > 0:
        prevision = limpiar_temporales(resumen["archivos"], dry_run=True)
        pantalla.print(
            f"Se liberarían {_formatear_bytes(prevision['bytes_liberados'])} "
            f"({prevision['eliminados']:,} archivos).",
            style=WARNING_STYLE,
        )
        if aceptar(f"¿Eliminar los {total:,} archivos temporales?"):
            resultado = limpiar_temporales(resumen["archivos"], dry_run=False)
            registrar_log(
                "temporales/limpiar",
                detalle=(
                    f"eliminados={resultado['eliminados']} "
                    f"bytes={resultado['bytes_liberados']} "
                    f"omitidos={resultado['omitidos']} (en uso o sin permiso)"
                ),
                estado="OK",
            )
            pantalla.print(
                f"[green]Limpieza completada:[/green] {resultado['eliminados']:,} eliminados, "
                f"{_formatear_bytes(resultado['bytes_liberados'])} liberados, "
                f"{resultado['omitidos']} omitidos.",
                style=NORMAL_STYLE,
            )
        else:
            pantalla.print("Limpieza de temporales omitida.", style=NORMAL_STYLE)
    else:
        pantalla.print("No se encontraron temporales que limpiar.", style=NORMAL_STYLE)

    pantalla.print()
    mejor = procesos_consumidores()
    if mejor:
        pantalla.print(
            "Procesos con mayor consumo (referencia para decidir qué cerrar):",
            style=WARNING_STYLE,
        )
        for pid, nombre, cpu, memoria in mejor:
            pantalla.print(f"  {pid:>7} {nombre:<24} CPU {cpu:>5.1f}%  MEM {memoria:>5.1f}%", style="muted")

    # 2. Telemetría
    pantalla.print()
    filas = consultar_estado()
    pantalla.print(_tabla_telemetria(filas))
    aplicables = [fila for fila in filas if fila.get("aplicable")]
    if aplicables and aceptar("¿Deshabilitar los mecanismos de telemetría listados?"):
        resultados = aplicar_telemetria(dry_run=False)
        for resultado in resultados:
            pantalla.print(
                f"  - {resultado['accion']}: {resultado['resultado']}",
                style=NORMAL_STYLE if resultado.get("resultado") == "ok" else WARNING_STYLE,
            )
    else:
        pantalla.print(
            "Telemetría sin cambios (se muestra el plan solo).",
            style=NORMAL_STYLE,
        )

    pantalla.print(
        f"\nLog auditable: {__log_path()}", style="muted",
    )
    return 0


def __log_path():
    from diagnosqui.optimizacion.safety import ubicacion_log

    return ubicacion_log()


__all__ = ["run_optimizacion"]