"""
Módulo para visualización y diagnóstico de interfaces de red, tráfico y conectividad.
"""
import json
from rich.table import Table
from rich.panel import Panel
from diagnosqui.core.platform_utils import get_backend, get_connectivity_info
from diagnosqui.ui.theme import console, print_header, print_status_badge


def recolectar_red() -> dict:
    """Recolecta datos de interfaces de red y devuelve el CONTRATO UNIFICADO."""
    backend = get_backend()
    return backend.get_network_info()


def recolectar_conectividad() -> dict:
    """Recolecta datos de conectividad y devuelve el CONTRATO UNIFICADO."""
    return get_connectivity_info()


def show_red():
    """Muestra adaptadores de red, direcciones asignadas, telemetría y conectividad."""
    print_header("Diagnóstico de Interfaces de Red", "Módulo 5 / Red")

    # Red (interfaces)
    data = recolectar_red()

    if "error" in data.get("detalle", {}):
        console.print(Panel(f"[red]Error en interfaces: {data['detalle']['error']}[/red]", border_style="red"))
    else:
        detalle = data.get("detalle", {})
        estado = data.get("estado", "NORMAL")
        evidencia = data.get("evidencia", "N/D")
        recomendaciones = data.get("recomendacion", [])

        interfaces = detalle.get("interfaces", [])
        apipa = detalle.get("apipa_detectada", False)

        table = Table(title="[bold white]Adaptadores de Red[/bold white]", border_style="cyan")
        table.add_column("Interfaz", style="cyan bold")
        table.add_column("Estado", justify="center")
        table.add_column("Velocidad", justify="right")
        table.add_column("IPv4", style="white")
        table.add_column("MAC", style="muted")

        for iface in interfaces:
            status_badge = print_status_badge("ACTIVO" if iface["is_up"] else "INACTIVO")
            ipv4_str = ", ".join(iface["ipv4"]) if iface["ipv4"] else "[muted]Sin IPv4[/muted]"
            if apipa and iface["ipv4"]:
                ipv4_str += " [red](APIPA)[/red]"
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
        global_io = detalle.get("global_io", {})
        io_table = Table(show_header=False, box=None, padding=(0, 2))
        io_table.add_column("Métrica", style="cyan bold")
        io_table.add_column("Valor", style="white")

        io_table.add_row("Tráfico Enviado", f"[green]{global_io.get('sent_mb', 0):.2f} MB[/green]")
        io_table.add_row("Tráfico Recibido", f"[cyan]{global_io.get('recv_mb', 0):.2f} MB[/cyan]")
        io_table.add_row("Paquetes TX / RX", f"{global_io.get('packets_sent', 0):,} / {global_io.get('packets_recv', 0):,}")
        io_table.add_row(
            "Errores Entrada / Salida",
            f"[red]{global_io.get('errin', 0)}[/red] / [red]{global_io.get('errout', 0)}[/red]"
            if (global_io.get('errin', 0) or global_io.get('errout', 0))
            else "[green]0 / 0 (Sin errores)[/green]"
        )
        io_table.add_row(
            "Paquetes Descartados",
            f"[yellow]{global_io.get('dropin', 0) + global_io.get('dropout', 0)}[/yellow]"
            if (global_io.get('dropin', 0) or global_io.get('dropout', 0))
            else "[green]0 (Sin descartes)[/green]"
        )

        console.print(Panel(io_table, border_style="bright_blue", title="[bold white]Estadísticas Globales de E/S de Red[/bold white]"))
        console.print()

        # Estado global de red
        status_table = Table(show_header=False, box=None)
        status_table.add_column("Label", style="bold")
        status_table.add_column("Value")
        status_table.add_row("Estado:", f"{print_status_badge(estado)} {evidencia}")

        if recomendaciones:
            for rec in recomendaciones:
                status_table.add_row("Recomendación:", f"[cyan]→ {rec}[/cyan]")

        border_color = "yellow" if estado == "ADVERTENCIA" else ("red" if estado == "CRITICO" else "green")
        console.print(Panel(status_table, border_style=border_color))

    # Conectividad
    console.print()
    print_header("Conectividad de Red", "Módulo 5.1 / Conectividad")

    conn_data = recolectar_conectividad()

    if "error" in conn_data.get("detalle", {}):
        console.print(Panel(f"[red]Error en conectividad: {conn_data['detalle']['error']}[/red]", border_style="red"))
        return

    conn_detalle = conn_data.get("detalle", {})
    conn_estado = conn_data.get("estado", "NORMAL")
    conn_evidencia = conn_data.get("evidencia", "N/D")
    conn_recomendaciones = conn_data.get("recomendacion", [])

    conn_table = Table(show_header=False, box=None, padding=(0, 2))
    conn_table.add_column("Comprobación", style="cyan bold")
    conn_table.add_column("Resultado", justify="center")

    gw_ok = conn_detalle.get("gateway_ok", False)
    inet_ok = conn_detalle.get("internet_ok", False)
    dns_ok = conn_detalle.get("dns_ok", False)
    gw_ip = conn_detalle.get("gateway_ip", "N/D")
    dns_servers = conn_detalle.get("dns_servers", [])

    conn_table.add_row("Gateway", f"{gw_ip} — {'[green]OK[/green]' if gw_ok else '[red]FAIL[/red]'}")
    conn_table.add_row("Internet (8.8.8.8)", f"{'[green]OK[/green]' if inet_ok else '[red]FAIL[/red]'}")
    conn_table.add_row("Resolución DNS (google.com)", f"{'[green]OK[/green]' if dns_ok else '[red]FAIL[/red]'}")

    console.print(conn_table)
    console.print()

    if dns_servers:
        dns_table = Table(show_header=False, box=None, padding=(0, 2))
        dns_table.add_column("Servidor DNS", style="cyan")
        for dns in dns_servers:
            dns_table.add_row(dns)
        console.print(Panel(dns_table, border_style="bright_blue", title="[bold white]Servidores DNS[/bold white]"))
        console.print()

    # Estado conectividad
    status_table = Table(show_header=False, box=None)
    status_table.add_column("Label", style="bold")
    status_table.add_column("Value")
    status_table.add_row("Estado:", f"{print_status_badge(conn_estado)} {conn_evidencia}")

    if conn_recomendaciones:
        for rec in conn_recomendaciones:
            status_table.add_row("Recomendación:", f"[cyan]→ {rec}[/cyan]")

    border_color = "yellow" if conn_estado == "ADVERTENCIA" else ("red" if conn_estado == "CRITICO" else "green")
    console.print(Panel(status_table, border_style=border_color))


if __name__ == "__main__":
    # Imprimir ambos contratos
    resultado_red = recolectar_red()
    resultado_conn = recolectar_conectividad()
    print(json.dumps({
        "red": resultado_red,
        "conectividad": resultado_conn
    }, indent=2, ensure_ascii=False))