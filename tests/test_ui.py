"""Pruebas de contrato para la interfaz de terminal de DiagnosQui.

Las pruebas usan consolas en memoria y mocks: no necesitan una TTY, no abren la
aplicación Textual y no consultan hardware real.
"""

from __future__ import annotations

import io
import numbers
import os
import tempfile
import unittest
from collections.abc import Mapping, Sequence
from unittest.mock import Mock, patch

from rich.console import Console
from rich.table import Table

from diagnosqui import cli
from diagnosqui.ui import boot, monitor_tui, terminal, theme


EXPECTED_NUMBER_ALIASES = {
    "1": "general",
    "2": "cpu",
    "3": "memoria",
    "4": "pci",
    "5": "red",
    "6": "usb",
    "7": "disco",
    "8": "gpu",
    "9": "controladores",
    "10": "problemas",
    "11": "conectividad",
    "12": "monitor",
    "13": "recomendaciones",
    "14": "reporte",
    "15": "exportar",
    "16": "optimizacion",
    "17": "salir",
    "0": "salir",
}

REQUIRED_RESULT_KEYS = {
    "componente",
    "evidencia",
    "valor_numerico",
    "estado",
    "detalle",
    "recomendacion",
}
VALID_STATES = {"NORMAL", "ADVERTENCIA", "CRITICO"}


def _as_results(value: object) -> list[Mapping[str, object]]:
    """Normaliza el retorno público de fixtures sin imponer lista o tupla."""

    if isinstance(value, Mapping):
        return [value]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return list(value)
    raise AssertionError(
        "Un fixture debe ser un diccionario de resultado o una secuencia de ellos"
    )


def _memory_console() -> tuple[Console, io.StringIO]:
    stream = io.StringIO()
    return (
        Console(
            file=stream,
            theme=theme.DIAGNOSQUI_THEME,
            force_terminal=False,
            color_system=None,
            width=180,
            legacy_windows=False,
        ),
        stream,
    )


class TestSharedTheme(unittest.TestCase):
    def test_percentage_thresholds_are_shared_at_70_and_90_percent(self):
        self.assertIs(theme.style_for_percentage(69.99), theme.NORMAL_STYLE)
        self.assertIs(theme.style_for_percentage(70), theme.WARNING_STYLE)
        self.assertIs(theme.style_for_percentage(89.99), theme.WARNING_STYLE)
        self.assertIs(theme.style_for_percentage(90), theme.CRITICAL_STYLE)

    def test_fixture_states_have_semantic_styles(self):
        self.assertIs(theme.style_for_status("NORMAL"), theme.NORMAL_STYLE)
        self.assertIs(theme.style_for_status("advertencia"), theme.WARNING_STYLE)
        self.assertIs(theme.style_for_status("CRÍTICO"), theme.CRITICAL_STYLE)


class TestBoot(unittest.TestCase):
    def test_boot_log_renders_without_a_real_terminal_or_delays(self):
        console, stream = _memory_console()
        with patch.object(boot, "console", console):
            boot.run_boot_animation()

        rendered = stream.getvalue()
        self.assertIn("$ npm install -g diagnosqui", rendered)
        for package, version, _description in boot.PACKAGES_SIMULATED:
            self.assertIn(f"{package}@{version}", rendered)
        self.assertIn(
            f"added {len(boot.PACKAGES_SIMULATED)} packages", rendered
        )

    def test_boot_uses_the_requested_braille_spinner_sequence(self):
        self.assertEqual(boot.BRAILLE_SPINNER_FRAMES, "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏")


class TestTerminalFixtures(unittest.TestCase):
    def test_fixture_catalog_uses_the_diagnostic_contract(self):
        fixtures = terminal.FIXTURES
        self.assertIs(terminal.DIAGNOSTIC_FIXTURES, fixtures)
        self.assertIsInstance(fixtures, Mapping)
        self.assertTrue(fixtures, "El catálogo de fixtures no puede quedar vacío")

        results: list[Mapping[str, object]] = []
        for fixture in fixtures.values():
            results.extend(_as_results(fixture))

        self.assertTrue(results)
        for result in results:
            with self.subTest(component=result.get("componente")):
                self.assertEqual(set(result), REQUIRED_RESULT_KEYS)
                self.assertIsInstance(result["componente"], str)
                self.assertTrue(result["componente"].strip())
                self.assertIsInstance(result["evidencia"], str)
                self.assertIsInstance(result["valor_numerico"], numbers.Real)
                self.assertNotIsInstance(result["valor_numerico"], bool)
                self.assertIn(result["estado"], VALID_STATES)
                self.assertIsInstance(result["detalle"], dict)
                self.assertIsInstance(result["recomendacion"], list)
                self.assertTrue(result["recomendacion"])
                self.assertTrue(
                    all(isinstance(line, str) and line for line in result["recomendacion"])
                )

    def test_cpu_fixture_is_available_through_public_accessor(self):
        results = _as_results(terminal.get_fixture_results("cpu"))
        self.assertTrue(results)
        self.assertTrue(
            any(result["componente"].strip().upper() == "CPU" for result in results)
        )


class TestTerminalCommands(unittest.TestCase):
    def test_names_and_numeric_aliases_resolve_to_the_same_command(self):
        for number, command in EXPECTED_NUMBER_ALIASES.items():
            with self.subTest(number=number, command=command):
                self.assertEqual(terminal.resolve_command(number), command)
                self.assertEqual(terminal.resolve_command(command), command)

    def test_resolution_is_case_insensitive_and_ignores_outer_whitespace(self):
        self.assertEqual(terminal.resolve_command("  CPU  "), "cpu")
        self.assertEqual(terminal.resolve_command(" SALIR "), "salir")

    def test_unknown_and_empty_commands_do_not_resolve(self):
        self.assertIsNone(terminal.resolve_command(""))
        self.assertIsNone(terminal.resolve_command("comando-inexistente"))

    def test_result_table_has_one_row_and_only_first_recommendation(self):
        result = {
            "componente": "CPU",
            "evidencia": "42%",
            "valor_numerico": 42,
            "estado": "NORMAL",
            "detalle": {"fuente": "fixture"},
            "recomendacion": ["Primera recomendación", "No debe mostrarse"],
        }

        table = terminal.build_result_table(result)

        self.assertIsInstance(table, Table)
        self.assertEqual(len(table.rows), 1)
        headers = {str(column.header).casefold() for column in table.columns}
        self.assertEqual(
            headers,
            {"componente", "evidencia", "estado", "recomendación"},
        )

        console, stream = _memory_console()
        console.print(table)
        rendered = stream.getvalue()
        self.assertIn("CPU", rendered)
        self.assertIn("42%", rendered)
        self.assertIn("NORMAL", rendered)
        self.assertIn("Primera recomendación", rendered)
        self.assertNotIn("No debe mostrarse", rendered)

    def test_numeric_command_dispatches_the_canonical_fixture_name(self):
        console, stream = _memory_console()
        fixture_provider = Mock(return_value=terminal.get_fixture_results("cpu"))

        action = terminal.dispatch_command(
            "2",
            console_instance=console,
            fixture_provider=fixture_provider,
            system_name="Linux",
        )

        fixture_provider.assert_called_once_with("cpu")
        self.assertIsNot(action, terminal.ShellAction.EXIT)
        self.assertIn("CPU", stream.getvalue())

    def test_monitor_runner_is_injected_and_returns_control_to_the_shell(self):
        console, _stream = _memory_console()
        monitor_runner = Mock()

        action = terminal.dispatch_command(
            "12",
            console_instance=console,
            monitor_runner=monitor_runner,
            system_name="Linux",
        )

        monitor_runner.assert_called_once_with()
        self.assertIsNot(action, terminal.ShellAction.EXIT)

    def test_windows_optimization_alias_is_safe_on_linux(self):
        console, stream = _memory_console()
        fixture_provider = Mock()

        action = terminal.dispatch_command(
            "16",
            console_instance=console,
            fixture_provider=fixture_provider,
            system_name="Linux",
        )

        fixture_provider.assert_not_called()
        self.assertIsNot(action, terminal.ShellAction.EXIT)
        self.assertIn("solo esta disponible en Windows", stream.getvalue())


class TestMonitorWithoutTerminal(unittest.TestCase):
    def test_monitor_reuses_shared_thresholds_and_palette(self):
        self.assertEqual(monitor_tui.NORMAL_LIMIT, theme.WARNING_THRESHOLD)
        self.assertEqual(monitor_tui.CRITICAL_LIMIT, theme.CRITICAL_THRESHOLD)
        self.assertEqual(monitor_tui.REFRESH_SECONDS, 1.0)

        css = monitor_tui.DiagnosQuiMonitor.CSS.casefold()
        for color in (
            theme.NORMAL_COLOR,
            theme.WARNING_COLOR,
            theme.CRITICAL_COLOR,
        ):
            with self.subTest(color=color):
                self.assertIn(color.casefold(), css)

    def test_monitor_threshold_levels_change_at_70_and_90(self):
        self.assertEqual(monitor_tui.threshold_level(69.99), "normal")
        self.assertEqual(monitor_tui.threshold_level(70), "warning")
        self.assertEqual(monitor_tui.threshold_level(89.99), "warning")
        self.assertEqual(monitor_tui.threshold_level(90), "critical")

    def test_process_rows_can_be_sorted_by_cpu_or_memory(self):
        app = monitor_tui.DiagnosQuiMonitor(sampler=Mock())
        app._process_rows = [
            monitor_tui.ProcessSnapshot(10, "cpu-heavy", 80.0, 10.0),
            monitor_tui.ProcessSnapshot(20, "memory-heavy", 15.0, 90.0),
            monitor_tui.ProcessSnapshot(30, "quiet", 2.0, 3.0),
        ]

        app._sort_field = "cpu"
        app._sort_descending = True
        self.assertEqual(
            [row.pid for row in app._sorted_process_rows()],
            [10, 20, 30],
        )

        app._sort_field = "memory"
        self.assertEqual(
            [row.pid for row in app._sorted_process_rows()],
            [20, 10, 30],
        )

    def test_monitor_has_q_and_escape_exit_bindings(self):
        keys = {binding.key for binding in monitor_tui.DiagnosQuiMonitor.BINDINGS}
        self.assertTrue({"q", "escape"}.issubset(keys))


class TestMonitorHeadless(unittest.IsolatedAsyncioTestCase):
    async def test_two_tabs_receive_processes_and_live_metric_states(self):
        class FakeSampler:
            def read_processes(self):
                return [
                    monitor_tui.ProcessSnapshot(10, "worker", 80.0, 12.0),
                    monitor_tui.ProcessSnapshot(20, "cache", 5.0, 72.0),
                ]

            def sample_performance(self):
                return monitor_tui.PerformanceSnapshot(
                    cpu=monitor_tui.MetricSnapshot(42.0, "CPU fixture"),
                    memory=monitor_tui.MetricSnapshot(73.0, "RAM fixture"),
                    disk=monitor_tui.MetricSnapshot(91.0, "Disco fixture"),
                    network=monitor_tui.MetricSnapshot(12.0, "Red fixture"),
                )

        app = monitor_tui.DiagnosQuiMonitor(sampler=FakeSampler())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            self.assertIsNotNone(app.query_one("#processes-pane"))
            self.assertIsNotNone(app.query_one("#performance-pane"))
            self.assertEqual(app.query_one("#process-table").row_count, 2)
            self.assertIn("warning", app.query_one("#memory-card").classes)
            self.assertIn("critical", app.query_one("#disk-card").classes)
            await pilot.press("escape")


class TestCli(unittest.TestCase):
    def test_parser_accepts_setup_without_reading_a_terminal(self):
        args = cli.build_parser().parse_args(["--setup"])
        self.assertTrue(args.setup)

    def test_setup_runs_boot_and_does_not_enter_interactive_shell(self):
        with patch.object(cli, "run_boot_animation") as run_boot, patch.object(
            cli, "run_interactive_shell"
        ) as run_shell:
            cli.main(["--setup"])

        run_boot.assert_called_once()
        run_shell.assert_not_called()

    def test_linux_menu_hides_windows_optimization(self):
        console, stream = _memory_console()
        cli.print_main_menu(system_name="Linux", console_instance=console)
        rendered = stream.getvalue()

        self.assertIn("1. Diagnóstico general", rendered)
        self.assertIn("15. Exportar diagnóstico", rendered)
        self.assertIn("17. Salir", rendered)
        self.assertNotIn("16. Optimización de Windows", rendered)

    def test_windows_menu_includes_windows_optimization(self):
        console, stream = _memory_console()
        cli.print_main_menu(system_name="Windows", console_instance=console)
        rendered = stream.getvalue()

        self.assertIn("16. Optimización de Windows", rendered)
        self.assertIn("17. Salir", rendered)

    def test_boot_marker_records_first_run_in_configured_state_directory(self):
        with tempfile.TemporaryDirectory() as state_dir:
            with patch.dict(
                os.environ, {"DIAGNOSQUI_STATE_DIR": state_dir}, clear=False
            ):
                self.assertTrue(cli.is_first_run())
                self.assertTrue(cli.mark_boot_completed())
                self.assertFalse(cli.is_first_run())
                self.assertTrue(cli.boot_marker_path().is_file())

    def test_default_main_boots_once_then_reuses_the_marker(self):
        with tempfile.TemporaryDirectory() as state_dir:
            with patch.dict(
                os.environ, {"DIAGNOSQUI_STATE_DIR": state_dir}, clear=False
            ):
                with patch.object(cli, "run_boot_animation") as run_boot:
                    with patch.object(cli, "print_main_menu") as print_menu:
                        with patch.object(
                            cli, "run_interactive_shell"
                        ) as run_shell:
                            with patch.object(
                                cli.platform, "system", return_value="Linux"
                            ):
                                self.assertEqual(cli.main([]), 0)
                                self.assertEqual(cli.main([]), 0)

        run_boot.assert_called_once_with()
        self.assertEqual(print_menu.call_count, 2)
        self.assertEqual(run_shell.call_count, 2)


if __name__ == "__main__":
    unittest.main()
