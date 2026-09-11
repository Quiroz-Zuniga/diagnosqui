"""Cálculos de telemetría y ciclo de vida del monitor sin hardware de prueba."""

from __future__ import annotations

import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import psutil
from textual.widgets import TabbedContent

from diagnosqui.ui import monitor_tui as monitor
from diagnosqui.ui.theme import WARNING_COLOR


class TestSystemSampler(unittest.TestCase):
    def setUp(self):
        self.sampler = monitor.SystemSampler.__new__(monitor.SystemSampler)
        self.sampler._last_disks = {}
        self.sampler._last_network = {}

    def test_process_cpu_is_normalized_and_inaccessible_processes_are_skipped(self):
        class GoneProcess:
            @property
            def info(self):
                raise psutil.NoSuchProcess(7)

        processes = [
            SimpleNamespace(info=dict(pid=1, name="worker", cpu_percent=400, memory_percent=20)),
            GoneProcess(),
            SimpleNamespace(info=dict(pid=2, name="protected", cpu_percent=None, memory_percent=None)),
        ]
        with patch.object(monitor.psutil, "process_iter", return_value=processes), patch.object(
            monitor.psutil, "cpu_count", return_value=8
        ):
            rows = self.sampler.read_processes()
        self.assertEqual(rows, [monitor.ProcessSnapshot(1, "worker", 50, 20)])

    def test_disk_activity_uses_maximum_instead_of_adding_duplicate_devices(self):
        self.sampler._last_disks = {name: (0, 0, 100) for name in ("sda", "sda1")}
        with patch.object(self.sampler, "_disk_usage_detail", return_value="92% ocupado"):
            metric = self.sampler._disk_metric(
                {name: (1024**2, 0, 800) for name in ("sda", "sda1")}, 1
            )
        self.assertEqual(metric.percent, 70)
        self.assertIn("1.00 MiB/s", metric.detail)

    def test_disk_without_busy_time_reports_rate_and_keeps_occupancy_separate(self):
        self.sampler._last_disks = {"disk": (0, 0, None)}
        with patch.object(self.sampler, "_disk_usage_detail", return_value="92% ocupado"):
            metric = self.sampler._disk_metric({"disk": (1024**2, 1024**2, None)}, 1)
        self.assertIsNone(metric.percent)
        self.assertEqual((metric.graph_value, metric.unit), (2, "MiB/s"))
        self.assertIn("92% ocupado", metric.detail)

    def test_unknown_network_capacity_never_creates_a_fake_percentage(self):
        self.sampler._last_network = {"wlan": (0, 0, 0)}
        metric = self.sampler._network_metric({"wlan": (500_000, 500_000, 0)}, 1)
        self.assertIsNone(metric.percent)
        self.assertEqual(metric.graph_value, 8)
        self.assertEqual(metric.unit, "Mbit/s")
        self.assertIn("capacidad no reportada", metric.detail)

    def test_known_network_capacity_uses_directional_utilization(self):
        self.sampler._last_network = {"eth": (0, 0, 100)}
        metric = self.sampler._network_metric({"eth": (10_000_000, 10_000_000, 100)}, 1)
        self.assertEqual(metric.percent, 80)
        self.assertEqual(metric.graph_value, 160)

    def test_hotplug_and_reset_counters_do_not_generate_traffic_spikes(self):
        self.sampler._last_network = {"eth": (10_000, 10_000, 100)}
        metric = self.sampler._network_metric(
            {"eth": (0, 0, 100), "new": (10**12, 10**12, 100)}, 1
        )
        self.assertIsNone(metric.percent)
        self.assertIsNone(metric.graph_value)


class TestMonitorLifecycle(unittest.IsolatedAsyncioTestCase):
    async def test_refresh_sort_colors_and_exit_with_narrow_layout(self):
        metric = monitor.MetricSnapshot(76, "fixture")
        sampler = Mock(
            read_processes=Mock(return_value=[
                monitor.ProcessSnapshot(1, "cpu-worker", 80, 4),
                monitor.ProcessSnapshot(2, "memory-worker", 4, 80),
            ]),
            sample_performance=Mock(return_value=monitor.PerformanceSnapshot(metric, metric, metric, metric)),
        )
        app = monitor.DiagnosQuiMonitor(sampler=sampler)
        started = time.monotonic()
        async with app.run_test(size=(60, 24)) as pilot:
            await pilot.pause()
            self.assertIn("narrow", app.query_one("#metrics-grid").classes)
            table = app.query_one("#process-table")
            self.assertEqual(table.get_row_at(0)[0], "1")
            await pilot.press("m")
            self.assertEqual(table.get_row_at(0)[0], "2")
            app.query_one(TabbedContent).active = "performance-pane"
            await pilot.pause(1.1)
            self.assertGreaterEqual(sampler.sample_performance.call_count, 2)
            graph = app.query_one("#cpu-graph")
            color = graph.get_component_rich_style("sparkline--min-color").color
            self.assertEqual(color.get_truecolor().hex, WARNING_COLOR)
            for _ in range(65):
                app._render_performance(sampler.sample_performance.return_value)
            self.assertEqual(len(app._histories["cpu"]), 60)
            await pilot.press("q")
        self.assertFalse(app._sampling_thread.is_alive())
        self.assertLess(time.monotonic() - started, 10)

    async def test_sampler_errors_are_visible_and_refresh_recovers(self):
        metric = monitor.MetricSnapshot(42, "fixture")
        sampler = Mock(
            read_processes=Mock(side_effect=[OSError("lectura fallida"), []]),
            sample_performance=Mock(return_value=monitor.PerformanceSnapshot(metric, metric, metric, metric)),
        )
        app = monitor.DiagnosQuiMonitor(sampler=sampler)
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.pause()
            self.assertIn("lectura fallida", str(app.query_one("#process-toolbar").render()))
            await pilot.press("r")
            await pilot.pause()
            self.assertIn("No hay procesos", str(app.query_one("#process-toolbar").render()))
        self.assertFalse(app._sampling_thread.is_alive())


if __name__ == "__main__":
    unittest.main()
