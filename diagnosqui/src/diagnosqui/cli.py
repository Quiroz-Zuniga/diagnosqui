"""Entrada de DiagnosQui: menú y conexión con los diagnósticos.

Esta entrega consume fixtures. Para conectar un módulo real, sustituir la rama
correspondiente de ``diagnostic_provider`` conservando el contrato de resultados.
"""

from __future__ import annotations

import argparse
import platform
from pathlib import Path
from typing import Optional, Sequence

from rich.console import Console
from rich.table import Table
from rich.text import Text

from diagnosqui.ui import terminal
from diagnosqui.ui.boot import run_boot_animation
from diagnosqui.ui.terminal import run_interactive_shell
from diagnosqui.ui.theme import (
    CRITICAL_STYLE, MUTED_STYLE, NORMAL_STYLE, PRIMARY_STYLE, WARNING_STYLE, console,
)


# El prompt, los números y el menú comparten el mismo catálogo.
MENU = tuple(
    (int(number), label, command)
    for command, (number, label) in terminal.COMMANDS_MAP.items()
)


def print_main_menu(
    system_name: Optional[str] = None,
    console_instance: Optional[Console] = None,
) -> None:
    output = console_instance or console
    current_system = system_name or platform.system()
    output.print(Text("=" * 56, style=MUTED_STYLE))
    output.print(Text("  DIAGNOSQUI — HARDWARE DIAGNOSTIC & REPAIR", style=PRIMARY_STYLE))
    output.print(Text("=" * 56, style=MUTED_STYLE))
    output.print("Diagnósticos: datos de prueba · Monitor: datos en vivo", style=MUTED_STYLE)
    output.print()
    menu = Table.grid(padding=(0, 3))
    menu.add_column()
    menu.add_column(style=PRIMARY_STYLE)
    for number, label, command in MENU:
        if number == 16 and current_system != "Windows":
            continue
        menu.add_row(Text(f"{number}. {label}"), Text(command))
    output.print(menu)
    output.print()
    output.print("help: ayuda · clear: limpiar · Tab: completar · ↑/↓: historial · 0: salir", style=MUTED_STYLE)
    output.print()


def diagnostic_provider(command: str) -> list[dict]:
    """Único punto de conexión; cada resultado conserva las seis claves acordadas.

    Los datos siguen siendo de prueba (fixtures), pero ``general`` y
    ``recomendaciones`` pasan por el motor de análisis y recomendaciones
    (``diagnosqui.analisis``): los estados y recomendaciones se recalculan
    con las reglas centrales del programa.

    Al integrar el equipo de diagnóstico real:
        from diagnosqui.core import cpu as cpu_module  # se conecta cuando esté listo
        if command == "cpu":
            return [cpu_module.diagnosticar()]  # debe devolver el contrato acordado

    General, recomendaciones y reportes deben usar el mismo proveedor de datos.
    """
    if command in {"general", "recomendaciones"}:
        from diagnosqui.analisis.recomendaciones import analizar_conjunto

        contratos = list(terminal.get_fixture_results(command))
        return analizar_conjunto(contratos)
    return terminal.get_fixture_results(command)


def boot_marker_path() -> Path:
    return terminal.state_directory() / "boot-completed"


def is_first_run() -> bool:
    try:
        return not boot_marker_path().is_file()
    except OSError:
        return True


def mark_boot_completed() -> bool:
    try:
        marker = boot_marker_path()
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("DiagnosQui UI setup completed\n", encoding="utf-8")
    except OSError:
        return False
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="diagnosqui",
        description="DiagnosQui · Interfaz de diagnóstico con fixtures y monitor en vivo",
    )
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--setup", action="store_true", help="Repetir el inicio visual estilo npm")
    actions.add_argument("--report", action="store_true", help="Mostrar un reporte de datos de prueba")
    actions.add_argument("--export-html", action="store_true", help="Exportar los datos de prueba a HTML y CSV")
    actions.add_argument("--command", "-c", help="Ejecutar un nombre o número de comando")
    parser.add_argument("--output-dir", type=Path, help="Carpeta de exportación (por defecto: ./reportes)")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    system_name = platform.system()

    def menu_printer() -> None:
        print_main_menu(system_name=system_name)

    try:
        if args.setup:
            run_boot_animation()
            if not mark_boot_completed():
                console.print("No se pudo guardar el estado de inicio; se repetirá al abrir.", style=WARNING_STYLE)
            return 0

        if args.export_html:
            paths = terminal.export_fixture_report(
                diagnostic_provider("general"), directory=args.output_dir, formats=("html", "csv")
            )
            console.print("Reporte de datos de prueba exportado:", style=NORMAL_STYLE)
            for path in paths.values():
                console.print(Text(str(path)))
            return 0

        if args.command is not None or args.report:
            action = terminal.dispatch_command(
                "reporte" if args.report else args.command,
                fixture_provider=diagnostic_provider,
                system_name=system_name,
                menu_printer=menu_printer,
                export_directory=args.output_dir,
            )
            return 1 if action is terminal.ShellAction.ERROR else 0

        if is_first_run():
            run_boot_animation()
            if not mark_boot_completed():
                console.print("No se pudo guardar el estado de inicio; se repetirá al abrir.", style=WARNING_STYLE)
        print_main_menu(system_name=system_name)
        run_interactive_shell(
            fixture_provider=diagnostic_provider,
            system_name=system_name,
            menu_printer=menu_printer,
            export_directory=args.output_dir,
        )
        return 0
    except KeyboardInterrupt:
        console.print("\nOperación cancelada.", style=WARNING_STYLE)
        return 130
    except (OSError, ValueError) as error:
        console.print(Text(f"No se pudo completar la operación: {error}", style=CRITICAL_STYLE))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
