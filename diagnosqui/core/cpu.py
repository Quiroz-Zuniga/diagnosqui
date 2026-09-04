"""
Módulo para visualización y diagnóstico de CPU.
"""
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn
from diagnosqui.core.platform_utils import get_backend
from diagnosqui.ui.theme import console, print_header, print_status_badge


def show_cpu():
    """Muestra estadísticas detalladas del procesador, uso por núcleo y carga global."""
    print_header("Diagnóstico de CPU", "Módulo 2 / Procesador")

    backend = get_backend()
    data = backend.get_cpu_info()

    info_table = Table(show_header=False, box=None, padding=(0, 2))
    info_table.add_column("Propiedad", style="cyan bold")
    info_table.add_column("Valor", style="white")

    info_table.add_row("Modelo de CPU", data["model"])
    info_table.add_row("Núcleos Físicos", str(data["physical_cores"]))
    info_table.add_row("Núcleos Lógicos (Hilos)", str(data["logical_cores"]))

    freq_str = f"{data['freq_current']:.0f} MHz"
    if data["freq_min"] or data["freq_max"]:
        freq_str += f" (Min: {data['freq_min']:.0f} MHz - Max: {data['freq_max']:.0f} MHz)"
    info_table.add_row("Frecuencia", freq_str)

    console.print(Panel(info_table, border_style="cyan", title="[bold white]Especificaciones[/bold white]"))
    console.print()

    # Uso por núcleo
    core_table = Table(title="[bold white]Uso por Núcleo[/bold white]", border_style="bright_blue", expand=False)
    core_table.add_column("Núcleo", justify="center", style="cyan")
    core_table.add_column("Carga Visual", justify="left", width=30)
    core_table.add_column("Porcentaje", justify="right")

    for i, pct in enumerate(data["per_cpu"]):
        blocks = int(pct / 5)
        bar_color = "red" if pct > 85 else ("yellow" if pct > 70 else "green")
        bar_visual = f"[{bar_color}]{'#' * blocks}[/{bar_color}][bright_black]{'-' * (20 - blocks)}[/bright_black]"
        core_table.add_row(f"Core #{i}", bar_visual, f"[{bar_color}]{pct:>5.1f}%[/{bar_color}]")

    console.print(core_table)
    console.print()

    # Estado global
    total = data["total_percent"]
    if total > 90:
        status = "CRITICO"
        desc = "Carga de CPU extrema. Posible saturación de hilos o proceso en bucle."
    elif total > 70:
        status = "ALERTA"
        desc = "Carga de CPU moderada-alta. El rendimiento general puede verse degradado."
    else:
        status = "OK"
        desc = "Carga de CPU en rango normal y óptimo."

    status_table = Table(show_header=False, box=None)
    status_table.add_column("Label", style="bold")
    status_table.add_column("Value")
    status_table.add_row("Uso Total:", f"[bold cyan]{total:.1f}%[/bold cyan]")
    status_table.add_row("Estado:", f"{print_status_badge(status)} {desc}")

    console.print(Panel(status_table, border_style="yellow" if status == "ALERTA" else ("red" if status == "CRITICO" else "green")))
