"""
Módulo para visualización y diagnóstico de GPU y adaptadores de pantalla.
"""
from rich.table import Table
from rich.panel import Panel
from diagnosqui.core.platform_utils import get_backend
from diagnosqui.ui.theme import console, print_header, print_status_badge


def show_monitor():
    """Muestra información de la tarjeta gráfica (GPU), memoria VRAM y controladores de video."""
    print_header("Diagnóstico de GPU y Pantalla", "Módulo 10 / GPU & Gráficos")

    backend = get_backend()
    data = backend.get_gpu_info()

    gpus = data["gpus"]

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

        if data["is_healthy"]:
            panel = Panel(
                f"{print_status_badge('OK')} [green]Los adaptadores gráficos responden correctamente con estado OK.[/green]",
                border_style="green",
                title="[bold green]Salud Gráfica[/bold green]"
            )
        else:
            panel = Panel(
                f"{print_status_badge('ALERTA')} [yellow]Se detectaron anomalías o drivers genéricos en el controlador de video. Puede causar problemas de renderizado o baja tasa de refresco.[/yellow]",
                border_style="yellow",
                title="[bold yellow]Atención Gráfica[/bold yellow]"
            )
        console.print(panel)
    else:
        console.print("[yellow]No se detectaron adaptadores de video activos mediante la interfaz WMI/LSPCI.[/yellow]")
