"""Monitor interactivo de procesos y rendimiento para DiagnosQui.

La interfaz vive en Textual, mientras que la recoleccion de datos se mantiene en
``SystemSampler``. Esta separacion permite probar los calculos sin levantar una
terminal y evita que un proceso que desaparece durante el muestreo cierre la app.
"""

from __future__ import annotations

import math
import os
import sys
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Deque, Dict, List, Optional, Tuple

try:
    from diagnosqui.ui.theme import (
        BACKGROUND_COLOR,
        CRITICAL_COLOR,
        CRITICAL_THRESHOLD,
        MUTED_COLOR,
        NORMAL_COLOR,
        PRIMARY_COLOR,
        TEXT_COLOR,
        WARNING_COLOR,
        WARNING_THRESHOLD,
    )
except ImportError:  # Rich aun no instalado: conservar import seguro del modulo
    PRIMARY_COLOR = "#22d3ee"
    NORMAL_COLOR = "#22c55e"
    WARNING_COLOR = "#facc15"
    CRITICAL_COLOR = "#ef4444"
    MUTED_COLOR = "#64748b"
    TEXT_COLOR = "#f8fafc"
    BACKGROUND_COLOR = "#0f172a"
    WARNING_THRESHOLD = 70.0
    CRITICAL_THRESHOLD = 90.0

try:
    import psutil
except ImportError as error:  # pragma: no cover - depende del entorno del usuario
    psutil = None  # type: ignore[assignment]
    _PSUTIL_IMPORT_ERROR: Optional[BaseException] = error
else:
    _PSUTIL_IMPORT_ERROR = None


# Alias historicos para consumidores del monitor; la fuente canonica es theme.py.
NORMAL_LIMIT = WARNING_THRESHOLD
CRITICAL_LIMIT = CRITICAL_THRESHOLD
HISTORY_SIZE = 60
REFRESH_SECONDS = 1.0


@dataclass(frozen=True)
class ProcessSnapshot:
    """Una fila estable de la tabla de procesos."""

    pid: int
    name: str
    cpu_percent: float
    memory_percent: float


@dataclass(frozen=True)
class MetricSnapshot:
    """Valor porcentual y texto auxiliar de una metrica."""

    percent: float
    detail: str


@dataclass(frozen=True)
class PerformanceSnapshot:
    """Muestra atomica de las cuatro metricas del monitor."""

    cpu: MetricSnapshot
    memory: MetricSnapshot
    disk: MetricSnapshot
    network: MetricSnapshot


def _finite_number(value: object, default: float = 0.0) -> float:
    """Convierte valores de psutil, incluidos ``None`` y NaN, con seguridad."""

    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError, OverflowError):
        return default
    return number if math.isfinite(number) else default


def _clamp_percent(value: object) -> float:
    return min(100.0, max(0.0, _finite_number(value)))


def threshold_level(percent: float) -> str:
    """Devuelve la clase visual correspondiente a los umbrales 70/90."""

    value = _clamp_percent(percent)
    if value >= CRITICAL_LIMIT:
        return "critical"
    if value >= NORMAL_LIMIT:
        return "warning"
    return "normal"


class SystemSampler:
    """Recolecta datos de psutil y calcula tasas entre muestras consecutivas."""

    def __init__(self) -> None:
        if psutil is None:
            raise RuntimeError(
                "psutil no esta instalado; ejecuta `python -m pip install psutil`."
            ) from _PSUTIL_IMPORT_ERROR

        self._last_sample_at = time.monotonic()
        self._last_disk_busy_ms = self._read_disk_busy_ms()
        net_bytes, _ = self._read_network_counters()
        self._last_network_bytes = net_bytes

        # La primera llamada establece la base usada por cpu_percent(interval=None).
        try:
            psutil.cpu_percent(interval=None)
        except (OSError, RuntimeError):
            pass

    @staticmethod
    def _is_loopback(interface_name: str) -> bool:
        name = interface_name.casefold().strip()
        return name in {"lo", "lo0"} or "loopback" in name

    @staticmethod
    def _read_disk_busy_ms() -> Optional[float]:
        """Lee tiempo activo acumulado; no todos los SO lo proporcionan."""

        assert psutil is not None
        try:
            counters = psutil.disk_io_counters()
        except (OSError, RuntimeError):
            return None
        if counters is None:
            return None
        busy_time = getattr(counters, "busy_time", None)
        if busy_time is None:
            return None
        return max(0.0, _finite_number(busy_time))

    @classmethod
    def _read_network_counters(cls) -> Tuple[float, float]:
        """Retorna bytes transferidos y capacidad activa estimada en Mbit/s."""

        assert psutil is not None
        try:
            per_interface = psutil.net_io_counters(pernic=True) or {}
        except (OSError, RuntimeError):
            per_interface = {}
        try:
            interface_stats = psutil.net_if_stats() or {}
        except (OSError, RuntimeError):
            interface_stats = {}

        total_bytes = 0.0
        capacity_mbit = 0.0
        for name, counters in per_interface.items():
            if cls._is_loopback(name):
                continue
            stats = interface_stats.get(name)
            if stats is not None and not getattr(stats, "isup", True):
                continue
            total_bytes += max(0.0, _finite_number(counters.bytes_sent))
            total_bytes += max(0.0, _finite_number(counters.bytes_recv))
            if stats is not None:
                capacity_mbit += max(0.0, _finite_number(getattr(stats, "speed", 0)))

        if per_interface:
            return total_bytes, capacity_mbit

        # Algunos sistemas solo exponen el contador agregado.
        try:
            counters = psutil.net_io_counters()
        except (OSError, RuntimeError):
            counters = None
        if counters is None:
            return 0.0, 0.0
        total_bytes = _finite_number(counters.bytes_sent) + _finite_number(
            counters.bytes_recv
        )
        return max(0.0, total_bytes), 0.0

    @staticmethod
    def _disk_usage_percent() -> float:
        assert psutil is not None
        if os.name == "nt":
            root_path = os.environ.get("SystemDrive", "C:") + os.sep
        else:
            root_path = os.sep
        try:
            return _clamp_percent(psutil.disk_usage(root_path).percent)
        except (OSError, RuntimeError):
            return 0.0

    @staticmethod
    def _memory_metric() -> MetricSnapshot:
        assert psutil is not None
        try:
            memory = psutil.virtual_memory()
        except (OSError, RuntimeError):
            return MetricSnapshot(0.0, "Memoria no disponible")
        gib = 1024.0**3
        used = _finite_number(getattr(memory, "used", 0.0)) / gib
        total = _finite_number(getattr(memory, "total", 0.0)) / gib
        return MetricSnapshot(
            _clamp_percent(getattr(memory, "percent", 0.0)),
            f"{used:.1f} / {total:.1f} GiB en uso",
        )

    @staticmethod
    def _cpu_metric() -> MetricSnapshot:
        assert psutil is not None
        try:
            percent = _clamp_percent(psutil.cpu_percent(interval=None))
        except (OSError, RuntimeError):
            percent = 0.0
        try:
            logical_cpus = psutil.cpu_count(logical=True)
        except (OSError, RuntimeError):
            logical_cpus = None
        detail = (
            f"{logical_cpus} procesadores logicos"
            if logical_cpus
            else "Procesadores logicos no disponibles"
        )
        return MetricSnapshot(percent, detail)

    def read_processes(self) -> List[ProcessSnapshot]:
        """Obtiene procesos accesibles; ignora carreras y permisos por proceso."""

        assert psutil is not None
        rows: List[ProcessSnapshot] = []
        attributes = ("pid", "name", "cpu_percent", "memory_percent")
        try:
            processes = psutil.process_iter(attrs=attributes)
            for process in processes:
                try:
                    info = process.info
                    pid = int(info.get("pid", process.pid))
                    name = str(info.get("name") or "<sin nombre>")
                    cpu = max(0.0, _finite_number(info.get("cpu_percent")))
                    memory = _clamp_percent(info.get("memory_percent"))
                except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                    psutil.ZombieProcess,
                    OSError,
                    TypeError,
                    ValueError,
                ):
                    continue
                rows.append(ProcessSnapshot(pid, name, cpu, memory))
        except (OSError, RuntimeError):
            return []
        return rows

    def sample_performance(self) -> PerformanceSnapshot:
        """Calcula una muestra usando deltas de disco y red de un segundo."""

        now = time.monotonic()
        elapsed = max(now - self._last_sample_at, 0.001)

        cpu = self._cpu_metric()
        memory = self._memory_metric()

        current_busy_ms = self._read_disk_busy_ms()
        stable_interval = elapsed >= 0.2
        if (
            stable_interval
            and current_busy_ms is not None
            and self._last_disk_busy_ms is not None
        ):
            busy_delta = max(0.0, current_busy_ms - self._last_disk_busy_ms)
            disk_percent = _clamp_percent(busy_delta / (elapsed * 10.0))
            disk_detail = f"Actividad de E/S · {self._disk_usage_percent():.1f}% ocupado"
        else:
            disk_percent = self._disk_usage_percent()
            disk_detail = "Ocupacion del sistema de archivos"

        current_network_bytes, capacity_mbit = self._read_network_counters()
        transferred = max(0.0, current_network_bytes - self._last_network_bytes)
        if not stable_interval:
            transferred = 0.0
        rate_mbit = transferred * 8.0 / elapsed / 1_000_000.0
        # Si el SO no reporta velocidad de enlace, 100 Mbit/s evita una grafica
        # sin escala y sigue ofreciendo un porcentaje util y acotado.
        effective_capacity = capacity_mbit if capacity_mbit > 0.0 else 100.0
        network_percent = _clamp_percent(rate_mbit / effective_capacity * 100.0)
        if capacity_mbit > 0.0:
            network_detail = f"{rate_mbit:.2f} Mbit/s · enlace {capacity_mbit:.0f} Mbit/s"
        else:
            network_detail = f"{rate_mbit:.2f} Mbit/s · capacidad no reportada"

        self._last_sample_at = now
        self._last_disk_busy_ms = current_busy_ms
        self._last_network_bytes = current_network_bytes

        return PerformanceSnapshot(
            cpu=cpu,
            memory=memory,
            disk=MetricSnapshot(disk_percent, disk_detail),
            network=MetricSnapshot(network_percent, network_detail),
        )


_TEXTUAL_IMPORT_ERROR: Optional[BaseException] = None
try:
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Grid, Vertical
    from textual.widgets import (
        DataTable,
        Digits,
        Footer,
        Header,
        Sparkline,
        Static,
        TabbedContent,
        TabPane,
    )
except ImportError as error:  # pragma: no cover - depende del entorno del usuario
    _TEXTUAL_IMPORT_ERROR = error


if _TEXTUAL_IMPORT_ERROR is None:

    class MetricCard(Vertical):
        """Tarjeta de valor actual y sus ultimos 60 puntos."""

        def __init__(self, metric_name: str, title: str) -> None:
            self.metric_name = metric_name
            self.metric_title = title
            super().__init__(
                id=f"{metric_name}-card", classes="metric-card normal"
            )

        def compose(self) -> ComposeResult:
            yield Static(self.metric_title, classes="metric-title")
            yield Digits(
                "0.0%", id=f"{self.metric_name}-value", classes="metric-value normal"
            )
            yield Sparkline(
                [0.0],
                id=f"{self.metric_name}-graph",
                classes="metric-graph normal",
                summary_function=max,
            )
            yield Static(
                "Esperando la primera muestra...",
                id=f"{self.metric_name}-detail",
                classes="metric-detail",
            )


    class DiagnosQuiMonitor(App):
        """Task Manager de DiagnosQui; ``q`` o Escape retorna al menu."""

        TITLE = "DiagnosQui · Monitor del sistema"
        SUB_TITLE = "Procesos y rendimiento en vivo"

        BINDINGS = [
            Binding("q", "close_monitor", "Volver", show=True),
            Binding("escape", "close_monitor", "Volver", show=False),
            Binding("c", "sort_cpu", "Ordenar CPU", show=True),
            Binding("m", "sort_memory", "Ordenar memoria", show=True),
            Binding("r", "refresh_now", "Actualizar", show=True),
        ]

        CSS = """
        Screen {
            background: __BACKGROUND__;
            color: __TEXT__;
        }

        Header, Footer {
            background: __BACKGROUND__;
            color: __PRIMARY__;
        }

        TabbedContent {
            height: 1fr;
        }

        TabPane {
            height: 1fr;
            padding: 0 1;
        }

        Tabs {
            background: __BACKGROUND__;
        }

        Tab.-active {
            color: __BACKGROUND__;
            background: __PRIMARY__;
            text-style: bold;
        }

        #process-toolbar, #performance-toolbar {
            height: 1;
            color: __MUTED__;
        }

        #process-table {
            height: 1fr;
            background: __BACKGROUND__;
            color: __TEXT__;
        }

        DataTable > .datatable--header {
            background: __BACKGROUND__;
            color: __PRIMARY__;
            text-style: bold;
        }

        DataTable > .datatable--cursor {
            background: __PRIMARY__;
            color: __BACKGROUND__;
        }

        #metrics-grid {
            layout: grid;
            grid-size: 2 2;
            grid-columns: 1fr 1fr;
            grid-rows: 1fr 1fr;
            grid-gutter: 1;
            height: 1fr;
        }

        .metric-card {
            padding: 0 1;
            border: round __PRIMARY__;
            background: __BACKGROUND__;
            min-height: 8;
        }

        .metric-title {
            height: 1;
            color: __PRIMARY__;
            text-style: bold;
        }

        .metric-value {
            height: 3;
            width: 100%;
            text-align: center;
        }

        .metric-graph {
            height: 1fr;
            min-height: 1;
        }

        .metric-detail {
            height: 1;
            color: __MUTED__;
            text-align: center;
        }

        .metric-card.normal {
            border: round __NORMAL__;
        }

        .metric-value.normal, .metric-graph.normal {
            color: __NORMAL__;
        }

        .metric-card.warning {
            border: round __WARNING__;
        }

        .metric-value.warning, .metric-graph.warning {
            color: __WARNING__;
        }

        .metric-card.critical {
            border: round __CRITICAL__;
        }

        .metric-value.critical, .metric-graph.critical {
            color: __CRITICAL__;
        }
        """.replace("__BACKGROUND__", BACKGROUND_COLOR).replace(
            "__PRIMARY__", PRIMARY_COLOR
        ).replace("__TEXT__", TEXT_COLOR).replace("__MUTED__", MUTED_COLOR).replace(
            "__NORMAL__", NORMAL_COLOR
        ).replace(
            "__WARNING__", WARNING_COLOR
        ).replace(
            "__CRITICAL__", CRITICAL_COLOR
        )

        def __init__(self, sampler: Optional[SystemSampler] = None) -> None:
            super().__init__()
            self._sampler = sampler or SystemSampler()
            self._process_rows: List[ProcessSnapshot] = []
            self._sort_field = "cpu"
            self._sort_descending = True
            self._histories: Dict[str, Deque[float]] = {
                name: deque([0.0], maxlen=HISTORY_SIZE)
                for name in ("cpu", "memory", "disk", "network")
            }

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with TabbedContent(initial="processes-pane"):
                with TabPane("Procesos", id="processes-pane"):
                    yield Static("Cargando procesos...", id="process-toolbar")
                    yield DataTable(
                        id="process-table",
                        cursor_type="row",
                        zebra_stripes=True,
                    )
                with TabPane("Rendimiento", id="performance-pane"):
                    yield Static(
                        "Actualizacion cada 1 s · amarillo >= 70% · rojo >= 90%",
                        id="performance-toolbar",
                    )
                    with Grid(id="metrics-grid"):
                        yield MetricCard("cpu", "CPU")
                        yield MetricCard("memory", "MEMORIA")
                        yield MetricCard("disk", "DISCO")
                        yield MetricCard("network", "RED")
            yield Footer()

        def on_mount(self) -> None:
            table = self.query_one("#process-table", DataTable)
            table.add_column("PID", key="pid", width=8)
            table.add_column("Proceso", key="name")
            table.add_column("CPU %", key="cpu", width=10)
            table.add_column("Memoria %", key="memory", width=12)
            table.focus()
            self._refresh_all()
            self.set_interval(REFRESH_SECONDS, self._refresh_all)

        def action_close_monitor(self) -> None:
            self.exit()

        def action_refresh_now(self) -> None:
            self._refresh_all()

        def action_sort_cpu(self) -> None:
            self._change_sort("cpu")

        def action_sort_memory(self) -> None:
            self._change_sort("memory")

        def on_data_table_header_selected(self, event: object) -> None:
            """Permite ordenar haciendo clic en CPU o Memoria."""

            column_key = getattr(event, "column_key", "")
            key = str(getattr(column_key, "value", column_key))
            if key in {"cpu", "memory"}:
                self._change_sort(key)

        def _change_sort(self, field: str) -> None:
            if self._sort_field == field:
                self._sort_descending = not self._sort_descending
            else:
                self._sort_field = field
                self._sort_descending = True
            self._render_processes()

        def _refresh_all(self) -> None:
            try:
                self._process_rows = self._sampler.read_processes()
                self._render_processes()
            except Exception as error:  # protege el loop de refresco de fallos del SO
                self.query_one("#process-toolbar", Static).update(
                    f"No se pudieron leer procesos: {error}"
                )

            try:
                snapshot = self._sampler.sample_performance()
                self._render_performance(snapshot)
            except Exception as error:  # protege el loop de refresco de fallos del SO
                self.query_one("#performance-toolbar", Static).update(
                    f"No se pudo actualizar el rendimiento: {error}"
                )

        def _sorted_process_rows(self) -> List[ProcessSnapshot]:
            if self._sort_field == "memory":
                key = lambda row: (row.memory_percent, row.cpu_percent, row.pid)
            else:
                key = lambda row: (row.cpu_percent, row.memory_percent, row.pid)
            return sorted(
                self._process_rows, key=key, reverse=self._sort_descending
            )

        @staticmethod
        def _short_process_name(name: str, width: int = 52) -> str:
            if len(name) <= width:
                return name
            return name[: width - 1] + "…"

        def _render_processes(self) -> None:
            table = self.query_one("#process-table", DataTable)
            table.clear()
            rows = self._sorted_process_rows()
            for row in rows:
                table.add_row(
                    str(row.pid),
                    self._short_process_name(row.name),
                    f"{row.cpu_percent:6.1f}",
                    f"{row.memory_percent:8.1f}",
                    key=f"pid-{row.pid}",
                )

            direction = "descendente" if self._sort_descending else "ascendente"
            field_name = "CPU" if self._sort_field == "cpu" else "memoria"
            message = (
                f"{len(rows)} procesos · orden: {field_name} {direction} · "
                "clic en CPU/Memoria o teclas c/m"
            )
            if not rows:
                message = "No hay procesos accesibles · pulsa r para reintentar"
            self.query_one("#process-toolbar", Static).update(message)

        def _render_performance(self, snapshot: PerformanceSnapshot) -> None:
            metrics = {
                "cpu": snapshot.cpu,
                "memory": snapshot.memory,
                "disk": snapshot.disk,
                "network": snapshot.network,
            }
            for name, metric in metrics.items():
                level = threshold_level(metric.percent)
                history = self._histories[name]
                history.append(metric.percent)

                card = self.query_one(f"#{name}-card", MetricCard)
                value = self.query_one(f"#{name}-value", Digits)
                graph = self.query_one(f"#{name}-graph", Sparkline)
                detail = self.query_one(f"#{name}-detail", Static)

                card.set_classes(f"metric-card {level}")
                value.set_classes(f"metric-value {level}")
                graph.set_classes(f"metric-graph {level}")
                value.update(f"{metric.percent:.1f}%")
                graph.data = list(history)
                detail.update(metric.detail)

            self.query_one("#performance-toolbar", Static).update(
                f"Actualizado {datetime.now():%H:%M:%S} · cada 1 s · "
                "amarillo >= 70% · rojo >= 90%"
            )


else:

    class DiagnosQuiMonitor:  # pragma: no cover - solo sin dependencia opcional
        """Marcador que conserva un error claro cuando falta Textual."""

        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs
            raise RuntimeError(
                "Textual no esta instalado; ejecuta "
                "`python -m pip install 'textual>=0.47'`."
            ) from _TEXTUAL_IMPORT_ERROR


def run_monitor() -> bool:
    """Abre el monitor y vuelve al llamador al pulsar ``q`` o Escape.

    El booleano permite al CLI decidir si debe mostrar un aviso adicional sin que
    una dependencia ausente derribe el menu principal.
    """

    if _PSUTIL_IMPORT_ERROR is not None:
        print(
            "DiagnosQui: falta psutil. Instala las dependencias del proyecto.",
            file=sys.stderr,
        )
        return False
    if _TEXTUAL_IMPORT_ERROR is not None:
        print(
            "DiagnosQui: falta Textual. Ejecuta "
            "`python -m pip install 'textual>=0.47'`.",
            file=sys.stderr,
        )
        return False

    try:
        DiagnosQuiMonitor().run()  # type: ignore[attr-defined]
    except KeyboardInterrupt:
        return True
    except Exception as error:
        print(f"DiagnosQui: no se pudo abrir el monitor: {error}", file=sys.stderr)
        return False
    return True


# Alias explicito para integraciones que prefieran el verbo "launch".
launch_monitor = run_monitor


if __name__ == "__main__":
    raise SystemExit(0 if run_monitor() else 1)
