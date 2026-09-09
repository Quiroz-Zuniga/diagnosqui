"""
Módulo para visualización y diagnóstico de memoria RAM y Swap.
"""
import json
from rich.table import Table
from rich.panel import Panel
from diagnosqui.core.platform_utils import get_backend
from diagnosqui.ui.theme import console, print_header, print_status_badge


def recolectar_memoria() -> dict:
    """Recolecta datos de memoria y devuelve el CONTRATO UNIFICADO."""
    backend = get_backend()
    return backend.get_memory_info()


def show_memoria():
    """Muestra estadísticas de memoria física (RAM) y memoria virtual (Swap)."""
    print_header("Diagnóstico de Memoria RAM", "Módulo 3 / Memoria")

    data = recolectar_memoria()

    # Si hay error en la recolección
    if "error" in data.get("detalle", {}):
        console.print(Panel(f"[red]Error: {data['detalle']['error']}[/red]", border_style="red"))
        return

    detalle = data.get("detalle", {})
    estado = data.get("estado", "NORMAL")
    evidencia = data.get("evidencia", "N/D")
    recomendaciones = data.get("recomendacion", [])

    # RAM
    total_gb = detalle.get("total_gb", 0)
    disponible_gb = detalle.get("disponible_gb", 0)
    usada_gb = detalle.get("usada_gb", 0)
    pct = detalle.get("porcentaje", data.get("valor_numerico", 0))

    blocks = int(pct / 5)
    bar_color = "red" if pct >= 90 else ("yellow" if pct >= 70 else "green")
    bar_visual = f"[{bar_color}]{'#' * blocks}[/{bar_color}][bright_black]{'-' * (20 - blocks)}[/bright_black]"

    mem_table = Table(show_header=False, box=None, padding=(0, 2))
    mem_table.add_column("Métrica", style="cyan bold")
    mem_table.add_column("Valor", style="white")

    mem_table.add_row("Memoria Total", f"{total_gb:.2f} GB")
    mem_table.add_row("Memoria Disponible", f"[green]{disponible_gb:.2f} GB[/green]")
    mem_table.add_row("Memoria Utilizada", f"[{bar_color}]{usada_gb:.2f} GB[/{bar_color}]")
    mem_table.add_row("Porcentaje de Uso", f"[{bar_color}]{pct:.1f}%[/{bar_color}] {bar_visual}")

    console.print(Panel(mem_table, border_style="cyan", title="[bold white]Memoria Física (RAM)[/bold white]"))
    console.print()

    # Swap
    swap_total_gb = detalle.get("swap_total_gb", 0)
    swap_usada_gb = detalle.get("swap_usada_gb", 0)
    swap_pct = detalle.get("swap_porcentaje", 0)

    swap_blocks = int(swap_pct / 5)
    swap_color = "red" if swap_pct >= 90 else ("yellow" if swap_pct >= 70 else "cyan")
    swap_visual = f"[{swap_color}]{'#' * swap_blocks}[/{swap_color}][bright_black]{'-' * (20 - swap_blocks)}[/bright_black]"

    swap_table = Table(show_header=False, box=None, padding=(0, 2))
    swap_table.add_column("Métrica", style="cyan bold")
    swap_table.add_column("Valor", style="white")

    swap_table.add_row("Swap Total", f"{swap_total_gb:.2f} GB")
    swap_table.add_row("Swap Utilizada", f"{swap_usada_gb:.2f} GB")
    swap_table.add_row("Uso de Swap", f"[{swap_color}]{swap_pct:.1f}%[/{swap_color}] {swap_visual}")

    console.print(Panel(swap_table, border_style="bright_blue", title="[bold white]Archivo de Paginación / Swap[/bold white]"))
    console.print()

    # Estado global - usar el estado del contrato
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
    resultado = recolectar_memoria()
    print(json.dumps(resultado, indent=2, ensure_ascii=False))