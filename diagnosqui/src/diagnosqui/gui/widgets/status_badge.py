"""Estado visible mediante texto e icono vectorial, además del color."""

from __future__ import annotations

from typing import Optional
from PySide6.QtGui import QIcon
from PySide6.QtCore import QSize, Slot
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QWidget
from diagnosqui.gui.theme import LABELS, state_color
from diagnosqui.gui.widgets.common import label
from diagnosqui.gui.widgets.icons import icon


def state_icon(state: Optional[str]) -> QIcon:
    name = {
        "NORMAL": "circle-check",
        "ADVERTENCIA": "triangle-alert",
        "CRITICO": "circle-alert",
    }.get(state, "circle-help")
    return icon(name, state_color(state))


class StatusBadge(QWidget):
    def __init__(
        self, state: Optional[str] = None, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        self.icon = QLabel()
        self.text = label()
        layout.addWidget(self.icon)
        layout.addWidget(self.text)
        layout.addStretch()
        self.set_state(state)
        QApplication.instance().theme_manager.changed.connect(self.refresh_theme)

    @Slot()
    def refresh_theme(self) -> None:
        self.set_state(self.state, self.text.text())

    def set_state(self, state: Optional[str], text: str = "") -> None:
        self.state = state
        self.icon.setPixmap(
            state_icon(state).pixmap(QSize(18, 18), self.devicePixelRatioF())
        )
        self.text.setText(text or LABELS.get(state, "Sin datos"))
        self.text.setStyleSheet(f"color: {state_color(state)}; font-weight: 600;")
        self.setAccessibleName(self.text.text())
