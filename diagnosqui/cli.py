"""
Punto de entrada CLI para la herramienta DiagnosQui.
"""
import argparse
import sys

from diagnosqui.ui.boot import run_boot_animation
from diagnosqui.ui.terminal import run_interactive_shell, COMMANDS_MAP
from diagnosqui.core.reporte import show_reporte
from diagnosqui.ui.theme import console


def main():
    """Función principal ejecutada al invocar `diagnosqui` en la terminal."""
    parser = argparse.ArgumentParser(
        prog="diagnosqui",
        description="DiagnosQui ⚡ Administrador y Diagnóstico de Hardware Multiplataforma"
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Ejecuta la animación interactiva de arranque y validación de módulos estilo npm install"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Genera y muestra la matriz de diagnóstico y veredicto de inmediato"
    )
    parser.add_argument(
        "--export-html",
        action="store_true",
        help="Exporta de forma directa el reporte en formato CSV y HTML"
    )
    parser.add_argument(
        "--command", "-c",
        type=str,
        help="Ejecuta un comando específico directamente (ej: cpu, usb, memoria, discos)"
    )

    args = parser.parse_args()

    if args.setup:
        run_boot_animation()
        return

    if args.report or args.export_html:
        show_reporte(export_files=True)
        return

    if args.command:
        cmd_clean = args.command.strip().lower()
        for cmd_name, (num_str, _, func) in COMMANDS_MAP.items():
            if cmd_clean == cmd_name or cmd_clean == num_str:
                func()
                return
        console.print(f"[red]Comando desconocido: '{args.command}'.[/red]")
        sys.exit(1)

    # Por defecto: arranque visual y shell interactivo
    run_boot_animation()
    run_interactive_shell()


if __name__ == "__main__":
    main()
