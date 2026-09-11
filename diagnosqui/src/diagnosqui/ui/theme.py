"""Paleta compartida por Rich, el prompt y el monitor Textual."""

from __future__ import annotations

import unicodedata

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.style import Style
from rich.text import Text
from rich.theme import Theme


BACKGROUND_COLOR = "#0a1118"
TEXT_COLOR = "#e5edf0"
MUTED_COLOR = "#80919b"
PRIMARY_COLOR = "#34d3c8"
NORMAL_COLOR = "#46e38a"
WARNING_COLOR = "#f2c66d"
CRITICAL_COLOR = "#ff6b6b"

WARNING_THRESHOLD = 70.0
CRITICAL_THRESHOLD = 90.0

PRIMARY_STYLE = Style(color=PRIMARY_COLOR, bold=True)
NORMAL_STYLE = Style(color=NORMAL_COLOR, bold=True)
WARNING_STYLE = Style(color=WARNING_COLOR, bold=True)
CRITICAL_STYLE = Style(color=CRITICAL_COLOR, bold=True)
MUTED_STYLE = Style(color=MUTED_COLOR)
TEXT_STYLE = Style(color=TEXT_COLOR)

DIAGNOSQUI_THEME = Theme(
    {
        "info": PRIMARY_STYLE,
        "success": NORMAL_STYLE,
        "warning": WARNING_STYLE,
        "danger": CRITICAL_STYLE,
        "normal": NORMAL_STYLE,
        "critical": CRITICAL_STYLE,
        "accent": PRIMARY_STYLE,
        "muted": MUTED_STYLE,
        "title": PRIMARY_STYLE,
        "highlight": Style(color=BACKGROUND_COLOR, bgcolor=PRIMARY_COLOR, bold=True),
        "metric.label": TEXT_STYLE,
        "metric.value": PRIMARY_STYLE,
        "badge.ok": Style(color=BACKGROUND_COLOR, bgcolor=NORMAL_COLOR, bold=True),
        "badge.warn": Style(color=BACKGROUND_COLOR, bgcolor=WARNING_COLOR, bold=True),
        "badge.crit": Style(color=BACKGROUND_COLOR, bgcolor=CRITICAL_COLOR, bold=True),
    }
)

# Compatibilidad para consumidores existentes de la interfaz.
custom_theme = DIAGNOSQUI_THEME
console = Console(theme=DIAGNOSQUI_THEME, legacy_windows=False)


def _normalize_status(status: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFD", status.strip().upper())
        if not unicodedata.combining(character)
    )


def style_for_status(status: str) -> Style:
    """Resuelve estados del contrato y los alias usados por módulos existentes."""
    normalized = _normalize_status(status)
    if normalized in {"NORMAL", "OK", "ACTIVO", "PASSED"}:
        return NORMAL_STYLE
    if normalized in {"ADVERTENCIA", "ALERTA", "WARN", "WARNING", "MODERADO"}:
        return WARNING_STYLE
    if normalized in {"CRITICO", "CRITICAL", "ERROR", "FALLA", "DEGRADED"}:
        return CRITICAL_STYLE
    return MUTED_STYLE


def style_for_percentage(value: float) -> Style:
    """Umbrales inclusivos: advertencia desde 70 %, crítico desde 90 %."""
    if value >= CRITICAL_THRESHOLD:
        return CRITICAL_STYLE
    if value >= WARNING_THRESHOLD:
        return WARNING_STYLE
    return NORMAL_STYLE


def print_header(title: str, subtitle: str = "") -> None:
    """Encabezado compatible con los consumidores anteriores de theme."""
    content = Text(f"  [>] {title.upper()}", style=PRIMARY_STYLE)
    if subtitle:
        content.append(f"  [{subtitle}]", style=MUTED_STYLE)
    console.print()
    console.print(Panel(content, border_style=PRIMARY_STYLE, expand=False))


def print_status_badge(status: str) -> str:
    """Retorna una insignia Rich; mantiene la API de los módulos existentes."""
    style = style_for_status(status)
    if style is NORMAL_STYLE:
        return "[badge.ok]  OK  [/badge.ok]"
    if style is WARNING_STYLE:
        return "[badge.warn] WARN [/badge.warn]"
    if style is CRITICAL_STYLE:
        return "[badge.crit] CRIT [/badge.crit]"
    return f"[muted]{escape(status)}[/muted]"
