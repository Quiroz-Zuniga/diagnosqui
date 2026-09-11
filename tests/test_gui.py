"""Pruebas headless de GUI, proveedores y ciclo de vida; hardware sustituido."""

from __future__ import annotations
import importlib
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QSettings, QTimer, Qt
from PySide6.QtTest import QTest
from diagnosqui.gui.app import create_application
from diagnosqui.gui.main_window import MainWindow
from diagnosqui.gui.services.contracts import normalize_result
from diagnosqui.gui.services.diagnostic_service import COMPONENTS, DiagnosticService
from diagnosqui.gui.theme import COLORS, LABELS, state_color
from diagnosqui.gui.widgets.status_badge import StatusBadge
from diagnosqui.gui.widgets.chart_widget import ChartWidget
from diagnosqui.core.telemetry import (
    MetricSnapshot,
    PerformanceSnapshot,
    ProcessSnapshot,
)


def fixture(component="CPU", **changes):
    data = dict(
        componente=component,
        evidencia="42%",
        valor_numerico=42,
        estado="NORMAL",
        detalle={"fuente": "fixture"},
        recomendacion=["Sin acciones de prueba."],
    )
    data.update(changes)
    return data


class TestContracts(unittest.TestCase):
    def test_missing_keys_invalid_numbers_and_statuses(self):
        for raw in (
            {},
            None,
            {"valor_numerico": "mal", "detalle": [], "recomendacion": 4},
            {"valor_numerico": float("nan")},
        ):
            result = normalize_result(raw, "CPU")
            self.assertEqual(set(result), set(fixture()))
            self.assertEqual(result["componente"], "CPU")
            self.assertIsNone(result["valor_numerico"])
            self.assertIsInstance(result["detalle"], dict)
            self.assertIsInstance(result["recomendacion"], list)
            self.assertEqual(result["estado"], "ADVERTENCIA")
        self.assertEqual(normalize_result({"estado": "CRÍTICO"})["estado"], "CRITICO")
        failed = normalize_result(
            fixture(valor_numerico=0, detalle={"error": "Sin permisos"})
        )
        self.assertIsNone(failed["valor_numerico"])
        self.assertEqual(failed["estado"], "ADVERTENCIA")

    def test_provider_failure_is_a_partial_result(self):
        service = DiagnosticService({"cpu": Mock(side_effect=OSError("sin permisos"))})
        result = service.collect("cpu")
        self.assertEqual(result["estado"], "ADVERTENCIA")
        self.assertIn("sin permisos", result["detalle"]["error"])
        self.assertEqual(result["detalle"]["fuente"], "real")

    def test_service_uses_real_collector_without_show_functions(self):
        with patch(
            "diagnosqui.core.cpu.recolectar_cpu", return_value=fixture()
        ) as collect:
            with patch(
                "diagnosqui.core.cpu.show_cpu",
                side_effect=AssertionError("No usar Rich"),
            ):
                result = DiagnosticService().collect("cpu")
        collect.assert_called_once_with()
        self.assertEqual(result["valor_numerico"], 42)

    def test_exports_preserve_source_and_escape_hardware_names(self):
        from diagnosqui.core.reporte import export_diagnostic_results

        with tempfile.TemporaryDirectory() as directory:
            result = fixture(evidencia="<script>dato</script>")
            paths = export_diagnostic_results([result], directory)
            self.assertEqual(set(paths), {"json", "csv", "html"})
            payload = json.loads(Path(paths["json"]).read_text())
            self.assertEqual(payload["fuente"], "fixture")
            self.assertEqual(payload["resultados"][0], result)
            html = Path(paths["html"]).read_text()
            self.assertIn("&lt;script&gt;", html)
            self.assertNotIn("<script>", html)
            self.assertIn("Fuente: fixture", html)
            self.assertIn(
                "Fuente de los resultados,fixture", Path(paths["csv"]).read_text()
            )
            second = export_diagnostic_results([result], directory)
            self.assertNotEqual(paths, second)

    def test_platform_modules_import_without_running_platform_commands(self):
        for module in ("windows_backend", "linux_backend"):
            with patch(
                "subprocess.run", side_effect=AssertionError("No ejecutar al importar")
            ):
                importlib.reload(
                    importlib.import_module(f"diagnosqui.backends.{module}")
                )

    def test_installed_entry_points_and_styles(self):
        import importlib.metadata

        distribution = importlib.metadata.distribution("diagnosqui")
        entries = {
            entry.name: (entry.group, entry.value)
            for entry in distribution.entry_points
        }
        self.assertEqual(
            entries["diagnosqui"], ("console_scripts", "diagnosqui.cli:main")
        )
        self.assertEqual(
            entries["DiagnosQui-Escritorio"], ("gui_scripts", "diagnosqui.gui_cli:main")
        )
        self.assertEqual(
            entries["diagnosqui-gui"], ("gui_scripts", "diagnosqui.gui_cli:main")
        )
        names = [
            entry.name.casefold()
            for entry in distribution.entry_points
            if entry.group in {"console_scripts", "gui_scripts"}
        ]
        self.assertEqual(
            len(names),
            len(set(names)),
            "Los ejecutables no deben colisionar en Windows",
        )
        from diagnosqui.gui import app

        self.assertTrue(
            (Path(app.__file__).parent / "styles" / "application.qss").is_file()
        )


class TestDesktop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_application()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.settings = QSettings(
            str(Path(self.directory.name) / "settings.ini"), QSettings.Format.IniFormat
        )
        self.settings.setValue("confirm_close", False)
        self.settings.setValue("animations", False)
        self.providers = {
            key: Mock(return_value=fixture(title))
            for key, (title, _) in COMPONENTS.items()
        }
        self.service = DiagnosticService(self.providers)
        metric = MetricSnapshot(42, "Medición de prueba")
        self.telemetry = Mock(
            sample=Mock(
                return_value={
                    "performance": PerformanceSnapshot(metric, metric, metric, metric),
                    "processes": [
                        ProcessSnapshot(1, "trabajador", 80, 4, "prueba", "running"),
                        ProcessSnapshot(2, "cache", 4, 80, "prueba", "sleeping"),
                    ],
                }
            )
        )
        self.window = MainWindow(
            self.service, self.telemetry, self.settings, auto_start=False
        )
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.close()
        self.wait_until(lambda: self.window.controller.workers.finished())
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()
        self.directory.cleanup()

    def wait_until(self, condition, timeout=5):
        deadline = time.monotonic() + timeout
        while not condition() and time.monotonic() < deadline:
            self.app.processEvents()
            QTest.qWait(10)
        self.assertTrue(condition(), "La operación no terminó dentro del límite")

    def test_window_registers_pages_and_navigation_does_not_create_timers(self):
        expected = {
            "inicio",
            *COMPONENTS,
            "procesos",
            "monitor",
            "reportes",
            "configuracion",
        }
        self.assertEqual(set(self.window.pages), expected)
        timers = len(self.window.findChildren(QTimer))
        for _ in range(2):
            for name, page in self.window.pages.items():
                self.window.navigate(name)
                self.assertIs(self.window.stack.currentWidget(), page)
                self.assertTrue(self.window.nav_buttons[name].isChecked())
        self.assertEqual(len(self.window.findChildren(QTimer)), timers)
        self.window.toggle_sidebar()
        self.assertEqual(self.window.sidebar.width(), 72)
        self.window.toggle_sidebar()
        self.assertEqual(self.window.sidebar.width(), 230)

    def test_states_and_chart_history(self):
        for state, color in COLORS.items():
            badge = StatusBadge(state)
            self.assertEqual(badge.text.text(), LABELS[state])
            self.assertIn(state_color(state), badge.text.styleSheet())
        chart = ChartWidget("CPU")
        for value in range(100):
            chart.add_sample(value, "%", value)
        self.assertEqual(len(chart.history), 60)
        self.assertEqual(chart.history[0], 40)
        chart.add_sample(8, "Mbit/s")
        self.assertEqual(list(chart.history), [8])

    def test_diagnostic_runs_off_main_thread_and_controls_recover(self):
        main_thread = threading.get_ident()
        ran = []
        release = threading.Event()

        def collect():
            ran.append(threading.get_ident())
            release.wait(2)
            return fixture()

        self.service.providers["cpu"] = collect
        self.window.controller.collect("cpu")
        self.assertFalse(self.window.components["cpu"].run_button.isEnabled())
        self.window.navigate("configuracion")
        self.assertEqual(self.window.current_page, "configuracion")
        release.set()
        self.wait_until(lambda: "cpu" not in self.window.controller.workers.pending)
        self.assertNotEqual(ran[0], main_thread)
        self.assertTrue(self.window.components["cpu"].run_button.isEnabled())
        self.assertEqual(self.window.components["cpu"].evidence.text(), "42%")

    def test_errors_missing_keys_and_retry_are_visible(self):
        self.service.providers["cpu"] = Mock(
            side_effect=PermissionError("permiso denegado")
        )
        self.window.controller.collect("cpu")
        self.wait_until(lambda: not self.window.controller.workers.pending)
        page = self.window.components["cpu"]
        self.assertIn("permiso denegado", page.error.text())
        self.assertTrue(page.run_button.isEnabled())
        self.service.providers["cpu"] = lambda: {}
        self.window.controller.collect("cpu")
        self.wait_until(lambda: not self.window.controller.workers.pending)
        self.assertEqual(page.evidence.text(), "N/D")

    def test_process_search_sort_pause_and_live_data(self):
        self.window.navigate("procesos")
        self.wait_until(
            lambda: "telemetry" not in self.window.controller.workers.pending
        )
        page = self.window.processes
        self.assertEqual(page.model.rowCount(), 2)
        page.search.setText("cache")
        self.assertEqual(page.proxy.rowCount(), 1)
        page.search.clear()
        page.table.sortByColumn(3, Qt.SortOrder.DescendingOrder)
        self.assertEqual(page.proxy.index(0, 0).data(), "2")
        page.toggle_pause()
        page.set_processes([])
        self.assertEqual(page.model.rowCount(), 2)
        page.toggle_pause()
        page.set_processes([])
        self.assertEqual(page.model.rowCount(), 0)
        self.assertEqual(len(self.window.monitor.charts["cpu"].history), 1)

    def test_close_during_work_finishes_without_updating_destroyed_widgets(self):
        release = threading.Event()
        self.service.providers["cpu"] = lambda: (release.wait(2), fixture())[1]
        self.window.controller.collect("cpu")
        self.window.close()
        self.assertTrue(self.window._closing)
        self.assertFalse(self.window.controller.timer.isActive())
        release.set()
        self.wait_until(lambda: not self.window.isVisible())
        self.assertTrue(self.window.controller.workers.finished())

    def test_complete_report_uses_dialog_and_exports_snapshot(self):
        self.window.controller.refresh_all()
        self.wait_until(lambda: not self.window.controller.workers.pending)
        page = self.window.reports
        self.assertEqual(page.table.rowCount(), len(COMPONENTS))
        with patch(
            "diagnosqui.gui.pages.reports_page.QFileDialog.getExistingDirectory",
            return_value=self.directory.name,
        ):
            page.choose_directory()
        self.assertEqual(page.directory.text(), self.directory.name)
        self.window.controller.export(self.directory.name, ("json", "csv", "html"))
        self.wait_until(lambda: not self.window.controller.workers.pending)
        self.assertIn("Exportación completada", page.message.text())
        self.assertEqual(len(list(Path(self.directory.name).glob("*.html"))), 1)
        self.assertTrue(page.export_button.isEnabled())

    def test_preferences_persist_and_apply_without_more_timers(self):
        page = self.window.preferences
        page.interval.setValue(3)
        page.directory.setText(self.directory.name)
        page.save()
        self.assertEqual(self.window.controller.timer.interval(), 3000)
        saved = QSettings(self.settings.fileName(), QSettings.Format.IniFormat)
        self.assertEqual(saved.value("monitor_interval", type=int), 3)

    def test_export_failure_restores_controls(self):
        self.window.controller.results = {"cpu": fixture()}
        self.window.reports.set_results(self.window.controller.results)
        with patch.object(
            self.service, "export", side_effect=PermissionError("Carpeta protegida")
        ):
            self.window.controller.export(self.directory.name, ("json",))
            self.wait_until(lambda: not self.window.controller.workers.pending)
        self.assertIn("Carpeta protegida", self.window.reports.message.text())
        self.assertTrue(self.window.reports.export_button.isEnabled())

    def test_component_refresh_does_not_reenable_an_export_in_progress(self):
        self.window.controller.results = {"cpu": fixture()}
        self.window.reports.set_results(self.window.controller.results)
        release = threading.Event()

        def export(*args):
            release.wait(2)
            return {"json": str(Path(self.directory.name) / "reporte.json")}

        with patch.object(self.service, "export", side_effect=export):
            self.window.controller.export(self.directory.name, ("json",))
            self.window.controller.collect("cpu")
            self.wait_until(lambda: "cpu" not in self.window.controller.workers.pending)
            self.assertFalse(self.window.reports.export_button.isEnabled())
            release.set()
            self.wait_until(lambda: not self.window.controller.workers.pending)
        self.assertTrue(self.window.reports.export_button.isEnabled())


if __name__ == "__main__":
    unittest.main()
