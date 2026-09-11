"""Monitor Textual, adaptado del prototipo de ``diagnosqui/ui/monitor_tui.py``.

SystemSampler es independiente de la pantalla. Un único hilo persistente lee
psutil, conserva sus bases temporales y publica muestras en el hilo de Textual.
"""

from __future__ import annotations

import sys
import threading
from collections import deque
from datetime import datetime
from typing import Optional

import psutil as psutil  # API pública conservada para consumidores del monitor.
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import DataTable, Digits, Footer, Header, Sparkline, Static, TabbedContent, TabPane

from diagnosqui.ui.theme import (
    BACKGROUND_COLOR, CRITICAL_COLOR, CRITICAL_THRESHOLD, MUTED_COLOR,
    NORMAL_COLOR, PRIMARY_COLOR, TEXT_COLOR, WARNING_COLOR, WARNING_THRESHOLD,
    style_for_percentage,
)

NORMAL_LIMIT = WARNING_THRESHOLD
CRITICAL_LIMIT = CRITICAL_THRESHOLD
HISTORY_SIZE = 60
REFRESH_SECONDS = 1.0


# Reexportaciones compatibles con consumidores del monitor original.
from diagnosqui.core.telemetry import (
    MetricSnapshot as MetricSnapshot,
    PerformanceSnapshot, ProcessSnapshot, SystemSampler, threshold_level,
)


class MetricCard(Vertical):
    def __init__(self, metric_name: str, title: str) -> None:
        self.metric_name, self.metric_title = metric_name, title
        super().__init__(id=f"{metric_name}-card", classes="metric-card unknown")

    def compose(self) -> ComposeResult:
        yield Static(self.metric_title, classes="metric-title")
        yield Digits("--", id=f"{self.metric_name}-value", classes="metric-value unknown")
        yield Static("%", id=f"{self.metric_name}-unit", classes="metric-unit")
        yield Sparkline([], id=f"{self.metric_name}-graph", classes="metric-graph unknown", summary_function=max)
        yield Static("Esperando la primera muestra…", id=f"{self.metric_name}-detail", classes="metric-detail", markup=False)


class SampleReady(Message):
    def __init__(self, rows, snapshot, errors) -> None:
        super().__init__()
        self.rows, self.snapshot, self.errors = rows, snapshot, errors


class DiagnosQuiMonitor(App):
    TITLE = "DiagnosQui · Monitor del sistema"
    SUB_TITLE = "Procesos y rendimiento en vivo"
    BINDINGS = [
        Binding("q", "close_monitor", "Volver", priority=True),
        Binding("escape", "close_monitor", "Volver", show=False, priority=True),
        Binding("c", "sort_cpu", "Ordenar CPU"),
        Binding("m", "sort_memory", "Ordenar memoria"),
        Binding("r", "refresh_now", "Actualizar"),
    ]
    CSS = """
    Screen { background: __BACKGROUND__; color: __TEXT__; }
    Header, Footer { background: __BACKGROUND__; color: __PRIMARY__; }
    TabbedContent, TabPane { height: 1fr; }
    TabPane { padding: 0 1; }
    Tabs { background: __BACKGROUND__; }
    Tab.-active { color: __PRIMARY__; text-style: bold; }
    #process-toolbar, #performance-toolbar { height: 2; color: __MUTED__; }
    #process-table { height: 1fr; background: __BACKGROUND__; color: __TEXT__; }
    DataTable > .datatable--header { background: __BACKGROUND__; color: __PRIMARY__; text-style: bold; }
    DataTable > .datatable--cursor { background: __PRIMARY__; color: __BACKGROUND__; }
    #performance-scroll { height: 1fr; }
    #metrics-grid { grid-size: 2; grid-columns: 1fr 1fr; grid-rows: 13; grid-gutter: 1; height: 27; }
    #metrics-grid.narrow { grid-size: 1; height: 55; }
    .metric-card { padding: 0 1; border: round __PRIMARY__; background: __BACKGROUND__; height: 13; }
    .metric-title { height: 1; color: __PRIMARY__; text-style: bold; }
    .metric-value { height: 3; width: 100%; text-align: center; }
    .metric-unit { height: 1; color: __MUTED__; text-align: center; }
    .metric-graph { height: 2; }
    .metric-detail { height: 3; color: __MUTED__; text-align: center; }
    .metric-card.normal { border: round __NORMAL__; }
    .metric-card.warning { border: round __WARNING__; }
    .metric-card.critical { border: round __CRITICAL__; }
    .metric-card.unknown { border: round __PRIMARY__; }
    .metric-value.normal { color: __NORMAL__; }
    .metric-value.warning { color: __WARNING__; }
    .metric-value.critical { color: __CRITICAL__; }
    .metric-value.unknown { color: __PRIMARY__; }
    Sparkline.normal > .sparkline--min-color, Sparkline.normal > .sparkline--max-color { color: __NORMAL__; }
    Sparkline.warning > .sparkline--min-color, Sparkline.warning > .sparkline--max-color { color: __WARNING__; }
    Sparkline.critical > .sparkline--min-color, Sparkline.critical > .sparkline--max-color { color: __CRITICAL__; }
    Sparkline.unknown > .sparkline--min-color, Sparkline.unknown > .sparkline--max-color { color: __PRIMARY__; }
    """.replace("__BACKGROUND__", BACKGROUND_COLOR).replace("__TEXT__", TEXT_COLOR).replace(
        "__PRIMARY__", PRIMARY_COLOR).replace("__MUTED__", MUTED_COLOR).replace(
        "__NORMAL__", NORMAL_COLOR).replace("__WARNING__", WARNING_COLOR).replace("__CRITICAL__", CRITICAL_COLOR)

    def __init__(self, sampler: Optional[SystemSampler] = None) -> None:
        super().__init__()
        self._sampler = sampler
        self._process_rows = []
        self._sort_field = "cpu"
        self._sort_descending = True
        self._histories = {name: deque(maxlen=HISTORY_SIZE) for name in ("cpu", "memory", "disk", "network")}
        self._history_units = {}
        self._stop_sampling = threading.Event()
        self._refresh_requested = threading.Event()
        self._sampling_thread: Optional[threading.Thread] = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(initial="processes-pane"):
            with TabPane("Procesos", id="processes-pane"):
                yield Static("Cargando procesos…", id="process-toolbar", markup=False)
                yield DataTable(id="process-table", cursor_type="row", zebra_stripes=True)
            with TabPane("Rendimiento", id="performance-pane"):
                yield Static("Actualización cada 1 s · advertencia ≥70% · crítico ≥90%", id="performance-toolbar", markup=False)
                with VerticalScroll(id="performance-scroll"):
                    with Grid(id="metrics-grid"):
                        yield MetricCard("cpu", "CPU")
                        yield MetricCard("memory", "MEMORIA")
                        yield MetricCard("disk", "DISCO · DISPOSITIVO MÁS ACTIVO")
                        yield MetricCard("network", "RED · INTERFAZ MÁS ACTIVA")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#process-table", DataTable)
        table.add_column("PID", key="pid", width=7)
        table.add_column("Proceso", key="name", width=30)
        table.add_column("CPU %", key="cpu", width=9)
        table.add_column("Memoria %", key="memory", width=11)
        table.focus()
        self.query_one("#metrics-grid").set_class(self.size.width < 76, "narrow")
        self._sampling_thread = threading.Thread(
            target=self._sampling_loop, name="diagnosqui-sampler", daemon=True
        )
        self._sampling_thread.start()
        self._refresh_all()
        self.set_interval(REFRESH_SECONDS, self._refresh_all)

    def on_resize(self) -> None:
        for grid in self.query("#metrics-grid"):
            grid.set_class(self.size.width < 76, "narrow")

    def _sampling_loop(self) -> None:
        # Un hilo propio mantiene la base de psutil y permite cerrarlo sin esperar
        # al executor global de asyncio. post_message es seguro entre hilos.
        while not self._stop_sampling.is_set():
            if not self._refresh_requested.wait(timeout=0.1):
                continue
            self._refresh_requested.clear()
            if self._stop_sampling.is_set():
                break
            errors = {}
            rows = snapshot = None
            try:
                if self._sampler is None:
                    self._sampler = SystemSampler()
                rows = self._sampler.read_processes()
            except Exception as error:
                errors["process"] = str(error)
            try:
                if self._sampler is not None:
                    snapshot = self._sampler.sample_performance()
            except Exception as error:
                errors["performance"] = str(error)
            if not self._stop_sampling.is_set():
                self.post_message(SampleReady(rows, snapshot, errors))

    def on_sample_ready(self, message: SampleReady) -> None:
        if message.rows is not None:
            self._process_rows = message.rows
            self._render_processes()
        if message.snapshot is not None:
            self._render_performance(message.snapshot)
        for area, error in message.errors.items():
            self.query_one(f"#{area}-toolbar", Static).update(f"No se pudo actualizar: {error}")

    def _refresh_all(self) -> None:
        self._refresh_requested.set()

    def on_unmount(self) -> None:
        self._stop_sampling.set()
        self._refresh_requested.set()
        if self._sampling_thread is not None:
            self._sampling_thread.join(timeout=0.25)

    def action_close_monitor(self) -> None:
        self.on_unmount()
        self.exit()

    def action_refresh_now(self) -> None:
        self._refresh_all()

    def action_sort_cpu(self) -> None:
        self._change_sort("cpu")

    def action_sort_memory(self) -> None:
        self._change_sort("memory")

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        if event.column_key.value in {"cpu", "memory"}:
            self._change_sort(event.column_key.value)

    def _change_sort(self, field: str) -> None:
        self._sort_descending = not self._sort_descending if self._sort_field == field else True
        self._sort_field = field
        self._render_processes()

    def _sorted_process_rows(self) -> list[ProcessSnapshot]:
        if self._sort_field == "memory":
            key = lambda row: (row.memory_percent, row.cpu_percent, row.pid)
        else:
            key = lambda row: (row.cpu_percent, row.memory_percent, row.pid)
        return sorted(self._process_rows, key=key, reverse=self._sort_descending)

    def _render_processes(self) -> None:
        table = self.query_one("#process-table", DataTable)
        cursor_row, scroll_x, scroll_y = table.cursor_row, table.scroll_x, table.scroll_y
        selected = table.coordinate_to_cell_key(table.cursor_coordinate).row_key if table.row_count else None
        rows = self._sorted_process_rows()
        wanted = {f"pid-{row.pid}" for row in rows}
        for key in list(table.rows):
            if key.value not in wanted:
                table.remove_row(key)
        for row in rows:
            key = f"pid-{row.pid}"
            values = (str(row.pid), Text(row.name[:52]),
                      Text(f"{row.cpu_percent:.1f}", style=style_for_percentage(row.cpu_percent)),
                      Text(f"{row.memory_percent:.1f}", style=style_for_percentage(row.memory_percent)))
            if key in table.rows:
                for column, value in zip(("pid", "name", "cpu", "memory"), values):
                    table.update_cell(key, column, value)
            else:
                table.add_row(*values, key=key)
        ranks = {str(row.pid): rank for rank, row in enumerate(rows)}
        table.sort("pid", key=lambda pid: ranks[pid])
        if rows:
            index = table.get_row_index(selected) if selected in table.rows else min(cursor_row, len(rows) - 1)
            table.move_cursor(row=index, scroll=False)
        table.scroll_to(x=scroll_x, y=scroll_y, animate=False, immediate=True)
        field = "CPU" if self._sort_field == "cpu" else "memoria"
        direction = "↓" if self._sort_descending else "↑"
        self.query_one("#process-toolbar", Static).update(
            f"{len(rows)} procesos · orden {field} {direction} · c/m o clic en encabezado\nCPU normalizada al total del sistema"
            if rows else "No hay procesos accesibles · pulsa r para reintentar"
        )

    def _render_performance(self, snapshot: PerformanceSnapshot) -> None:
        for name in ("cpu", "memory", "disk", "network"):
            metric = getattr(snapshot, name)
            level = threshold_level(metric.percent)
            history = self._histories[name]
            if self._history_units.get(name) != metric.unit:
                history.clear()
                self._history_units[name] = metric.unit
            if metric.graph_value is not None:
                history.append(metric.graph_value)
            self.query_one(f"#{name}-card").set_classes(f"metric-card {level}")
            value = self.query_one(f"#{name}-value", Digits)
            value.set_classes(f"metric-value {level}")
            value.update("--" if metric.graph_value is None else f"{metric.graph_value:.1f}")
            self.query_one(f"#{name}-unit", Static).update(metric.unit)
            graph = self.query_one(f"#{name}-graph", Sparkline)
            graph.set_classes(f"metric-graph {level}")
            graph.data = list(history)
            self.query_one(f"#{name}-detail", Static).update(metric.detail)
        self.query_one("#performance-toolbar", Static).update(
            f"{datetime.now():%H:%M:%S} · cada 1 s · últimos 60 puntos · escala automática\nAdvertencia ≥70% · crítico ≥90% · cian: sin porcentaje medible"
        )


def run_monitor() -> bool:
    """Abre el monitor; q/Esc restaura la terminal y devuelve el control al menú."""
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("DiagnosQui: el monitor necesita una terminal interactiva.", file=sys.stderr)
        return False
    try:
        DiagnosQuiMonitor().run()
    except KeyboardInterrupt:
        return True
    except Exception as error:
        print(f"DiagnosQui: no se pudo abrir el monitor: {error}", file=sys.stderr)
        return False
    return True


launch_monitor = run_monitor

if __name__ == "__main__":
    raise SystemExit(0 if run_monitor() else 1)
