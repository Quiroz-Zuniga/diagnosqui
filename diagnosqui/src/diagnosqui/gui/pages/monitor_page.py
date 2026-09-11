"""Historial en vivo y medición puntual usando el recolector de E/S existente."""

from __future__ import annotations
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QWidget
from diagnosqui.gui.widgets.common import button, label, page_layout
from diagnosqui.gui.widgets.chart_widget import ChartWidget


class MonitorPage(QWidget):
    io_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = page_layout(
            self,
            "Monitor en vivo",
            "Datos reales · 60 muestras por gráfica · porcentajes con umbrales de 70% y 90%",
        )
        self.updated = label("Esperando muestras…", "muted", True)
        layout.addWidget(self.updated)
        grid = QGridLayout()
        self.charts = {}
        for index, (key, title) in enumerate(
            (
                ("cpu", "CPU"),
                ("memory", "Memoria RAM"),
                ("disk", "Disco más activo"),
                ("network", "Interfaz más activa"),
            )
        ):
            chart = ChartWidget(title)
            self.charts[key] = chart
            grid.addWidget(chart, index // 2, index % 2)
        layout.addLayout(grid, 1)
        self.io_button = button("Medir E/S durante 1 segundo")
        self.io_button.clicked.connect(self.io_requested)
        layout.addWidget(self.io_button)
        self.io_result = label(
            "Las tasas sin porcentaje usan el acento de la plataforma.", "muted", True
        )
        layout.addWidget(self.io_result)

    def set_performance(self, snapshot: object) -> None:
        from datetime import datetime

        details = []
        for key, chart in self.charts.items():
            metric = getattr(snapshot, key)
            chart.add_sample(
                metric.graph_value, metric.unit, metric.percent, metric.detail
            )
            if key in {"disk", "network"}:
                details.append(metric.detail)
        self.updated.setText(
            f"Actualizado a las {datetime.now():%H:%M:%S}\n" + "\n".join(details)
        )

    def set_io(self, data: dict) -> None:
        if data.get("error"):
            self.io_result.setText(f"No se pudo medir E/S: {data['error']}")
            return
        disk, net = data.get("disk") or {}, data.get("net") or {}
        self.io_result.setText(
            f"En {data.get('duration', 'N/D')} s: lectura {disk.get('read_kb', 'N/D')} KB · "
            f"escritura {disk.get('write_kb', 'N/D')} KB · enviado {net.get('sent_kb', 'N/D')} KB · "
            f"recibido {net.get('recv_kb', 'N/D')} KB"
        )
