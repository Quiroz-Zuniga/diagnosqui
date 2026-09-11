"""Presentación visual estilo npm: no instala paquetes ni inspecciona hardware."""

from __future__ import annotations

import time

import pyfiglet
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text

from diagnosqui.ui.theme import MUTED_STYLE, NORMAL_STYLE, PRIMARY_STYLE, console


# Rich denomina "dots" a esta secuencia de diez caracteres braille.
BRAILLE_SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

PACKAGES_SIMULATED = (
    ("os-probe", "1.8.0", "sondeo de sistema"),
    ("kernel-inspect", "0.9.3", "inspección de kernel"),
    ("driver-scan", "2.1.0", "catálogo de controladores"),
    ("memory-check", "1.3.2", "diagnóstico de memoria"),
    ("storage-probe", "1.5.0", "diagnóstico de almacenamiento"),
    ("network-check", "0.8.4", "pruebas de conectividad"),
    ("device-map", "1.2.1", "inventario de dispositivos"),
    ("report-kit", "1.0.0", "presentación de reportes"),
)


def run_boot_animation(force_verbose: bool = False) -> None:
    """Muestra el arranque; las salidas sin TTY se generan sin esperas.

    ``force_verbose`` añade las descripciones de los paquetes de ejemplo.
    La persistencia de la primera ejecución corresponde al punto de entrada.
    """
    animated = console.is_terminal and not console.is_dumb_terminal
    console.print("$ npm install -g diagnosqui", style=PRIMARY_STYLE, markup=False)
    console.print(
        "Simulación visual de instalación · paquetes de ejemplo", style=MUTED_STYLE
    )
    started = time.perf_counter()

    if not animated:
        console.print("resolviendo dependencias...", style=MUTED_STYLE)

    with Progress(
        SpinnerColumn("dots", style=PRIMARY_STYLE, finished_text="✔"),
        TextColumn("{task.description}", style=MUTED_STYLE, markup=False),
        console=console,
        transient=True,
        disable=not animated,
        refresh_per_second=12,
    ) as progress:
        task = progress.add_task("resolviendo dependencias...", total=None)
        if animated:
            time.sleep(0.35)
        for package, version, description in PACKAGES_SIMULATED:
            progress.update(task, description=f"preparando {package}@{version}...")
            if animated:
                time.sleep(0.30)
            line = Text("✔ ", style=NORMAL_STYLE)
            line.append(f"{package}@{version}")
            if force_verbose:
                line.append(f"  {description}", style=MUTED_STYLE)
            progress.console.print(line)

    elapsed = time.perf_counter() - started
    console.print(
        f"added {len(PACKAGES_SIMULATED)} packages in {elapsed:.1f}s",
        style=NORMAL_STYLE,
        markup=False,
    )
    console.print()
    # El tipo compacto conserva la legibilidad en terminales estrechas.
    font = "slant" if console.width >= 76 else "small"
    banner = pyfiglet.figlet_format("DiagnosQui", font=font, width=console.width)
    console.print(Text(banner.rstrip(), style=PRIMARY_STYLE))
    console.print("DiagnosQui · Diagnóstico de hardware", style=PRIMARY_STYLE)
    console.print()


if __name__ == "__main__":
    run_boot_animation()
