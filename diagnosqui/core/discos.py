"""
Módulo para visualización y diagnóstico de discos y almacenamiento.
"""
from rich.table import Table
from rich.panel import Panel
from diagnosqui.core.platform_utils import get_backend
from diagnosqui.ui.theme import console, print_header, print_status_badge


def show_discos():
    """Muestra particiones montadas, estadísticas de E/S y discos físicos detectados."""
    print_header("Diagnóstico de Almacenamiento", "Módulo 4 / Discos")

    backend = get_backend()
    data = backend.get_disks_info()

    # Particiones
    part_table = Table(title="[bold white]Particiones y Volúmenes Montados[/bold white]", border_style="cyan")
    part_table.add_column("Unidad", style="cyan bold")
    part_table.add_column("Punto Montaje", style="white")
    part_table.add_column("FS", style="muted")
    part_table.add_column("Total", justify="right")
    part_table.add_column("Usado", justify="right")
    part_table.add_column("Libre", justify="right")
    part_table.add_column("Uso %", justify="center")

    has_warning = False
    for p in data["partitions"]:
        if "error" in p:
            part_table.add_row(p["device"], p["mountpoint"], p.get("fstype", "N/D"), "-", "-", "-", f"[yellow]{p['error']}[/yellow]")
            continue

        pct = p["percent"]
        blocks = int(pct / 10)
        color = "red" if pct > 85 else ("yellow" if pct > 75 else "green")
        if pct > 85:
            has_warning = True

        bar = f"[{color}]{'#' * blocks}{'-' * (10 - blocks)} {pct:.1f}%[/{color}]"
        part_table.add_row(
            p["device"],
            p["mountpoint"],
            p["fstype"],
            f"{p['total_gb']:.1f} GB",
            f"{p['used_gb']:.1f} GB",
            f"[green]{p['free_gb']:.1f} GB[/green]",
            bar
        )

    console.print(part_table)
    console.print()

    # Discos Físicos
    if data["physical_disks"]:
        phys_table = Table(title="[bold white]Discos Físicos del Sistema[/bold white]", border_style="bright_blue")
        phys_table.add_column("Dispositivo / Modelo", style="bold white")
        phys_table.add_column("Tipo de Medio", style="cyan")
        phys_table.add_column("Bus", style="magenta")
        phys_table.add_column("Salud / Estado", justify="center")
        phys_table.add_column("Capacidad", justify="right")

        for d in data["physical_disks"]:
            status_text = d.get("HealthStatus", "OK")
            badge = print_status_badge(status_text)
            phys_table.add_row(
                d.get("FriendlyName", "Disco"),
                d.get("MediaType", "N/D"),
                d.get("BusType", "N/D"),
                badge,
                d.get("Size", "N/D")
            )
        console.print(phys_table)
        console.print()

    # Estadísticas de E/S
    if data["io_stats"]:
        io = data["io_stats"]
        io_table = Table(show_header=False, box=None, padding=(0, 2))
        io_table.add_column("Métrica", style="cyan bold")
        io_table.add_column("Valor", style="white")

        io_table.add_row("Operaciones de Lectura", f"{io['read_count']:,}")
        io_table.add_row("Operaciones de Escritura", f"{io['write_count']:,}")
        io_table.add_row("Total Leído", f"{io['read_mb']:.2f} MB")
        io_table.add_row("Total Escrito", f"{io['write_mb']:.2f} MB")

        console.print(Panel(io_table, border_style="cyan", title="[bold white]Acumulado de E/S de Disco[/bold white]"))
