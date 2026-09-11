"""Tarjeta reutilizable para métricas y acceso al diagnóstico del componente."""

from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Signal, Slot, Qt, QSize
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QSizePolicy,
)
from diagnosqui.gui.widgets.common import button, label
from diagnosqui.gui.widgets.status_badge import StatusBadge
from diagnosqui.gui.widgets.icons import icon


class MetricCard(QFrame):
    activated = Signal(str)

    def __init__(self, key: str, title: str) -> None:
        super().__init__()
        self.key = key
        self.setProperty("role", "card")
        self.setMinimumHeight(124)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(3)
        heading = QHBoxLayout()
        heading.addWidget(label(title, "section"))
        heading.addStretch()
        open_button = button("")
        self.open_button = open_button
        open_button.setProperty("role", "detail")
        open_button.setFixedSize(28, 28)
        open_button.setIconSize(QSize(16, 16))
        open_button.setToolTip(f"Abrir diagnóstico de {title}")
        open_button.setAccessibleName(f"Abrir diagnóstico de {title}")
        open_button.clicked.connect(lambda: self.activated.emit(self.key))
        heading.addWidget(open_button)
        layout.addLayout(heading)
        self.value = label("N/D", "value")
        layout.addWidget(self.value)
        self.description = label("Pendiente de lectura", "muted")
        self.description.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self._detail = "Pendiente de lectura"
        layout.addWidget(self.description)
        self.badge = StatusBadge()
        layout.addWidget(self.badge)
        QApplication.instance().theme_manager.changed.connect(self.refresh_theme)
        self.refresh_theme()

    @Slot()
    def refresh_theme(self) -> None:
        self.open_button.setIcon(icon("chevron-right"))

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)
        self._elide_detail()

    def _elide_detail(self) -> None:
        self.description.setText(
            self.description.fontMetrics().elidedText(
                self._detail, Qt.TextElideMode.ElideRight, max(20, self.width() - 28)
            )
        )

    def update_metric(self, value: str, state: Optional[str], detail: str) -> None:
        self.value.setText(value)
        self.value.setToolTip(value)
        self._detail = " ".join(detail.split())
        self._elide_detail()
        self.description.setToolTip(detail)
        self.badge.set_state(state)
