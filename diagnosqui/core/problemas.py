"""
Módulo para detección y diagnóstico de dispositivos con fallas o degradados.
"""
from rich.table import Table
from rich.panel import Panel
from diagnosqui.core.platform_utils import get_backend
from diagnosqui.ui.theme import console, print_header, print_status_badge


def show_problemas():
    """Identifica dispositivos con errores de hardware, controladores faltantes o estado degradado."""
    print_header("Diagnóstico de Dispositivos con Problemas", "Módulo 9 / Fallas de Hardware")

    backend = get_backend()
    data = backend.get_problem_devices()

    errors = data["errors"]
    degraded = data["degraded"]
    unk_count = data["unknown_count"]

    if errors:
        table_err = Table(title="[bold red][!] Dispositivos en Estado ERROR[/bold red]", border_style="red")
        table_err.add_column("Dispositivo", style="bold red")
        table_err.add_column("Estado", justify="center")
        table_err.add_column("Clase", style="cyan")
        table_err.add_column("ID de Instancia", style="muted")

        for dev in errors:
            table_err.add_row(
                dev.get("FriendlyName", "Dispositivo"),
                print_status_badge("ERROR"),
                dev.get("Class", "N/D"),
                dev.get("InstanceId", "N/D")[:50]
            )
        console.print(table_err)
        console.print()

    if degraded:
        table_deg = Table(title="[bold yellow][!] Dispositivos en Estado DEGRADADO[/bold yellow]", border_style="yellow")
        table_deg.add_column("Dispositivo", style="bold yellow")
        table_deg.add_column("Estado", justify="center")
        table_deg.add_column("Clase", style="cyan")

        for dev in degraded:
            table_deg.add_row(
                dev.get("FriendlyName", "Dispositivo"),
                print_status_badge("DEGRADED"),
                dev.get("Class", "N/D")
            )
        console.print(table_deg)
        console.print()

    if unk_count > 0:
        console.print(f"[yellow][!] Se detectaron [bold]{unk_count}[/bold] dispositivos en estado Desconocido (Unknown).[/yellow]")
        console.print()

    if not errors and not degraded and unk_count == 0:
        panel_ok = Panel(
            f"{print_status_badge('OK')} [green]No se detectaron dispositivos con errores, fallas de controlador ni estados degradados en el árbol de hardware.[/green]",
            border_style="green",
            title="[bold green]Salud de Dispositivos[/bold green]"
        )
        console.print(panel_ok)
    else:
        total = data["total_problematic"]
        panel_warn = Panel(
            f"{print_status_badge('CRITICO')} [red]Se detectaron {total} incidentes en dispositivos del sistema. Revise los controladores o la conexión física del periférico.[/red]",
            border_style="red",
            title="[bold red]Atención Requerida[/bold red]"
        )
        console.print(panel_warn)
