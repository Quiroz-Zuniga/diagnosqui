"""
Módulo para visualización y diagnóstico del bus USB.
"""
from rich.table import Table
from rich.panel import Panel
from diagnosqui.core.platform_utils import get_backend
from diagnosqui.ui.theme import console, print_header, print_status_badge


def show_usb():
    """Muestra dispositivos USB conectados y analiza dispositivos con errores."""
    print_header("Diagnóstico del Bus USB", "Módulo 6 / Periféricos USB")

    backend = get_backend()
    data = backend.get_usb_devices()

    devices = data["devices"]
    problems = data["problem_devices"]

    if devices:
        table = Table(title=f"[bold white]Dispositivos USB Conectados ({len(devices)})[/bold white]", border_style="cyan")
        table.add_column("Nombre / Descripción", style="bold white")
        table.add_column("Estado", justify="center")
        table.add_column("Clase", style="cyan")
        table.add_column("ID de Instancia", style="muted")

        for dev in devices:
            status = dev.get("Status", "OK")
            badge = print_status_badge(status)
            table.add_row(
                dev.get("FriendlyName", "Dispositivo USB"),
                badge,
                dev.get("Class", "USB"),
                dev.get("InstanceId", "N/D")[:45]
            )
        console.print(table)
    else:
        console.print("[yellow]No se detectaron dispositivos USB o el acceso a PnP requiere elevación.[/yellow]")

    console.print()

    # Diagnóstico de problemas
    if problems:
        prob_table = Table(title="[bold red]⚠ Dispositivos USB con Problemas Detectados[/bold red]", border_style="red")
        prob_table.add_column("Dispositivo", style="bold red")
        prob_table.add_column("Estado", justify="center")
        prob_table.add_column("Detalle del Problema", style="yellow")

        for prob in problems:
            prob_table.add_row(
                prob.get("FriendlyName", "Dispositivo desconocido"),
                print_status_badge(prob.get("Status", "ERROR")),
                prob.get("Problem", "Código de error de controlador o descriptor inválido")
            )
        console.print(prob_table)
    else:
        status_panel = Panel(
            f"{print_status_badge('OK')} [green]Todos los dispositivos USB conectados operan correctamente sin errores registrados.[/green]",
            border_style="green",
            title="[bold green]Salud del Bus USB[/bold green]"
        )
        console.print(status_panel)
