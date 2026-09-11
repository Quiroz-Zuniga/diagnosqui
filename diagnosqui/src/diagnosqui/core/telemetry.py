"""Muestreo psutil compartido por las interfaces, sin dependencias gráficas.

La instancia debe conservarse y usarse desde un único hilo entre muestras.
"""

from __future__ import annotations
import math
import os
import time
from dataclasses import dataclass
from typing import Optional
import psutil


@dataclass(frozen=True)
class ProcessSnapshot:
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    username: str = "N/D"
    status: str = "N/D"


@dataclass(frozen=True)
class MetricSnapshot:
    """Porcentaje medido opcional; ``value`` y ``unit`` permiten tasas reales."""

    percent: Optional[float]
    detail: str
    value: Optional[float] = None
    unit: str = "%"

    @property
    def graph_value(self) -> Optional[float]:
        return self.value if self.value is not None else self.percent


@dataclass(frozen=True)
class PerformanceSnapshot:
    cpu: MetricSnapshot
    memory: MetricSnapshot
    disk: MetricSnapshot
    network: MetricSnapshot


def _finite_number(value: object, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return number if math.isfinite(number) else default


def _clamp_percent(value: object) -> float:
    return min(100.0, max(0.0, _finite_number(value)))


def threshold_level(percent: Optional[float]) -> str:
    if percent is None:
        return "unknown"
    if percent >= 90.0:
        return "critical"
    if percent >= 70.0:
        return "warning"
    return "normal"


class SystemSampler:
    """Lee contadores por dispositivo; cambios de identidad reinician su base."""

    def __init__(self) -> None:
        self._last_sample_at = time.monotonic()
        self._last_disks = self._read_disk_counters()
        self._last_network = self._read_network_counters()
        # Se crea y utiliza en el mismo worker: psutil mantiene esta base por hilo.
        self._cpu_metric()

    @staticmethod
    def _read_disk_counters() -> dict:
        try:
            counters = psutil.disk_io_counters(perdisk=True) or {}
        except (OSError, RuntimeError, psutil.Error):
            return {}
        return {
            name: (
                _finite_number(item.read_bytes),
                _finite_number(item.write_bytes),
                None
                if getattr(item, "busy_time", None) is None
                else _finite_number(item.busy_time),
            )
            for name, item in counters.items()
        }

    @staticmethod
    def _is_loopback(name: str) -> bool:
        return name.casefold() in {"lo", "lo0"} or "loopback" in name.casefold()

    @classmethod
    def _read_network_counters(cls) -> dict:
        try:
            counters = psutil.net_io_counters(pernic=True) or {}
        except (OSError, RuntimeError, psutil.Error):
            return {}
        try:
            stats = psutil.net_if_stats() or {}
        except (OSError, RuntimeError, psutil.Error):
            stats = {}
        result = {}
        for name, item in counters.items():
            status = stats.get(name)
            if cls._is_loopback(name) or (status is not None and not status.isup):
                continue
            result[name] = (
                _finite_number(item.bytes_sent),
                _finite_number(item.bytes_recv),
                max(0.0, _finite_number(getattr(status, "speed", 0))),
            )
        return result

    @staticmethod
    def _disk_usage_detail() -> str:
        root = (
            os.environ.get("SystemDrive", "C:") + os.sep if os.name == "nt" else os.sep
        )
        try:
            return f"{psutil.disk_usage(root).percent:.1f}% ocupado en {root}"
        except (OSError, RuntimeError, psutil.Error):
            return "Ocupación no disponible"

    @staticmethod
    def _cpu_metric() -> MetricSnapshot:
        try:
            return MetricSnapshot(
                _clamp_percent(psutil.cpu_percent(interval=None)),
                f"{psutil.cpu_count(logical=True) or '?'} procesadores lógicos",
            )
        except (OSError, RuntimeError, psutil.Error):
            return MetricSnapshot(None, "CPU no disponible")

    @staticmethod
    def _memory_metric() -> MetricSnapshot:
        try:
            memory = psutil.virtual_memory()
            return MetricSnapshot(
                _clamp_percent(memory.percent),
                f"{memory.used / 1024**3:.1f} / {memory.total / 1024**3:.1f} GiB en uso",
            )
        except (OSError, RuntimeError, psutil.Error):
            return MetricSnapshot(None, "Memoria no disponible")

    def read_processes(self) -> list[ProcessSnapshot]:
        """Mantiene la caché de process_iter y normaliza CPU al total de núcleos."""
        rows = []
        cpu_count = psutil.cpu_count(logical=True) or 1
        try:
            for process in psutil.process_iter(
                attrs=(
                    "pid",
                    "name",
                    "cpu_percent",
                    "memory_percent",
                    "username",
                    "status",
                ),
                ad_value=None,
            ):
                try:
                    info = process.info
                    if any(
                        info.get(key) is None
                        for key in ("pid", "name", "cpu_percent", "memory_percent")
                    ):
                        continue
                    rows.append(
                        ProcessSnapshot(
                            int(info["pid"]),
                            str(info["name"]),
                            _clamp_percent(
                                _finite_number(info["cpu_percent"]) / cpu_count
                            ),
                            _clamp_percent(info["memory_percent"]),
                            str(info.get("username") or "N/D"),
                            str(info.get("status") or "N/D"),
                        )
                    )
                except (psutil.Error, OSError, TypeError, ValueError):
                    continue
        except (psutil.Error, OSError, RuntimeError):
            pass
        return rows

    def _disk_metric(self, current: dict, elapsed: float) -> MetricSnapshot:
        samples = []
        for name, (read, written, busy) in current.items():
            previous = self._last_disks.get(name)
            if previous is None or elapsed < 0.2:
                continue
            # Una reducción de contadores indica reinicio/reconexión.
            if read < previous[0] or written < previous[1]:
                continue
            rate = ((read - previous[0]) + (written - previous[1])) / elapsed / 1024**2
            percent = None
            if busy is not None and previous[2] is not None and busy >= previous[2]:
                percent = _clamp_percent((busy - previous[2]) / elapsed / 10.0)
            samples.append((name, percent, rate))
        occupied = self._disk_usage_detail()
        if not samples:
            return MetricSnapshot(
                None, f"Esperando actividad de disco · {occupied}", unit="MiB/s"
            )
        measured = [sample for sample in samples if sample[1] is not None]
        # El máximo evita sumar discos, particiones y volúmenes lógicos duplicados.
        if measured:
            name, percent, rate = max(
                measured, key=lambda sample: (sample[1], sample[2])
            )
            return MetricSnapshot(
                percent, f"{name} · {rate:.2f} MiB/s E/S · {occupied}"
            )
        name, _, rate = max(samples, key=lambda sample: sample[2])
        return MetricSnapshot(
            None, f"{name} · lectura + escritura · {occupied}", rate, "MiB/s"
        )

    def _network_metric(self, current: dict, elapsed: float) -> MetricSnapshot:
        samples = []
        for name, (sent, received, speed) in current.items():
            previous = self._last_network.get(name)
            if (
                previous is None
                or elapsed < 0.2
                or sent < previous[0]
                or received < previous[1]
            ):
                continue
            tx = (sent - previous[0]) * 8.0 / elapsed / 1_000_000
            rx = (received - previous[1]) * 8.0 / elapsed / 1_000_000
            # Enlaces full duplex tienen capacidad independiente en cada sentido.
            percent = _clamp_percent(max(tx, rx) / speed * 100.0) if speed > 0 else None
            samples.append((name, percent, tx, rx, speed))
        if not samples:
            return MetricSnapshot(None, "Esperando una interfaz activa", unit="Mbit/s")
        # Una interfaz, no la suma de puentes y adaptadores que llevan el mismo tráfico.
        name, percent, tx, rx, speed = max(
            samples, key=lambda sample: sample[2] + sample[3]
        )
        capacity = (
            f"{percent:.1f}% de {speed:g} Mbit/s"
            if percent is not None
            else "capacidad no reportada"
        )
        return MetricSnapshot(
            None if percent is None else percent,
            f"{name} · ↑ {tx:.2f} ↓ {rx:.2f} · {capacity}",
            tx + rx,
            "Mbit/s",
        )

    def sample_performance(self) -> PerformanceSnapshot:
        now = time.monotonic()
        elapsed = max(now - self._last_sample_at, 0.001)
        disks = self._read_disk_counters()
        network = self._read_network_counters()
        snapshot = PerformanceSnapshot(
            self._cpu_metric(),
            self._memory_metric(),
            self._disk_metric(disks, elapsed),
            self._network_metric(network, elapsed),
        )
        self._last_sample_at = now
        self._last_disks = disks
        self._last_network = network
        return snapshot
