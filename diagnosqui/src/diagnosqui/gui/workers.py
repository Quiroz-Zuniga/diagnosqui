"""Pools acotados, señales encoladas y cancelación cooperativa al cerrar."""

from __future__ import annotations
from threading import Event
from typing import Any, Callable
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


class TaskSignals(QObject):
    completed = Signal(str, object, str)


class Task(QRunnable):
    def __init__(
        self, key: str, operation: Callable[[], Any], cancelled: Event
    ) -> None:
        super().__init__()
        self.key, self.operation, self.cancelled = key, operation, cancelled
        self.signals = TaskSignals()

    def run(self) -> None:
        value, error = None, ""
        try:
            if not self.cancelled.is_set():
                value = self.operation()
        except Exception as exception:
            error = f"{type(exception).__name__}: {exception}"
        finally:
            self.signals.completed.emit(self.key, value, error)


class WorkerManager(QObject):
    completed = Signal(str, object, str)

    def __init__(self, parent: QObject) -> None:
        super().__init__(parent)
        self.cancelled = Event()
        self.pending: dict[str, Task] = {}
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(2)
        self.pool.setExpiryTimeout(-1)
        self.telemetry_pool = QThreadPool(self)
        self.telemetry_pool.setMaxThreadCount(1)
        self.telemetry_pool.setExpiryTimeout(-1)

    def submit(
        self, key: str, operation: Callable[[], Any], telemetry: bool = False
    ) -> bool:
        if self.cancelled.is_set() or key in self.pending:
            return False
        task = Task(key, operation, self.cancelled)
        task.signals.completed.connect(self._completed)
        self.pending[key] = task
        (self.telemetry_pool if telemetry else self.pool).start(task)
        return True

    @Slot(str, object, str)
    def _completed(self, key: str, value: object, error: str) -> None:
        self.pending.pop(key, None)
        if not self.cancelled.is_set():
            self.completed.emit(key, value, error)

    def stop(self) -> None:
        # No destruir objetos ni terminar a la fuerza funciones del backend.
        # Las tareas ya en cola se retiran cooperativamente al comenzar.
        self.cancelled.set()

    def finished(self) -> bool:
        return (
            not self.pending
            and self.pool.activeThreadCount() == 0
            and self.telemetry_pool.activeThreadCount() == 0
        )
