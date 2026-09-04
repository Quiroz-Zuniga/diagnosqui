"""
Shell interactivo estilo terminal Bash usando prompt_toolkit y rich.
"""
import os
import sys
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style as PromptStyle

from rich.table import Table
from rich.panel import Panel

from diagnosqui.ui.theme import console
from diagnosqui.ui.boot import run_boot_animation
from diagnosqui.core.sistema import show_sistema
from diagnosqui.core.cpu import show_cpu
from diagnosqui.core.memoria import show_memoria
from diagnosqui.core.discos import show_discos
from diagnosqui.core.red import show_red
from diagnosqui.core.usb import show_usb
from diagnosqui.core.pci import show_pci
from diagnosqui.core.controladores import show_controladores
from diagnosqui.core.problemas import show_problemas
from diagnosqui.core.monitor import show_monitor
from diagnosqui.core.io_monitor import show_io_monitor
from diagnosqui.core.reporte import show_reporte

COMMANDS_MAP = {
    "sistema": ("1", "Información del SO, kernel, arquitectura y uptime", show_sistema),
    "cpu": ("2", "Frecuencia, uso por núcleo y carga total del procesador", show_cpu),
    "memoria": ("3", "Telemetría de memoria RAM física y archivo Swap", show_memoria),
    "discos": ("4", "Particiones montadas, discos físicos y estadísticas de E/S", show_discos),
    "red": ("5", "Interfaces de red, direcciones IPv4/MAC y tráfico global", show_red),
    "usb": ("6", "Dispositivos conectados al bus USB e incidencias", show_usb),
    "pci": ("7", "Topología de buses PCI, PCIe y dispositivos ACPI", show_pci),
    "controladores": ("8", "Auditoría de drivers cargados y controladores firmados", show_controladores),
    "problemas": ("9", "Dispositivos en estado Error, Degradado o Desconocido", show_problemas),
    "monitor": ("10", "Tarjeta de video (GPU), VRAM y controlador gráfico", show_monitor),
    "io": ("11", "Muestreo en tiempo real de operaciones de E/S (disco y red)", show_io_monitor),
    "reporte": ("12", "Generar matriz de diagnóstico, veredicto y exportar CSV/HTML", show_reporte),
}


def print_help_menu():
    """Muestra la tabla de comandos interactivos disponibles."""
    table = Table(
        title="[bold cyan]COMANDOS DISPONIBLES — DIAGNOSQUI BASH SHELL[/bold cyan]",
        border_style="bright_blue",
        padding=(0, 1)
    )
    table.add_column("Cmd", style="cyan bold", width=16)
    table.add_column("Nº", justify="center", style="yellow bold", width=5)
    table.add_column("Descripción", style="white")

    for cmd, (num, desc, _) in COMMANDS_MAP.items():
        table.add_row(cmd, num, desc)

    table.add_row("setup", "-", "Ejecutar animación de arranque estilo npm")
    table.add_row("clear / cls", "-", "Limpiar la pantalla de la terminal")
    table.add_row("help / ayuda", "-", "Mostrar este menú de ayuda")
    table.add_row("salir / exit", "0", "Cerrar la consola DiagnosQui")

    console.print()
    console.print(table)
    console.print()


def run_interactive_shell():
    """Inicia el bucle principal de la terminal interactiva de DiagnosQui."""
    history_file = os.path.expanduser("~/.diagnosqui_history")

    command_words = (
        list(COMMANDS_MAP.keys()) +
        [num for num, _, _ in COMMANDS_MAP.values()] +
        ["setup", "clear", "cls", "help", "ayuda", "salir", "exit", "quit", "0"]
    )
    completer = WordCompleter(command_words, ignore_case=True)

    session = PromptSession(
        history=FileHistory(history_file),
        completer=completer,
        style=PromptStyle.from_dict({
            "prompt": "ansicyan bold",
            "arrow": "ansigreen bold",
            "host": "ansibrightblack",
        })
    )

    console.print("[dim]Escribe [bold white]'help'[/bold white] o el número de opción para comenzar. Presiona [bold white]Tab[/bold white] para autocompletar.[/dim]\n")

    while True:
        try:
            prompt_html = HTML("<arrow>➜ </arrow><prompt>diagnosqui</prompt> <host>›</host> ")
            user_input = session.prompt(prompt_html).strip().lower()

            if not user_input:
                continue

            # Comandos de control
            if user_input in ("0", "salir", "exit", "quit"):
                console.print("\n[cyan]⚡ Sesión de DiagnosQui finalizada. ¡Hasta luego![/cyan]")
                break
            elif user_input in ("clear", "cls"):
                console.clear()
                continue
            elif user_input in ("help", "ayuda", "?"):
                print_help_menu()
                continue
            elif user_input == "setup":
                run_boot_animation()
                continue

            # Mapeo por comando o por número
            dispatched = False
            for cmd_name, (num_str, _, func) in COMMANDS_MAP.items():
                if user_input == cmd_name or user_input == num_str:
                    func()
                    dispatched = True
                    break

            if not dispatched:
                console.print(f"[red]✖ Comando no reconocido:[/red] '{user_input}'. Escribe [bold white]'help'[/bold white] para ver la lista.")

            console.print()

        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Operación cancelada por el usuario.[/yellow]")
            break
