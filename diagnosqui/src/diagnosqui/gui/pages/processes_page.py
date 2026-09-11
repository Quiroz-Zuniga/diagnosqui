"""Procesos reales con búsqueda y orden numérico mediante modelo y proxy Qt."""

from __future__ import annotations
from typing import Any
from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QHBoxLayout,
    QLineEdit,
    QTableView,
    QWidget,
)
from diagnosqui.gui.widgets.common import button, label, page_layout

PROCESS_STATES = {
    "running": "En ejecución",
    "sleeping": "En espera",
    "disk-sleep": "Espera de E/S",
    "stopped": "Detenido",
    "tracing-stop": "En depuración",
    "zombie": "Zombi",
    "dead": "Finalizado",
    "idle": "Inactivo",
    "locked": "Bloqueado",
    "waiting": "Esperando",
    "waking": "Activándose",
    "parked": "En pausa",
    "suspended": "Suspendido",
}


class ProcessModel(QAbstractTableModel):
    HEADERS = ("PID", "Nombre", "CPU %", "Memoria %", "Usuario", "Estado")

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[Any] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.HEADERS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or index.row() >= len(self.rows):
            return None
        row = self.rows[index.row()]
        values = (
            row.pid,
            row.name,
            row.cpu_percent,
            row.memory_percent,
            row.username,
            PROCESS_STATES.get(row.status, "N/D"),
        )
        value = values[index.column()]
        if role == Qt.ItemDataRole.UserRole:
            return value
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole):
            return f"{value:.1f}" if isinstance(value, float) else str(value)
        if role == Qt.ItemDataRole.TextAlignmentRole and index.column() in (0, 2, 3):
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
        ):
            return self.HEADERS[section]
        return None

    def replace(self, rows: list[Any]) -> None:
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()


class ProcessesPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.paused = False
        layout = page_layout(
            self, "Procesos", "CPU normalizada al total de núcleos · Solo lectura"
        )
        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar por nombre, PID o usuario…")
        self.search.setAccessibleName("Buscar procesos")
        toolbar.addWidget(self.search, 1)
        for title, column in (("Ordenar CPU", 2), ("Ordenar memoria", 3)):
            sort = button(title)
            sort.clicked.connect(
                lambda checked=False, col=column: self.table.sortByColumn(
                    col, Qt.SortOrder.DescendingOrder
                )
            )
            toolbar.addWidget(sort)
        self.pause_button = button("Pausar")
        self.pause_button.clicked.connect(self.toggle_pause)
        toolbar.addWidget(self.pause_button)
        layout.addLayout(toolbar)
        self.model = ProcessModel()
        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterKeyColumn(-1)
        self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy.setSortRole(Qt.ItemDataRole.UserRole)
        self.search.textChanged.connect(self.proxy.setFilterFixedString)
        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.sortByColumn(2, Qt.SortOrder.DescendingOrder)
        layout.addWidget(self.table, 1)
        self.summary = label("Esperando procesos…", "muted")
        layout.addWidget(self.summary)

    def toggle_pause(self) -> None:
        self.paused = not self.paused
        self.pause_button.setText("Reanudar" if self.paused else "Pausar")
        self.summary.setText(
            "Actualización pausada" if self.paused else "Actualización reanudada"
        )

    def set_processes(self, rows: list[Any]) -> None:
        if self.paused:
            return
        scroll = self.table.verticalScrollBar().value()
        selected = self.table.currentIndex()
        pid = (
            self.proxy.index(selected.row(), 0).data(Qt.ItemDataRole.UserRole)
            if selected.isValid()
            else None
        )
        self.model.replace(rows)
        if pid is not None:
            for index, row in enumerate(rows):
                if row.pid == pid:
                    self.table.setCurrentIndex(
                        self.proxy.mapFromSource(self.model.index(index, 0))
                    )
                    break
        self.table.verticalScrollBar().setValue(scroll)
        self.summary.setText(
            f"{len(rows)} procesos accesibles · {self.proxy.rowCount()} coinciden con la búsqueda"
        )
