"""Presentación consistente de un contrato de diagnóstico."""

from __future__ import annotations
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QProgressBar, QScrollArea, QVBoxLayout, QWidget
from diagnosqui.gui.widgets.common import button, label, page_layout
from diagnosqui.gui.widgets.diagnostic_table import DetailTree
from diagnosqui.gui.widgets.status_badge import StatusBadge


class ComponentPage(QWidget):
    requested = Signal(str)

    def __init__(self, key: str, title: str, description: str) -> None:
        super().__init__()
        self.key = key
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        content = QWidget()
        layout = page_layout(content, title, description)
        self.scroll.setWidget(content)
        outer.addWidget(self.scroll)
        toolbar = QHBoxLayout()
        self.badge = StatusBadge()
        toolbar.addWidget(self.badge)
        toolbar.addStretch()
        self.run_button = button("Ejecutar diagnóstico", True)
        self.run_button.clicked.connect(lambda: self.requested.emit(self.key))
        toolbar.addWidget(self.run_button)
        layout.addLayout(toolbar)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)
        self.error = label("", "error", True)
        self.error.hide()
        layout.addWidget(self.error)
        self.evidence = label(
            "Ejecuta el diagnóstico para consultar este componente.", "section", True
        )
        layout.addWidget(self.evidence)
        self.numeric = label("Valor: N/D", "muted")
        layout.addWidget(self.numeric)
        self.details = DetailTree()
        layout.addWidget(self.details, 1)
        layout.addWidget(label("Recomendaciones", "section"))
        self.recommendations = label("Pendientes de diagnóstico", wrap=True)
        layout.addWidget(self.recommendations)
        self.timestamp = label("Sin ejecutar", "muted")
        layout.addWidget(self.timestamp)

    def set_busy(self, busy: bool) -> None:
        self.run_button.setDisabled(busy)
        self.run_button.setText("Leyendo datos…" if busy else "Ejecutar diagnóstico")
        self.progress.setVisible(busy)

    def show_error(self, message: str) -> None:
        self.error.setText(message)
        self.error.setVisible(bool(message))

    def set_result(self, result: dict) -> None:
        detail = result.get("detalle") or {}
        self.badge.set_state(result.get("estado"))
        self.evidence.setText(result.get("evidencia", "N/D"))
        number = result.get("valor_numerico")
        self.numeric.setText(
            "Valor: N/D" if number is None else f"Valor numérico: {number:g}"
        )
        self.details.set_details(detail)
        self.recommendations.setText(
            "\n".join(
                result.get("recomendacion")
                or ["El proveedor no emitió recomendaciones."]
            )
        )
        self.timestamp.setText(
            f"Ejecutado: {detail.get('ejecutado_en', 'N/D')} · Fuente: {detail.get('fuente', 'N/D')}"
        )
        self.show_error(str(detail.get("error", "")))
