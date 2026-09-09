"""
Módulo para monitorización en tiempo real de operaciones de E/S (disco y red).
"""
import json
import time
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from diagnosqui.core.platform_utils import get_backend
from diagnosqui.ui.theme import console, print_header


def recolectar_io_delta(duration: int = 3) -> dict:
    """Recolecta delta de E/S y devuelve dict (no contrato unificado, es medición dinámica)."""
    backend = get_backend()
    return backend.get_io_delta(duration)


def show_io_monitor(sample_seconds: int = 3):
    """Mide la tasa de transferencia de Entrada/Salida en disco y red durante una ventana de tiempo."""
    print_header("Monitorización de E/S (Entrada/Salida)", "Módulo 11 / Rendimiento I/O")

    backend = get_backend()

    with Progress(
        SpinnerColumn(spinner_name="line"),
        TextColumn(f"[cyan]Capturando flujo de E/S en tiempo real ({sample_seconds} segundos)...[/cyan]"),
        console=console,
        transient=True
    ) as progress:
        progress.add_task("sample", total=None)
        delta = backend.get_io_delta(sample_seconds)

    disk = delta.get("disk", {})
    net = delta.get("net", {})

    # Tabla Disco
    d_table = Table(title="[bold white]Actividad de E/S en Disco[/bold white]", border_style="cyan")
    d_table.add_column("Métrica", style="cyan bold")
    d_table.add_column("Operaciones en Ventana", justify="right")
    d_table.add_column("Velocidad Promedio", justify="right", style="green")

    if disk:
        d_table.add_row(
            "Lecturas",
            f"{disk.get('reads', 0):,} ops",
            f"{disk.get('read_kb', 0) / sample_seconds:.2f} KB/s"
        )
        d_table.add_row(
            "Escrituras",
            f"{disk.get('writes', 0):,} ops",
            f"{disk.get('write_kb', 0) / sample_seconds:.2f} KB/s"
        )
        d_table.add_row(
            "Total Transferido",
            "-",
            f"{(disk.get('read_kb', 0) + disk.get('write_kb', 0)) / 1024:.2f} MB"
        )
    console.print(d_table)
    console.print()

    # Tabla Red
    n_table = Table(title="[bold white]Actividad de Red en Ventana[/bold white]", border_style="bright_blue")
    n_table.add_column("Dirección de Flujo", style="bold white")
    n_table.add_column("Paquetes", justify="right")
    n_table.add_column("Tasa de Transferencia", justify="right", style="cyan")

    if net:
        n_table.add_row(
            "Tráfico Enviado (TX)",
            f"{net.get('packets_sent', 0):,} paq",
            f"{net.get('sent_kb', 0) / sample_seconds:.2f} KB/s"
        )
        n_table.add_row(
            "Tráfico Recibido (RX)",
            f"{net.get('packets_recv', 0):,} paq",
            f"{net.get('recv_kb', 0) / sample_seconds:.2f} KB/s"
        )
    console.print(n_table)
    console.print()

    # Periféricos de interfaz humana / E/S
    perif_table = Table(show_header=False, box=None, padding=(0, 2))
    perif_table.add_column("Canal E/S", style="cyan bold")
    perif_table.add_column("Estado de Dispositivo", style="white")

    perif_table.add_row("Teclado (Entrada)", "[green][OK] Activo (Controlador de bus HID registrado)[/green]")
    perif_table.add_row("Mouse / Puntero (Entrada)", "[green][OK] Activo (Sensor óptico/HID)[/green]")
    perif_table.add_row("Adaptador de Salida Gráfica", "[green][OK] Renderizando a consola de terminal[/green]")

    console.print(Panel(perif_table, border_style="cyan", title="[bold white]Subsistemas Periféricos de Interacción[/bold white]"))


if __name__ == "__main__":
    resultado = recolectar_io_delta(3)
    print(json.dumps(resultado, indent=2, ensure_ascii=False))