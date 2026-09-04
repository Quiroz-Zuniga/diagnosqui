"""
Módulo para visualización y diagnóstico de memoria RAM y Swap.
"""
from rich.table import Table
from rich.panel import Panel
from diagnosqui.core.platform_utils import get_backend
from diagnosqui.ui.theme import console, print_header, print_status_badge


def show_memoria():
    """Muestra estadísticas de memoria física (RAM) y memoria virtual (Swap)."""
    print_header("Diagnóstico de Memoria RAM", "Módulo 3 / Memoria")

    backend = get_backend()
    data = backend.get_memory_info()

    pct = data["percent"]
    blocks = int(pct / 5)
    bar_color = "red" if pct > 85 else ("yellow" if pct > 70 else "green")
    bar_visual = f"[{bar_color}]{'#' * blocks}[/{bar_color}][bright_black]{'-' * (20 - blocks)}[/bright_black]"

    mem_table = Table(show_header=False, box=None, padding=(0, 2))
    mem_table.add_column("Métrica", style="cyan bold")
    mem_table.add_column("Valor", style="white")

    mem_table.add_row("Memoria Total", f"{data['total_gb']:.2f} GB")
    mem_table.add_row("Memoria Disponible", f"[green]{data['available_gb']:.2f} GB[/green]")
    mem_table.add_row("Memoria Utilizada", f"[{bar_color}]{data['used_gb']:.2f} GB[/{bar_color}]")
    mem_table.add_row("Porcentaje de Uso", f"[{bar_color}]{pct:.1f}%[/{bar_color}] {bar_visual}")

    console.print(Panel(mem_table, border_style="cyan", title="[bold white]Memoria Física (RAM)[/bold white]"))
    console.print()

    # Swap
    swap_pct = data["swap_percent"]
    swap_blocks = int(swap_pct / 5)
    swap_color = "red" if swap_pct > 80 else ("yellow" if swap_pct > 50 else "cyan")
    swap_visual = f"[{swap_color}]{'#' * swap_blocks}[/{swap_color}][bright_black]{'-' * (20 - swap_blocks)}[/bright_black]"

    swap_table = Table(show_header=False, box=None, padding=(0, 2))
    swap_table.add_column("Métrica", style="cyan bold")
    swap_table.add_column("Valor", style="white")

    swap_table.add_row("Swap Total", f"{data['swap_total_gb']:.2f} GB")
    swap_table.add_row("Swap Utilizada", f"{data['swap_used_gb']:.2f} GB")
    swap_table.add_row("Uso de Swap", f"[{swap_color}]{swap_pct:.1f}%[/{swap_color}] {swap_visual}")

    console.print(Panel(swap_table, border_style="bright_blue", title="[bold white]Archivo de Paginación / Swap[/bold white]"))
    console.print()

    # Diagnóstico
    if pct > 90:
        status = "CRITICO"
        desc = "Memoria RAM al límite. El sistema está paginando fuertemente hacia el disco (causa mayor de lentitud)."
    elif pct > 70:
        status = "ALERTA"
        desc = "Consumo de memoria elevado. Cierre aplicaciones innecesarias para evitar cuellos de botella."
    else:
        status = "OK"
        desc = "Capacidad de memoria suficiente para la carga actual."

    status_table = Table(show_header=False, box=None)
    status_table.add_column("Label", style="bold")
    status_table.add_column("Value")
    status_table.add_row("Estado:", f"{print_status_badge(status)} {desc}")

    console.print(Panel(status_table, border_style="yellow" if status == "ALERTA" else ("red" if status == "CRITICO" else "green")))
