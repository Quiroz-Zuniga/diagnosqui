"""
Módulo para visualización de información del sistema operativo.
"""
import json
from rich.table import Table
from rich.panel import Panel
from diagnosqui.core.platform_utils import get_backend, check_elevation_warning
from diagnosqui.ui.theme import console, print_header


def recolectar_sistema() -> dict:
    """Recolecta datos del sistema (metadata, no contrato unificado)."""
    backend = get_backend()
    return backend.get_system_info()


def show_sistema():
    """Muestra información detallada del sistema operativo y la plataforma."""
    print_header("Información del Sistema", "Módulo 1 / Sistema Operativo")
    check_elevation_warning()

    data = recolectar_sistema()

    if "error" in data:
        console.print(Panel(f"[red]Error: {data['error']}[/red]", border_style="red"))
        return

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Propiedad", style="cyan bold")
    table.add_column("Valor", style="white")

    table.add_row("Sistema Operativo", data.get("os", "N/D"))
    table.add_row("Versión de Kernel/SO", data.get("version", "N/D"))
    table.add_row("Plataforma", data.get("platform", "N/D"))
    table.add_row("Procesador", data.get("processor", "N/D"))
    table.add_row("Arquitectura", data.get("architecture", "N/D"))
    table.add_row("Nombre del Equipo", data.get("hostname", "N/D"))
    table.add_row("Versión de Python", data.get("python", "N/D"))
    table.add_row("Tiempo Encendido", f"[green]{data.get('uptime', 'N/D')}[/green]")
    table.add_row(
        "Privilegios",
        "[badge.ok]  ADMINISTRADOR  [/badge.ok]" if data.get("is_admin") else "[badge.warn]  USUARIO ESTÁNDAR  [/badge.warn]"
    )

    console.print(Panel(table, border_style="cyan", title="[bold white]Detalles del Sistema[/bold white]"))


if __name__ == "__main__":
    resultado = recolectar_sistema()
    print(json.dumps(resultado, indent=2, ensure_ascii=False))