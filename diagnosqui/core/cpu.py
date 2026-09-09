"""
Módulo para visualización y diagnóstico de CPU.
"""
import json
from rich.table import Table
from rich.panel import Panel
from diagnosqui.core.platform_utils import get_backend
from diagnosqui.ui.theme import console, print_header, print_status_badge


def recolectar_cpu() -> dict:
    """Recolecta datos de CPU y devuelve el CONTRATO UNIFICADO."""
    backend = get_backend()
    return backend.get_cpu_info()


def show_cpu():
    """Muestra estadísticas detalladas del procesador, uso por núcleo y carga global."""
    print_header("Diagnóstico de CPU", "Módulo 2 / Procesador")

    data = recolectar_cpu()

    # Si hay error en la recolección
    if "error" in data.get("detalle", {}):
        console.print(Panel(f"[red]Error: {data['detalle']['error']}[/red]", border_style="red"))
        return

    detalle = data.get("detalle", {})

    info_table = Table(show_header=False, box=None, padding=(0, 2))
    info_table.add_column("Propiedad", style="cyan bold")
    info_table.add_column("Valor", style="white")

    info_table.add_row("Modelo de CPU", detalle.get("modelo", "N/D"))
    info_table.add_row("Núcleos Físicos", str(detalle.get("nucleos_fisicos", "N/D")))
    info_table.add_row("Núcleos Lógicos (Hilos)", str(detalle.get("nucleos_logicos", "N/D")))

    freq_actual = detalle.get("frecuencia_actual_mhz", 0)
    freq_min = detalle.get("frecuencia_min_mhz", 0)
    freq_max = detalle.get("frecuencia_max_mhz", 0)
    freq_str = f"{freq_actual:.0f} MHz"
    if freq_min or freq_max:
        freq_str += f" (Min: {freq_min:.0f} MHz - Max: {freq_max:.0f} MHz)"
    info_table.add_row("Frecuencia", freq_str)

    console.print(Panel(info_table, border_style="cyan", title="[bold white]Especificaciones[/bold white]"))
    console.print()

    # Uso por núcleo
    por_nucleo = detalle.get("por_nucleo", [])
    if por_nucleo:
        core_table = Table(title="[bold white]Uso por Núcleo[/bold white]", border_style="bright_blue", expand=False)
        core_table.add_column("Núcleo", justify="center", style="cyan")
        core_table.add_column("Carga Visual", justify="left", width=30)
        core_table.add_column("Porcentaje", justify="right")

        for i, pct in enumerate(por_nucleo):
            blocks = int(pct / 5)
            # Usar los mismos umbrales del contrato: 70/90
            bar_color = "red" if pct >= 90 else ("yellow" if pct >= 70 else "green")
            bar_visual = f"[{bar_color}]{'#' * blocks}[/{bar_color}][bright_black]{'-' * (20 - blocks)}[/bright_black]"
            core_table.add_row(f"Core #{i}", bar_visual, f"[{bar_color}]{pct:>5.1f}%[/{bar_color}]")

        console.print(core_table)
        console.print()

    # Estado global - usar el estado del contrato
    estado = data.get("estado", "NORMAL")
    valor = data.get("valor_numerico", 0)
    evidencia = data.get("evidencia", "N/D")
    recomendaciones = data.get("recomendacion", [])

    status_table = Table(show_header=False, box=None)
    status_table.add_column("Label", style="bold")
    status_table.add_column("Value")
    status_table.add_row("Uso Total:", f"[bold cyan]{evidencia}[/bold cyan]")
    status_table.add_row("Estado:", f"{print_status_badge(estado)} {data.get('componente', 'CPU')}: {estado}")

    if recomendaciones:
        for rec in recomendaciones:
            status_table.add_row("Recomendación:", f"[cyan]→ {rec}[/cyan]")

    border_color = "yellow" if estado == "ADVERTENCIA" else ("red" if estado == "CRITICO" else "green")
    console.print(Panel(status_table, border_style=border_color))


if __name__ == "__main__":
    resultado = recolectar_cpu()
    print(json.dumps(resultado, indent=2, ensure_ascii=False))