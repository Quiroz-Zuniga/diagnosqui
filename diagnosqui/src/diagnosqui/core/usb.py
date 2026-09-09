"""
Módulo para visualización y diagnóstico del bus USB.
"""
import json
from rich.table import Table
from rich.panel import Panel
from diagnosqui.core.platform_utils import get_backend
from diagnosqui.ui.theme import console, print_header, print_status_badge


def recolectar_usb() -> dict:
    """Recolecta datos de USB y devuelve el CONTRATO UNIFICADO."""
    backend = get_backend()
    return backend.get_usb_devices()


def show_usb():
    """Muestra dispositivos USB conectados y analiza dispositivos con errores."""
    print_header("Diagnóstico del Bus USB", "Módulo 6 / Periféricos USB")

    data = recolectar_usb()

    if "error" in data.get("detalle", {}):
        console.print(Panel(f"[red]Error: {data['detalle']['error']}[/red]", border_style="red"))
        return

    detalle = data.get("detalle", {})
    estado = data.get("estado", "NORMAL")
    evidencia = data.get("evidencia", "N/D")
    recomendaciones = data.get("recomendacion", [])

    devices = detalle.get("dispositivos", [])
    problems = detalle.get("problemas", [])

    if devices:
        table = Table(title=f"[bold white]Dispositivos USB Conectados ({len(devices)})[/bold white]", border_style="cyan")
        table.add_column("Nombre / Descripción", style="bold white")
        table.add_column("Estado", justify="center")
        table.add_column("Clase", style="cyan")
        table.add_column("ID de Instancia", style="muted")

        for dev in devices:
            status = dev.get("estado_clasificado", dev.get("Status", "OK"))
            badge = print_status_badge(status)
            table.add_row(
                dev.get("FriendlyName", "Dispositivo USB"),
                badge,
                dev.get("Class", "USB"),
                dev.get("InstanceId", "N/D")[:45]
            )
        console.print(table)
    else:
        console.print("[yellow]No se detectaron dispositivos USB o el acceso requiere elevación.[/yellow]")

    console.print()

    # Diagnóstico de problemas
    if problems:
        prob_table = Table(title="[bold red]⚠ Dispositivos USB con Problemas Detectados[/bold red]", border_style="red")
        prob_table.add_column("Dispositivo", style="bold red")
        prob_table.add_column("Estado", justify="center")
        prob_table.add_column("Detalle del Problema", style="yellow")

        for prob in problems:
            status = prob.get("estado_clasificado", prob.get("Status", "ERROR"))
            prob_table.add_row(
                prob.get("FriendlyName", "Dispositivo desconocido"),
                print_status_badge(status),
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

    # Estado global
    status_table = Table(show_header=False, box=None)
    status_table.add_column("Label", style="bold")
    status_table.add_column("Value")
    status_table.add_row("Estado:", f"{print_status_badge(estado)} {evidencia}")

    if recomendaciones:
        for rec in recomendaciones:
            status_table.add_row("Recomendación:", f"[cyan]→ {rec}[/cyan]")

    border_color = "yellow" if estado == "ADVERTENCIA" else ("red" if estado == "CRITICO" else "green")
    console.print(Panel(status_table, border_style=border_color))


if __name__ == "__main__":
    resultado = recolectar_usb()
    print(json.dumps(resultado, indent=2, ensure_ascii=False))