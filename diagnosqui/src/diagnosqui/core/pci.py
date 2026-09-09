"""
Módulo para visualización y diagnóstico de buses PCI, PCIe y subsistemas ACPI.
"""
import json
from rich.table import Table
from rich.panel import Panel
from diagnosqui.core.platform_utils import get_backend
from diagnosqui.ui.theme import console, print_header, print_status_badge


def recolectar_pci() -> dict:
    """Recolecta datos de PCI y devuelve el CONTRATO UNIFICADO."""
    backend = get_backend()
    return backend.get_pci_devices()


def show_pci():
    """Muestra la topología de buses PCI/PCIe, controladores host y periféricos ACPI."""
    print_header("Diagnóstico de Buses PCI / PCIe", "Módulo 7 / Topología PCI")

    data = recolectar_pci()

    if "error" in data.get("detalle", {}):
        console.print(Panel(f"[red]Error: {data['detalle']['error']}[/red]", border_style="red"))
        return

    detalle = data.get("detalle", {})
    estado = data.get("estado", "NORMAL")
    evidencia = data.get("evidencia", "N/D")
    recomendaciones = data.get("recomendacion", [])

    pci_devs = detalle.get("dispositivos", [])
    bus_devs = detalle.get("buses_usb", [])

    if pci_devs:
        table = Table(
            title=f"[bold white]Dispositivos PCI / PCIe / ACPI Detectados ({len(pci_devs)})[/bold white]",
            border_style="cyan"
        )
        table.add_column("Dispositivo", style="bold white")
        table.add_column("Estado", justify="center")
        table.add_column("Clase de Bus", style="magenta")
        table.add_column("ID de Hardware / Instancia", style="muted")

        for dev in pci_devs[:35]:  # Mostrar los primeros 35 para legibilidad
            status = dev.get("estado_clasificado", dev.get("Status", "OK"))
            badge = print_status_badge(status)
            table.add_row(
                dev.get("FriendlyName", "Dispositivo PCI"),
                badge,
                dev.get("Class", "PCI"),
                dev.get("InstanceId", "N/D")[:50]
            )

        console.print(table)
        if len(pci_devs) > 35:
            console.print(f"[muted]... y {len(pci_devs) - 35} dispositivos PCI adicionales no listados.[/muted]")
    else:
        console.print("[yellow]No se detectaron dispositivos PCI o se requiere ejecución con privilegios elevados.[/yellow]")

    console.print()

    if bus_devs:
        bus_table = Table(title="[bold white]Controladores y Endpoints de Bus[/bold white]", border_style="bright_blue")
        bus_table.add_column("Nombre", style="bold white")
        bus_table.add_column("Estado", justify="center")
        bus_table.add_column("Instancia", style="muted")

        for b in bus_devs[:15]:
            status = b.get("estado_clasificado", b.get("Status", "OK"))
            bus_table.add_row(
                b.get("FriendlyName", "Endpoint"),
                print_status_badge(status),
                b.get("InstanceId", "N/D")[:45]
            )
        console.print(bus_table)

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
    resultado = recolectar_pci()
    print(json.dumps(resultado, indent=2, ensure_ascii=False))