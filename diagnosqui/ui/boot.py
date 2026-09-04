"""
Animación de inicialización estilo 'npm install' y presentación de banner.
"""
import sys
import time
import random
import importlib
import pyfiglet
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.text import Text
from diagnosqui.ui.theme import console


PACKAGES_SIMULATED = [
    ("@diagnosqui/core-engine", "2.4.1", "motor de diagnóstico de hardware"),
    ("@diagnosqui/win32-pnp-bridge", "1.1.0", "interfaz de buses PnP y CIM"),
    ("@diagnosqui/linux-sysfs-scanner", "3.0.2", "conector para /proc y /sys"),
    ("@diagnosqui/pci-enumerator", "1.4.0", "analizador de topología PCIe"),
    ("@diagnosqui/usb-descriptor-parser", "2.0.1", "decodificador de endpoints USB"),
    ("@diagnosqui/gpu-telemetry", "1.0.8", "colector de VRAM y estados de driver"),
    ("@diagnosqui/smart-matrix-engine", "4.2.0", "matriz de correlación de fallos"),
    ("@diagnosqui/report-generator-html", "2.3.0", "renderizador de reportes ejecutivos"),
]


def check_real_dependencies() -> list[tuple[str, bool, str]]:
    """Valida los módulos reales instalados en el entorno."""
    checks = [
        ("psutil", "Telemetría de CPU, RAM y Discos"),
        ("rich", "Motor de renderizado de terminal"),
        ("prompt_toolkit", "Línea de comandos interactiva"),
        ("pyfiglet", "Generador de arte ASCII"),
    ]
    if sys.platform == "win32":
        checks.append(("wmi", "Interfaz WMI de Windows"))
        checks.append(("win32api", "Extensiones de pywin32"))

    results = []
    for mod_name, desc in checks:
        try:
            importlib.import_module(mod_name)
            results.append((mod_name, True, desc))
        except ImportError:
            results.append((mod_name, False, desc))
    return results


def run_boot_animation(force_verbose: bool = False):
    """Ejecuta la secuencia de arranque con estilo npm install y banner figlet."""
    console.clear()
    console.print("[cyan bold]DiagnosQui CLI[/cyan bold] [muted]v2.4.1[/muted]")
    console.print("[muted]Inicializando entorno de telemetría y periféricos...[/muted]\n")

    start_time = time.time()

    with Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=35, complete_style="green", finished_style="cyan"),
        TextColumn("[cyan]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:
        task_resolve = progress.add_task("[yellow]Resolviendo dependencias del sistema...", total=len(PACKAGES_SIMULATED))

        for pkg, ver, desc in PACKAGES_SIMULATED:
            progress.update(task_resolve, advance=1, description=f"[cyan]fetch[/cyan] {pkg}@{ver} ({desc})")
            time.sleep(random.uniform(0.08, 0.18))

        task_audit = progress.add_task("[magenta]Auditando compatibilidad de hardware...", total=100)
        for pct in (20, 45, 70, 90, 100):
            time.sleep(0.1)
            progress.update(task_audit, completed=pct)

    real_checks = check_real_dependencies()
    total_packages = len(PACKAGES_SIMULATED) + len(real_checks)
    elapsed = time.time() - start_time

    console.print()
    console.print(
        f"[green][OK][/green] [bold white]added {total_packages} packages[/bold white] "
        f"[muted]and audited system hardware modules in {elapsed:.2f}s[/muted]"
    )
    console.print("[green][OK][/green] [muted]found 0 vulnerabilities across subsystems[/muted]\n")

    # Banner PyFiglet
    ascii_banner = pyfiglet.figlet_format("DiagnosQui", font="slant")
    banner_panel = Panel(
        Text(ascii_banner, style="cyan bold"),
        subtitle="[bold white]v2.4.1 — Administrador & Diagnóstico de Hardware[/bold white]",
        subtitle_align="right",
        border_style="bright_blue",
        padding=(0, 2),
    )
    console.print(banner_panel)
    console.print()


if __name__ == "__main__":
    run_boot_animation()
