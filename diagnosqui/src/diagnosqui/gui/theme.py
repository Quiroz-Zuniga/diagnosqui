"""Estados del diagnóstico y acceso a los tokens visuales de la aplicación."""

from __future__ import annotations
from typing import Optional
import math
from diagnosqui.core.estados import clasificar_porcentaje
from diagnosqui.gui.visual_tokens import COLORS as COLORS, VisualTokens, build_tokens

LABELS = {"NORMAL": "Normal", "ADVERTENCIA": "Advertencia", "CRITICO": "Crítico"}
PRIORITY = {"CRITICO": 0, "ADVERTENCIA": 1, "NORMAL": 2}


def current_tokens() -> VisualTokens:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    manager = getattr(app, "theme_manager", None)
    return manager.tokens if manager is not None else build_tokens()


def state_color(state: Optional[str]) -> str:
    return current_tokens().state_ink(state or "")


def percentage_state(value: Optional[float]) -> Optional[str]:
    """Se conserva el contrato de core: NORMAL / ADVERTENCIA / CRITICO (70/90)."""
    return None if value is None else clasificar_porcentaje(value)


def format_percentage(value: Optional[float]) -> str:
    """El redondeo visible nunca cruza un umbral que la muestra no alcanzó."""
    if value is None or not math.isfinite(value):
        return "N/D"
    rounded = round(value, 1)
    if percentage_state(rounded) != percentage_state(value):
        rounded = math.floor(value * 10) / 10
    return f"{rounded:.1f} %"
