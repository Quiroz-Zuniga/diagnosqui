"""
Módulo para visualización y diagnóstico de buses PCI, PCIe y subsistemas ACPI.
"""
from rich.table import Table
from rich.panel import Panel
from diagnosqui.core.platform_utils import get_backend
from diagnosqui.ui.theme import console, print_header, print_status_badge


def show_pci():
    """Muestra la topología de buses PCI/PCIe, controladores host y periféricos ACPI."""
    print_header("Diagnóstico de Buses PCI / PCIe", "Módulo 7 / Topología PCI")

    backend = get_backend()
    data = backend.get_pci_devices()

    pci_devs = data["pci_devices"]
    bus_devs = data["usb_bus_devices"]

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
            status = dev.get("Status", "OK")
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
            bus_table.add_row(
                b.get("FriendlyName", "Endpoint"),
                print_status_badge(b.get("Status", "OK")),
                b.get("InstanceId", "N/D")[:45]
            )
        console.print(bus_table)
