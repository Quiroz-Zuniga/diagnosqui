"""
Módulo para visualización de información del sistema operativo.
"""
from rich.table import Table
from rich.panel import Panel
from diagnosqui.core.platform_utils import get_backend, check_elevation_warning
from diagnosqui.ui.theme import console, print_header, print_status_badge


def show_sistema():
    """Muestra información detallada del sistema operativo y la plataforma."""
    print_header("Información del Sistema", "Módulo 1 / Sistema Operativo")
    check_elevation_warning()

    backend = get_backend()
    data = backend.get_system_info()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Propiedad", style="cyan bold")
    table.add_column("Valor", style="white")

    table.add_row("Sistema Operativo", data["os"])
    table.add_row("Versión de Kernel/SO", data["version"])
    table.add_row("Plataforma", data["platform"])
    table.add_row("Procesador", data["processor"])
    table.add_row("Arquitectura", data["architecture"])
    table.add_row("Nombre del Equipo", data["hostname"])
    table.add_row("Versión de Python", data["python"])
    table.add_row("Tiempo Encendido", f"[green]{data['uptime']}[/green]")
    table.add_row(
        "Privilegios",
        "[badge.ok]  ADMINISTRADOR  [/badge.ok]" if data["is_admin"] else "[badge.warn]  USUARIO ESTÁNDAR  [/badge.warn]"
    )

    console.print(Panel(table, border_style="cyan", title="[bold white]Detalles del Sistema[/bold white]"))
