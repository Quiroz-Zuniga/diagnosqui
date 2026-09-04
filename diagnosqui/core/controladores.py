"""
Módulo para visualización y auditoría de controladores (drivers) del sistema.
"""
from rich.table import Table
from diagnosqui.core.platform_utils import get_backend
from diagnosqui.ui.theme import console, print_header, print_status_badge


def show_controladores():
    """Muestra controladores cargados y verificación de controladores firmados."""
    print_header("Auditoría de Controladores (Drivers)", "Módulo 8 / Drivers")

    backend = get_backend()
    data = backend.get_drivers_info()

    signed = data["signed_drivers"]
    drivers = data["drivers"]

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
    console.print(f"[muted]Total de controladores registrados en el sistema: [bold white]{data['total_count']}[/bold white][/muted]")
