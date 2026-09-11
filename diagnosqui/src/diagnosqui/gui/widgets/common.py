"""Pequeñas convenciones de composición y texto seguro para widgets Qt."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


def label(text: str = "", role: str = "", wrap: bool = False) -> QLabel:
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(wrap)
    if role:
        widget.setProperty("role", role)
    return widget


def button(text: str, primary: bool = False) -> QPushButton:
    widget = QPushButton(text)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    widget.setMinimumHeight(34)
    if primary:
        widget.setProperty("role", "primary")
    return widget


def page_layout(page: QWidget, title: str, description: str) -> QVBoxLayout:
    layout = QVBoxLayout(page)
    layout.setContentsMargins(20, 16, 20, 12)
    layout.setSpacing(10)
    layout.addWidget(label(title, "title"))
    layout.addWidget(label(description, "muted", True))
    return layout
