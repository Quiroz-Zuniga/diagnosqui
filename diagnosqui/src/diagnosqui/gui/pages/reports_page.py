"""Resumen de diagnóstico y exportación desde diálogos de escritorio."""

from __future__ import annotations
from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QComboBox, QFileDialog, QHBoxLayout, QLineEdit, QWidget
from diagnosqui.gui.widgets.common import button, label, page_layout
from diagnosqui.gui.widgets.diagnostic_table import DiagnosticTable


class ReportsPage(QWidget):
    requested = Signal()
    export_requested = Signal(str, object)

    def __init__(self, directory: str) -> None:
        super().__init__()
        layout = page_layout(
            self, "Reportes", "Revisa los resultados antes de exportarlos a un archivo."
        )
        self.run_button = button("Ejecutar diagnóstico completo", True)
        self.run_button.clicked.connect(self.requested)
        layout.addWidget(self.run_button)
        self.source = label("Sin diagnóstico disponible", "muted", True)
        layout.addWidget(self.source)
        self.table = DiagnosticTable()
        layout.addWidget(self.table, 1)
        destination = QHBoxLayout()
        self.directory = QLineEdit(directory)
        self.directory.setAccessibleName("Carpeta de destino de reportes")
        destination.addWidget(self.directory, 1)
        choose = button("Elegir carpeta…")
        choose.clicked.connect(self.choose_directory)
        destination.addWidget(choose)
        layout.addLayout(destination)
        toolbar = QHBoxLayout()
        self.format = QComboBox()
        self.format.setAccessibleName("Formato del reporte")
        for title, formats in (
            ("Todos los formatos", ("json", "csv", "html")),
            ("JSON", ("json",)),
            ("CSV", ("csv",)),
            ("HTML", ("html",)),
        ):
            self.format.addItem(title, formats)
        toolbar.addWidget(self.format)
        self.export_button = button("Exportar", True)
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(
            lambda: self.export_requested.emit(
                self.directory.text(), self.format.currentData()
            )
        )
        toolbar.addWidget(self.export_button)
        self.open_button = button("Abrir carpeta")
        self.open_button.clicked.connect(self.open_directory)
        toolbar.addWidget(self.open_button)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        self.message = label("", "muted", True)
        self.message.setTextInteractionFlags(
            self.message.textInteractionFlags()
            | Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.message)
        self.has_results = False
        self.busy = False
        self.last_directory = ""

    def choose_directory(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self, "Elegir carpeta de reportes", self.directory.text()
        )
        if selected:
            self.directory.setText(selected)

    def open_directory(self) -> None:
        from pathlib import Path

        path = Path(self.last_directory or self.directory.text()).expanduser()
        if not path.is_dir() or not QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(path.resolve()))
        ):
            self.message.setText(
                "No se pudo abrir la carpeta. Comprueba que exista y que el escritorio tenga un gestor de archivos."
            )

    def set_results(self, results: dict) -> None:
        self.has_results = bool(results)
        self.table.set_results(list(results.values()))
        sources = {
            result.get("detalle", {}).get("fuente", "N/D")
            for result in results.values()
        }
        self.source.setText(
            f"{len(results)} componentes · Fuente: {', '.join(sorted(sources))} · Se exporta este diagnóstico, sin volver a consultar hardware."
        )
        self.export_button.setEnabled(self.has_results and not self.busy)

    def set_busy(self, busy: bool) -> None:
        self.busy = busy
        self.run_button.setDisabled(busy)
        self.export_button.setEnabled(self.has_results and not busy)
        self.run_button.setText(
            "Procesando…" if busy else "Ejecutar diagnóstico completo"
        )
