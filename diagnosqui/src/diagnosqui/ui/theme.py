import sys
from rich.console import Console
from rich.theme import Theme
from rich.panel import Panel
from rich.text import Text

# Forzar codificación UTF-8 en stdout y stderr para evitar fallas con charmap en consolas Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

custom_theme = Theme({
    "info": "cyan bold",
    "success": "green bold",
    "warning": "yellow bold",
    "danger": "red bold",
    "accent": "magenta bold",
    "muted": "bright_black",
    "title": "bold cyan",
    "highlight": "bold white on blue",
    "metric.label": "white",
    "metric.value": "bright_cyan bold",
    "badge.ok": "bold white on green",
    "badge.warn": "bold black on yellow",
    "badge.crit": "bold white on red",
})

console = Console(theme=custom_theme, legacy_windows=False)


def print_header(title: str, subtitle: str = ""):
    """Imprime un encabezado estilizado con bordes redondeados."""
    content = Text()
    content.append(f"  [>] {title.upper()}", style="title")
    if subtitle:
        content.append(f"  [{subtitle}]", style="muted")
    console.print()
    console.print(Panel(content, border_style="cyan", expand=False))


def print_status_badge(status: str) -> str:
    """Retorna un markup de Rich estilizado para el estado."""
    status_clean = status.upper().strip()
    if status_clean in ("OK", "NORMAL", "ACTIVO", "PASSED"):
        return "[badge.ok]  OK  [/badge.ok]"
    elif status_clean in ("ALERTA", "WARN", "WARNING", "MODERADO"):
        return "[badge.warn] WARN [/badge.warn]"
    elif status_clean in ("CRITICO", "CRITICAL", "ERROR", "FALLA", "DEGRADED"):
        return "[badge.crit] CRIT [/badge.crit]"
    else:
        return f"[muted]{status}[/muted]"
