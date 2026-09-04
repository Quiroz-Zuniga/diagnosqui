"""
Módulo para visualización y diagnóstico de interfaces de red y tráfico.
"""
from rich.table import Table
from rich.panel import Panel
from diagnosqui.core.platform_utils import get_backend
from diagnosqui.ui.theme import console, print_header, print_status_badge


def show_red():
    """Muestra adaptadores de red, direcciones asignadas y telemetría de paquetes."""
    print_header("Diagnóstico de Interfaces de Red", "Módulo 5 / Red")

    backend = get_backend()
    data = backend.get_network_info()

    table = Table(title="[bold white]Adaptadores de Red[/bold white]", border_style="cyan")
    table.add_column("Interfaz", style="cyan bold")
    table.add_column("Estado", justify="center")
    table.add_column("Velocidad", justify="right")
    table.add_column("IPv4", style="white")
    table.add_column("MAC", style="muted")

    for iface in data["interfaces"]:
        status_badge = print_status_badge("ACTIVO" if iface["is_up"] else "INACTIVO")
        ipv4_str = ", ".join(iface["ipv4"]) if iface["ipv4"] else "[muted]Sin IPv4[/muted]"
        speed_str = f"{iface['speed_mbps']} Mbps" if iface["speed_mbps"] > 0 else "Auto"

        table.add_row(
            iface["name"],
            status_badge,
            speed_str,
            ipv4_str,
            iface["mac"]
        )

    console.print(table)
    console.print()

    # Telemetría Global
    io = data["global_io"]
    io_table = Table(show_header=False, box=None, padding=(0, 2))
    io_table.add_column("Métrica", style="cyan bold")
    io_table.add_column("Valor", style="white")

    io_table.add_row("Tráfico Enviado", f"[green]{io['sent_mb']:.2f} MB[/green]")
    io_table.add_row("Tráfico Recibido", f"[cyan]{io['recv_mb']:.2f} MB[/cyan]")
    io_table.add_row("Paquetes TX / RX", f"{io['packets_sent']:,} / {io['packets_recv']:,}")
    io_table.add_row(
        "Errores Entrada / Salida",
        f"[red]{io['errin']}[/red] / [red]{io['errout']}[/red]" if (io['errin'] or io['errout']) else "[green]0 / 0 (Sin errores)[/green]"
    )
    io_table.add_row(
        "Paquetes Descartados",
        f"[yellow]{io['dropin'] + io['dropout']}[/yellow]" if (io['dropin'] or io['dropout']) else "[green]0 (Sin descartes)[/green]"
    )

    console.print(Panel(io_table, border_style="bright_blue", title="[bold white]Estadísticas Globales de E/S de Red[/bold white]"))
