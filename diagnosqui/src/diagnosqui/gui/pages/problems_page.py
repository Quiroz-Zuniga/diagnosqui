"""Incidencias ordenadas por gravedad y detalle del registro seleccionado."""

from __future__ import annotations
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget
from diagnosqui.gui.theme import PRIORITY
from diagnosqui.gui.widgets.common import button, label, page_layout
from diagnosqui.gui.widgets.diagnostic_table import DetailTree, DiagnosticTable


class ProblemsPage(QWidget):
    requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = page_layout(
            self,
            "Dispositivos con problemas",
            "Incidencias y recomendaciones del diagnóstico completo, por prioridad.",
        )
        self.run_button = button("Actualizar diagnóstico completo", True)
        self.run_button.clicked.connect(self.requested)
        layout.addWidget(self.run_button)
        self.message = label(
            "Ejecuta un diagnóstico para comprobar las incidencias.", "muted", True
        )
        layout.addWidget(self.message)
        self.table = DiagnosticTable(priorities=True)
        self.table.itemSelectionChanged.connect(self._selected)
        layout.addWidget(self.table, 2)
        self.details = DetailTree()
        layout.addWidget(self.details, 1)
        self.rows: list[dict] = []

    def set_results(self, results: dict) -> None:
        self.rows = sorted(
            results.values(), key=lambda result: PRIORITY.get(result.get("estado"), 1)
        )
        issues = sum(result.get("estado") != "NORMAL" for result in self.rows)
        self.message.setText(
            f"{issues} componentes requieren atención"
            if issues
            else "No se detectaron incidencias en los componentes consultados."
        )
        self.table.setVisible(bool(issues))
        self.details.setVisible(bool(issues))
        self.table.set_results(self.rows)
        if issues:
            self.table.selectRow(0)

    def _selected(self) -> None:
        index = self.table.currentRow()
        if 0 <= index < len(self.rows):
            self.details.set_details(self.rows[index].get("detalle") or {})
