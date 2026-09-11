"""Coordinación de tareas y widgets; solo los servicios acceden al hardware."""

from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING
from PySide6.QtCore import QObject, QTimer, Slot
from diagnosqui.gui.services.diagnostic_service import DiagnosticService
from diagnosqui.gui.services.telemetry_service import TelemetryService
from diagnosqui.gui.workers import WorkerManager

if TYPE_CHECKING:
    from diagnosqui.gui.main_window import MainWindow


class Controller(QObject):
    def __init__(
        self,
        window: MainWindow,
        service: DiagnosticService,
        telemetry: TelemetryService,
        auto_start: bool,
    ) -> None:
        super().__init__(window)
        self.window, self.service, self.telemetry = window, service, telemetry
        self.results: dict = {}
        self.workers = WorkerManager(self)
        self.workers.completed.connect(self._completed)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.setInterval(max(1, window.preferences.interval.value()) * 1000)
        self.start_timer = QTimer(self)
        self.start_timer.setSingleShot(True)
        self.start_timer.timeout.connect(self.refresh_all)
        if auto_start:
            self.timer.start()
            self.start_timer.start(0)
        window.refresh_button.clicked.connect(self.refresh_all)
        window.reports.requested.connect(self.refresh_all)
        window.problems.requested.connect(self.refresh_all)
        window.reports.export_requested.connect(self.export)
        window.monitor.io_requested.connect(self.measure_io)
        window.preferences.changed.connect(self.apply_preferences)
        for page in window.components.values():
            page.requested.connect(self.collect)

    def _busy(self, key: str, busy: bool) -> None:
        view = self.window
        if key == "full":
            view.refresh_button.setDisabled(busy)
            view.refresh_button.setText(
                "Diagnosticando…" if busy else "Actualizar datos"
            )
            view.reports.set_busy(busy)
            view.problems.run_button.setDisabled(busy)
            for page in view.components.values():
                page.set_busy(busy)
        elif key in view.components:
            view.components[key].set_busy(busy)
        elif key == "export":
            view.reports.set_busy(busy)
        elif key == "io":
            view.monitor.io_button.setDisabled(busy)

    @Slot()
    def refresh_all(self) -> None:
        if self.workers.pending.keys() - {"telemetry", "io"}:
            self.window.statusBar().showMessage(
                "Espera a que termine la operación actual.", 4000
            )
            return
        if self.workers.submit(
            "full", lambda: self.service.collect_all(self.workers.cancelled)
        ):
            self._busy("full", True)
            self.window.statusBar().showMessage(
                "Consultando los proveedores de diagnóstico…"
            )
            self.tick()

    @Slot(str)
    def collect(self, key: str) -> None:
        if "full" in self.workers.pending:
            return
        if self.workers.submit(key, lambda: self.service.collect(key)):
            self._busy(key, True)
            self.window.components[key].show_error("")

    @Slot()
    def tick(self) -> None:
        include_processes = (
            self.window.current_page == "procesos" and not self.window.processes.paused
        )
        self.workers.submit(
            "telemetry",
            lambda: self.telemetry.sample(include_processes),
            telemetry=True,
        )

    @Slot()
    def measure_io(self) -> None:
        if self.workers.submit("io", self.service.collect_io):
            self._busy("io", True)

    @Slot(str, object)
    def export(self, directory: str, formats: object) -> None:
        if not directory.strip():
            self.window.reports.message.setText("Elige una carpeta de destino.")
            return
        snapshot = deepcopy(self.results)
        if not snapshot or "full" in self.workers.pending:
            return
        path = str(Path(directory).expanduser())
        if self.workers.submit(
            "export", lambda: self.service.export(snapshot, path, tuple(formats))
        ):
            self._busy("export", True)
            self.window.reports.message.setText("Exportando el diagnóstico mostrado…")

    @Slot(str, object, str)
    def _completed(self, key: str, value: object, error: str) -> None:
        try:
            if error:
                self._show_error(key, error)
            elif key == "telemetry":
                if isinstance(value, dict):
                    performance = value.get("performance")
                    if performance is not None:
                        self.window.dashboard.set_performance(performance)
                        self.window.monitor.set_performance(performance)
                    if "processes" in value:
                        self.window.processes.set_processes(value["processes"])
            elif key == "export":
                paths = list(value.values())
                self.window.reports.message.setText(
                    "Exportación completada:\n" + "\n".join(map(str, paths))
                )
                if paths:
                    self.window.reports.last_directory = str(Path(paths[0]).parent)
            elif key == "io":
                self.window.monitor.set_io(value)
            else:
                incoming = value if key == "full" else {key: value}
                self.results.update(incoming)
                for component, result in incoming.items():
                    if component in self.window.components:
                        self.window.components[component].set_result(result)
                self.window.dashboard.set_results(incoming)
                self.window.problems.set_results(self.results)
                self.window.reports.set_results(self.results)
                self.window.update_summary(self.results)
                sources = sorted(
                    {
                        str(result.get("detalle", {}).get("fuente", "N/D"))
                        for result in self.results.values()
                    }
                )
                self.window.statusBar().showMessage(
                    "Diagnóstico actualizado. Fuente: " + ", ".join(sources), 5000
                )
        except Exception as exception:
            self._show_error(key, f"No se pudo presentar el resultado: {exception}")
        finally:
            self._busy(key, False)

    def _show_error(self, key: str, message: str) -> None:
        self.window.statusBar().showMessage(message)
        if key in self.window.components:
            self.window.components[key].show_error(message)
        elif key in {"full", "export"}:
            self.window.reports.message.setText(message)
            self.window.problems.message.setText(message)
        elif key == "telemetry":
            self.window.monitor.updated.setText(f"No se pudo actualizar: {message}")
        elif key == "io":
            self.window.monitor.io_result.setText(message)

    @Slot()
    def apply_preferences(self) -> None:
        self.window.theme_manager.apply(
            self.window.preferences.appearance.currentData()
        )
        self.timer.setInterval(self.window.preferences.interval.value() * 1000)
        self.window.reports.directory.setText(self.window.preferences.directory.text())
        if not self.window.preferences.animations.isChecked():
            self.window.animation.stop()
            self.window.fade.setOpacity(1)

    def stop(self) -> None:
        self.timer.stop()
        self.start_timer.stop()
        self.workers.stop()
