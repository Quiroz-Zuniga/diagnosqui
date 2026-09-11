"""Tablas de resultados y detalles estructurados, sin representaciones de Python."""

from __future__ import annotations
from collections.abc import Mapping
from typing import Any
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
)
from diagnosqui.gui.theme import LABELS, PRIORITY
from diagnosqui.gui.widgets.status_badge import state_icon

FIELD_NAMES = {
    "os": "Sistema operativo",
    "version": "Versión",
    "platform": "Plataforma",
    "processor": "Procesador",
    "architecture": "Arquitectura",
    "hostname": "Equipo",
    "uptime": "Tiempo de actividad",
    "uptime_seconds": "Actividad (segundos)",
    "is_admin": "Permisos de administrador",
    "python": "Versión de Python",
    "total_gb": "Capacidad total (GB)",
    "disponible_gb": "Disponible (GB)",
    "usada_gb": "En uso (GB)",
    "used_gb": "En uso (GB)",
    "free_gb": "Libre (GB)",
    "device": "Dispositivo",
    "mountpoint": "Punto de montaje",
    "fstype": "Sistema de archivos",
    "percent": "Utilización (%)",
    "io_stats": "Estadísticas de E/S",
    "global_io": "Tráfico acumulado",
    "read_count": "Operaciones de lectura",
    "write_count": "Operaciones de escritura",
    "read_mb": "Lectura (MB)",
    "write_mb": "Escritura (MB)",
    "sent_mb": "Enviado (MB)",
    "recv_mb": "Recibido (MB)",
    "packets_sent": "Paquetes enviados",
    "packets_recv": "Paquetes recibidos",
    "errin": "Errores de entrada",
    "errout": "Errores de salida",
    "dropin": "Descartes de entrada",
    "dropout": "Descartes de salida",
    "FriendlyName": "Nombre",
    "InstanceId": "Identificador",
    "Status": "Estado",
    "Class": "Clase",
    "Problem": "Problema",
    "name": "Nombre",
    "speed_mbps": "Velocidad (Mbps)",
    "is_up": "Conectada",
    "mtu": "MTU",
    "mac": "MAC",
    "ipv4": "IPv4",
    "ipv6": "IPv6",
    "gpus": "Adaptadores gráficos",
    "vram_gb": "VRAM (GB)",
    "driver_version": "Versión del controlador",
    "status": "Estado",
    "drivers": "Controladores",
    "drivers_firmados": "Controladores firmados",
    "Driver": "Controlador",
    "OriginalFileName": "Archivo",
    "ClassName": "Clase",
    "ProviderName": "Fabricante",
    "HealthStatus": "Estado declarado",
    "MediaType": "Tipo de medio",
    "BusType": "Bus",
    "Size": "Capacidad",
    "Module Name": "Módulo",
    "Driver Type": "Tipo de controlador",
    "duration": "Duración (segundos)",
    "disk": "Disco",
    "net": "Red",
    "reads": "Lecturas",
    "writes": "Escrituras",
    "read_kb": "Leído (KB)",
    "write_kb": "Escrito (KB)",
    "sent_kb": "Enviado (KB)",
    "recv_kb": "Recibido (KB)",
}


def display_value(value: Any) -> str:
    if value is None or value == "":
        return "N/D"
    if isinstance(value, bool):
        return "Sí" if value else "No"
    if isinstance(value, float):
        return f"{value:,.2f}"
    return str(value)


class DiagnosticTable(QTableWidget):
    def __init__(self, priorities: bool = False) -> None:
        super().__init__(0, 5 if priorities else 4)
        self.priorities = priorities
        self.setHorizontalHeaderLabels(
            ["Componente", "Evidencia", "Estado", "Recomendación"]
            + (["Prioridad"] if priorities else [])
        )
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)
        self.verticalHeader().hide()
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.setMinimumHeight(180)
        self.verticalHeader().setMinimumSectionSize(28)
        QApplication.instance().theme_manager.changed.connect(self.refresh_theme)

    @Slot()
    def refresh_theme(self) -> None:
        for row in range(self.rowCount()):
            item = self.item(row, 2)
            if item is not None:
                item.setIcon(state_icon(item.data(Qt.ItemDataRole.UserRole)))

    def set_results(self, results: list[dict]) -> None:
        self.setRowCount(len(results))
        for row, result in enumerate(results):
            state = result.get("estado", "ADVERTENCIA")
            recommendations = result.get("recomendacion") or []
            values = [
                result.get("componente", "N/D"),
                result.get("evidencia", "N/D"),
                LABELS.get(state, "Sin datos"),
                " · ".join(recommendations) or "Sin recomendaciones del proveedor",
            ]
            if self.priorities:
                values.append(
                    {0: "Alta", 1: "Media", 2: "Baja"}.get(PRIORITY.get(state, 1))
                )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setToolTip(str(value))
                if column == 2:
                    item.setData(Qt.ItemDataRole.UserRole, state)
                    item.setIcon(state_icon(state))
                self.setItem(row, column, item)
        self.resizeRowsToContents()


class DetailTree(QTreeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setHeaderLabels(["Propiedad", "Valor"])
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.header().setStretchLastSection(True)
        self.setMinimumHeight(180)

    def set_details(self, details: dict) -> None:
        self.clear()
        budget = [2000]

        def add(parent: Any, key: str, value: Any) -> None:
            if budget[0] <= 0:
                return
            budget[0] -= 1
            name = FIELD_NAMES.get(key, key.replace("_", " ").capitalize())
            group = isinstance(value, (Mapping, list, tuple))
            item = QTreeWidgetItem(
                parent,
                [name, f"{len(value)} elementos" if group else display_value(value)],
            )
            item.setToolTip(1, item.text(1))
            if isinstance(value, Mapping):
                for child_key, child in value.items():
                    add(item, str(child_key), child)
            elif isinstance(value, (list, tuple)):
                for index, child in enumerate(value[:500], 1):
                    add(item, str(index), child)
                if len(value) > 500:
                    QTreeWidgetItem(
                        item,
                        [
                            "Vista limitada",
                            "Primeros 500 elementos; exportar para ver todos",
                        ],
                    )

        for key, value in details.items():
            add(self, str(key), value)
        self.expandToDepth(0)
