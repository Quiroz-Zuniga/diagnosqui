"""
Módulo para detección y diagnóstico de dispositivos con fallas o degradados.
"""
import json
from rich.table import Table
from rich.panel import Panel
from diagnosqui.core.platform_utils import get_backend
from diagnosqui.ui.theme import console, print_header, print_status_badge


def recolectar_problemas() -> dict:
    """Recolecta datos de dispositivos problemáticos y devuelve el CONTRATO UNIFICADO."""
    backend = get_backend()
    return backend.get_problem_devices()


def show_problemas():
    """Identifica dispositivos con errores de hardware, controladores faltantes o estado degradado."""
    print_header("Diagnóstico de Dispositivos con Problemas", "Módulo 9 / Fallas de Hardware")

    data = recolectar_problemas()

    if "error" in data.get("detalle", {}):
        console.print(Panel(f"[red]Error: {data['detalle']['error']}[/red]", border_style="red"))
        return

    detalle = data.get("detalle", {})
    estado = data.get("estado", "NORMAL")
    evidencia = data.get("evidencia", "N/D")
    recomendaciones = data.get("recomendacion", [])

    errors = detalle.get("errores", [])
    degraded = detalle.get("degradados", [])
    unk_count = detalle.get("desconocidos", 0)
    journal_errors = detalle.get("journal_errores", [])
    nota_permisos = detalle.get("nota_permisos", "")

    if errors:
        table_err = Table(title="[bold red][!] Dispositivos en Estado ERROR[/bold red]", border_style="red")
        table_err.add_column("Dispositivo", style="bold red")
        table_err.add_column("Estado", justify="center")
        table_err.add_column("Clase", style="cyan")
        table_err.add_column("ID de Instancia", style="muted")

        for dev in errors:
            table_err.add_row(
                dev.get("FriendlyName", "Dispositivo"),
                print_status_badge("ERROR"),
                dev.get("Class", "N/D"),
                dev.get("InstanceId", "N/D")[:50]
            )
        console.print(table_err)
        console.print()

    if degraded:
        table_deg = Table(title="[bold yellow][!] Dispositivos en Estado DEGRADADO[/bold yellow]", border_style="yellow")
        table_deg.add_column("Dispositivo", style="bold yellow")
        table_deg.add_column("Estado", justify="center")
        table_deg.add_column("Clase", style="cyan")

        for dev in degraded:
            table_deg.add_row(
                dev.get("FriendlyName", "Dispositivo"),
                print_status_badge("DEGRADED"),
                dev.get("Class", "N/D")
            )
        console.print(table_deg)
        console.print()

    if journal_errors:
        table_jrn = Table(title="[bold red][!] Errores en Journal (systemd)[/bold red]", border_style="red")
        table_jrn.add_column("Entrada", style="bold red")
        table_jrn.add_column("Fuente", style="cyan")

        for dev in journal_errors:
            table_jrn.add_row(
                dev.get("FriendlyName", "Evento"),
                dev.get("Class", "Journal")
            )
        console.print(table_jrn)
        console.print()

    if unk_count > 0:
        console.print(f"[yellow][!] Se detectaron [bold]{unk_count}[/bold] dispositivos en estado Desconocido (Unknown).[/yellow]")
        console.print()

    if nota_permisos:
        console.print(f"[yellow]⚠ {nota_permisos}[/yellow]")
        console.print()

    if not errors and not degraded and unk_count == 0 and not journal_errors:
        panel_ok = Panel(
            f"{print_status_badge('OK')} [green]No se detectaron dispositivos con errores, fallas de controlador ni estados degradados en el árbol de hardware.[/green]",
            border_style="green",
            title="[bold green]Salud de Dispositivos[/bold green]"
        )
        console.print(panel_ok)
    else:
        total = len(errors) + len(degraded) + unk_count + len(journal_errors)
        panel_warn = Panel(
            f"{print_status_badge('CRITICO' if total > 2 else 'ADVERTENCIA')} [red]Se detectaron {total} incidentes en dispositivos del sistema. Revise los controladores o la conexión física del periférico.[/red]",
            border_style="red",
            title="[bold red]Atención Requerida[/bold red]"
        )
        console.print(panel_warn)

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
    resultado = recolectar_problemas()
    print(json.dumps(resultado, indent=2, ensure_ascii=False))