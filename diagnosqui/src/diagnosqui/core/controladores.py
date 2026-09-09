"""
Módulo para visualización y auditoría de controladores (drivers) del sistema.
"""
import json
from rich.table import Table
from rich.panel import Panel
from diagnosqui.core.platform_utils import get_backend
from diagnosqui.ui.theme import console, print_header, print_status_badge


def recolectar_controladores() -> dict:
    """Recolecta datos de controladores y devuelve el CONTRATO UNIFICADO."""
    backend = get_backend()
    return backend.get_drivers_info()


def show_controladores():
    """Muestra controladores cargados y verificación de controladores firmados."""
    print_header("Auditoría de Controladores (Drivers)", "Módulo 8 / Drivers")

    data = recolectar_controladores()

    if "error" in data.get("detalle", {}):
        console.print(Panel(f"[red]Error: {data['detalle']['error']}[/red]", border_style="red"))
        return

    detalle = data.get("detalle", {})
    estado = data.get("estado", "NORMAL")
    evidencia = data.get("evidencia", "N/D")
    recomendaciones = data.get("recomendacion", [])

    signed = detalle.get("drivers_firmados", [])
    drivers = detalle.get("drivers", [])

    if signed:
        table = Table(
            title=f"[bold white]Controladores Registrados / Firmados (Primeros {len(signed)})[/bold white]",
            border_style="cyan"
        )
        table.add_column("Controlador / Driver", style="bold white")
        table.add_column("Archivo / Módulo", style="cyan")
        table.add_column("Clase", style="magenta")
        table.add_column("Proveedor / Detalles", style="muted")

        for d in signed:
            table.add_row(
                d.get("Driver", "N/D"),
                d.get("OriginalFileName", "N/D"),
                d.get("ClassName", "N/D"),
                d.get("ProviderName", "N/D")[:45]
            )
        console.print(table)
    elif drivers:
        table = Table(title=f"[bold white]Controladores Detectados ({len(drivers)})[/bold white]", border_style="cyan")
        table.add_column("Nombre", style="bold white")
        table.add_column("Tipo", style="cyan")
        table.add_column("Estado", style="green")

        for d in drivers[:25]:
            table.add_row(
                d.get("Module Name", d.get("Driver", "N/D")),
                d.get("Driver Type", "Kernel Driver"),
                d.get("Status", "Running")
            )
        console.print(table)
    else:
        console.print("[yellow]No se pudieron enumerar controladores con el nivel de privilegios actual.[/yellow]")

    console.print()
    console.print(f"[muted]Total de controladores registrados en el sistema: [bold white]{detalle.get('total_count', len(drivers))}[/bold white][/muted]")

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
    resultado = recolectar_controladores()
    print(json.dumps(resultado, indent=2, ensure_ascii=False))