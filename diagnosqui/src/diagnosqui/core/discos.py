"""
Módulo para visualización y diagnóstico de discos y almacenamiento.
"""
import json
from rich.table import Table
from rich.panel import Panel
from diagnosqui.core.platform_utils import get_backend
from diagnosqui.ui.theme import console, print_header, print_status_badge


def recolectar_discos() -> dict:
    """Recolecta datos de almacenamiento y devuelve el CONTRATO UNIFICADO."""
    backend = get_backend()
    return backend.get_disks_info()


def show_discos():
    """Muestra particiones montadas, estadísticas de E/S y discos físicos detectados."""
    print_header("Diagnóstico de Almacenamiento", "Módulo 4 / Discos")

    data = recolectar_discos()

    # Si hay error en la recolección
    if "error" in data.get("detalle", {}):
        console.print(Panel(f"[red]Error: {data['detalle']['error']}[/red]", border_style="red"))
        return

    detalle = data.get("detalle", {})
    estado = data.get("estado", "NORMAL")
    evidencia = data.get("evidencia", "N/D")
    recomendaciones = data.get("recomendacion", [])

    # Particiones
    part_table = Table(title="[bold white]Particiones y Volúmenes Montados[/bold white]", border_style="cyan")
    part_table.add_column("Unidad", style="cyan bold")
    part_table.add_column("Punto Montaje", style="white")
    part_table.add_column("FS", style="muted")
    part_table.add_column("Total", justify="right")
    part_table.add_column("Usado", justify="right")
    part_table.add_column("Libre", justify="right")
    part_table.add_column("Uso %", justify="center")

    for p in detalle.get("particiones", []):
        if "error" in p:
            part_table.add_row(p["device"], p["mountpoint"], p.get("fstype", "N/D"), "-", "-", "-", f"[yellow]{p['error']}[/yellow]")
            continue

        pct = p.get("percent", 0)
        blocks = int(pct / 10)
        color = "red" if pct >= 90 else ("yellow" if pct >= 70 else "green")

        bar = f"[{color}]{'#' * blocks}{'-' * (10 - blocks)} {pct:.1f}%[/{color}]"
        part_table.add_row(
            p["device"],
            p["mountpoint"],
            p.get("fstype", "N/D"),
            f"{p.get('total_gb', 0):.1f} GB",
            f"{p.get('used_gb', 0):.1f} GB",
            f"[green]{p.get('free_gb', 0):.1f} GB[/green]",
            bar
        )

    console.print(part_table)
    console.print()

    # Discos Físicos
    physical_disks = detalle.get("discos_fisicos", [])
    if physical_disks:
        phys_table = Table(title="[bold white]Discos Físicos del Sistema[/bold white]", border_style="bright_blue")
        phys_table.add_column("Dispositivo / Modelo", style="bold white")
        phys_table.add_column("Tipo de Medio", style="cyan")
        phys_table.add_column("Bus", style="magenta")
        phys_table.add_column("Salud / Estado", justify="center")
        phys_table.add_column("Capacidad", justify="right")

        for d in physical_disks:
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
    io_stats = detalle.get("io_stats")
    if io_stats:
        io_table = Table(show_header=False, box=None, padding=(0, 2))
        io_table.add_column("Métrica", style="cyan bold")
        io_table.add_column("Valor", style="white")

        io_table.add_row("Operaciones de Lectura", f"{io_stats.get('read_count', 0):,}")
        io_table.add_row("Operaciones de Escritura", f"{io_stats.get('write_count', 0):,}")
        io_table.add_row("Total Leído", f"{io_stats.get('read_mb', 0):.2f} MB")
        io_table.add_row("Total Escrito", f"{io_stats.get('write_mb', 0):.2f} MB")

        console.print(Panel(io_table, border_style="cyan", title="[bold white]Acumulado de E/S de Disco[/bold white]"))

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
    resultado = recolectar_discos()
    print(json.dumps(resultado, indent=2, ensure_ascii=False))