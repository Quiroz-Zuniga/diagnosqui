"""Iconos Lucide distribuidos con el paquete, renderizados por Qt a alta densidad."""

from __future__ import annotations
from functools import lru_cache
from pathlib import Path
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from diagnosqui.gui.theme import current_tokens

DIRECTORY = Path(__file__).parents[1] / "resources" / "icons"
NAV_ICONS = {
    "inicio": "house",
    "sistema": "computer",
    "cpu": "cpu",
    "memoria": "memory-stick",
    "disco": "hard-drive",
    "red": "network",
    "usb": "usb",
    "pci": "circuit-board",
    "gpu": "monitor",
    "controladores": "cable",
    "problemas": "triangle-alert",
    "procesos": "list",
    "monitor": "activity",
    "reportes": "file-text",
    "configuracion": "settings",
}


@lru_cache(maxsize=32)
def _source(name: str) -> str:
    return (DIRECTORY / f"{name}.svg").read_text(encoding="utf-8")


def icon(name: str, color: str = "") -> QIcon:
    tokens = current_tokens()
    result = QIcon()
    for state, ink in (
        (QIcon.State.Off, color or tokens.text_secondary),
        (QIcon.State.On, color or tokens.accent_ink),
    ):
        svg = _source(name).replace("currentColor", ink)
        renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        pixmap = QPixmap(48, 48)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        pixmap.setDevicePixelRatio(2)
        result.addPixmap(pixmap, QIcon.Mode.Normal, state)
    return result
