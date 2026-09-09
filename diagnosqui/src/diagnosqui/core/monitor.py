"""
Módulo para visualización y diagnóstico de GPU y adaptadores de pantalla.
"""
import json
from rich.table import Table
from rich.panel import Panel
from diagnosqui.core.platform_utils import get_backend
from diagnosqui.ui.theme import console, print_header, print_status_badge


def recolectar_gpu() -> dict:
    """Recolecta datos de GPU y devuelve el CONTRATO UNIFICADO."""
    backend = get_backend()
    return backend.get_gpu_info()


def show_monitor():
    """Muestra información de la tarjeta gráfica (GPU), memoria VRAM y controladores de video."""
    print_header("Diagnóstico de GPU y Pantalla", "Módulo 10 / GPU & Gráficos")

    data = recolectar_gpu()

    if "error" in data.get("detalle", {}):
        console.print(Panel(f"[red]Error: {data['detalle']['error']}[/red]", border_style="red"))
        return

    detalle = data.get("detalle", {})
    estado = data.get("estado", "NORMAL")
    evidencia = data.get("evidencia", "N/D")
    recomendaciones = data.get("recomendacion", [])

    gpus = detalle.get("gpus", [])

    if gpus:
        table = Table(title="[bold white]Adaptadores de Video Detectados[/bold white]", border_style="cyan")
        table.add_column("Tarjeta Gráfica (GPU)", style="bold white")
        table.add_column("VRAM Dedicada", justify="right", style="cyan")
        table.add_column("Versión de Driver", style="white")
        table.add_column("Estado", justify="center")
        table.add_column("Procesador de Video", style="muted")

        for g in gpus:
            vram_str = f"{g['vram_gb']:.2f} GB" if g["vram_gb"] > 0 else "Compartida / N/D"
            badge = print_status_badge(g["status"])
            table.add_row(
                g["name"],
                vram_str,
                g["driver_version"],
                badge,
                g["processor"]
            )
        console.print(table)
        console.print()

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
    resultado = recolectar_gpu()
    print(json.dumps(resultado, indent=2, ensure_ascii=False))