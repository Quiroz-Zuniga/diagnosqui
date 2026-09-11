"""Resumen del equipo con contratos reales y telemetría compartida."""

from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QScrollArea, QVBoxLayout, QWidget
from diagnosqui.gui.widgets.common import label, page_layout
from diagnosqui.gui.widgets.chart_widget import ChartWidget
from diagnosqui.gui.widgets.metric_card import MetricCard
from diagnosqui.gui.theme import format_percentage, percentage_state


class DashboardPage(QWidget):
    navigate = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        self.scroll = scroll
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = page_layout(
            content,
            "Resumen del equipo",
            "Una vista de tu hardware, su estado y su actividad reciente.",
        )
        self.identity = label("Recopilando información del equipo…", "muted", True)
        layout.addWidget(self.identity)
        grid = QGridLayout()
        grid.setSpacing(12)
        self.cards = {}
        for index, (key, title) in enumerate(
            (
                ("cpu", "CPU"),
                ("memoria", "Memoria RAM"),
                ("disco", "Disco principal"),
                ("red", "Red"),
                ("gpu", "GPU"),
                ("problemas", "Incidencias"),
            )
        ):
            card = MetricCard(key, title)
            card.activated.connect(self.navigate)
            self.cards[key] = card
            grid.addWidget(card, index // 3, index % 3)
            grid.setColumnStretch(index % 3, 1)
        layout.addLayout(grid)
        layout.addWidget(label("Actividad reciente", "section"))
        charts = QGridLayout()
        self.charts = {}
        for index, (key, name) in enumerate(
            (
                ("cpu", "CPU"),
                ("memory", "Memoria"),
                ("disk", "Actividad de disco"),
                ("network", "Tráfico de red"),
            )
        ):
            self.charts[key] = ChartWidget(name)
            charts.addWidget(self.charts[key], 0, index)
        layout.addLayout(charts)
        self.updated = label("Última actualización: pendiente", "muted")
        layout.addWidget(self.updated)
        scroll.setWidget(content)
        outer.addWidget(scroll)
        self.results: dict = {}

    def set_results(self, results: dict) -> None:
        self.results.update(results)
        system = self.results.get("sistema", {}).get("detalle", {})
        cpu = self.results.get("cpu", {}).get("detalle", {})
        memory = self.results.get("memoria", {}).get("detalle", {})
        total = memory.get("total_gb")
        installed = f"{total:g} GB" if isinstance(total, (int, float)) else "N/D"
        self.identity.setText(
            f"{system.get('hostname', 'N/D')}  ·  {system.get('os', 'N/D')}  ·  {system.get('architecture', 'N/D')}\n"
            f"{cpu.get('modelo', system.get('processor', 'N/D'))}  ·  RAM instalada: {installed}  ·  Actividad: {system.get('uptime', 'N/D')}"
        )
        for key, result in results.items():
            if key not in self.cards:
                continue
            value = result.get("valor_numerico")
            state = result.get("estado")
            evidence = result.get("evidencia", "N/D")
            if key == "disco":
                partitions = result.get("detalle", {}).get("particiones") or []
                primary = next(
                    (
                        part
                        for part in partitions
                        if isinstance(part, dict)
                        and part.get("mountpoint") == Path.home().anchor
                    ),
                    {},
                )
                value = primary.get("percent")
                state = percentage_state(value)
                evidence = str(
                    primary.get("device", "Partición del sistema no disponible")
                )
            if key in {"cpu", "memoria", "disco"}:
                display = format_percentage(value)
            elif key == "gpu":
                display = (
                    "Detectada" if result.get("detalle", {}).get("gpus") else "N/D"
                )
            elif key == "problemas":
                display = str(int(value)) if value is not None else "N/D"
            else:
                display = f"{int(value)} activas" if value is not None else "N/D"
            self.cards[key].update_metric(display, state, evidence)
            self.updated.setText(
                f"Último diagnóstico: {result.get('detalle', {}).get('ejecutado_en', 'N/D')}"
            )

    def set_performance(self, snapshot: object) -> None:
        for key, chart in self.charts.items():
            metric = getattr(snapshot, key)
            chart.add_sample(
                metric.graph_value, metric.unit, metric.percent, metric.detail
            )
        for key, attribute in (("cpu", "cpu"), ("memoria", "memory")):
            metric = getattr(snapshot, attribute)
            self.cards[key].update_metric(
                format_percentage(metric.percent),
                percentage_state(metric.percent),
                metric.detail,
            )
