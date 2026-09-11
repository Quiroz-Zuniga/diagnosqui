"""Comprueba la entrada instalada y los archivos que recibe el usuario."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from diagnosqui.ui import terminal


class TestCliWorkflow(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.environment = dict(os.environ, DIAGNOSQUI_STATE_DIR=self.temp.name)

    def run_cli(self, *arguments, stdin=None):
        return subprocess.run(
            [sys.executable, "-m", "diagnosqui.cli", *arguments],
            input=stdin,
            text=True,
            encoding="utf-8",
            capture_output=True,
            env=dict(self.environment, PYTHONIOENCODING="utf-8"),
            cwd=self.directory,
            timeout=20,
        )

    def test_piped_session_dispatches_commands_and_only_boots_once(self):
        first = self.run_cli(stdin="2\n4\n7\n8\ncomando-inexistente\n0\n")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn("$ npm install -g diagnosqui", first.stdout)
        for component in ("CPU", "PCI", "GPU"):
            self.assertIn(component, first.stdout)
        self.assertNotIn("Traceback", first.stderr)
        self.assertNotIn("Input is not a terminal", first.stderr)
        second = self.run_cli(stdin="17\n")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertNotIn("$ npm install -g diagnosqui", second.stdout)
        self.assertIn("17. Salir", second.stdout)

    def test_direct_command_returns_failure_for_unknown_command(self):
        result = self.run_cli("--command", "comando-inexistente")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("$ npm install", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_monitor_without_terminal_returns_instead_of_hanging(self):
        result = self.run_cli("--command", "monitor")
        self.assertEqual(result.returncode, 1)
        self.assertIn("terminal", (result.stdout + result.stderr).casefold())
        self.assertNotIn("Traceback", result.stderr)

    def test_setup_can_be_repeated_and_does_not_wait_for_input(self):
        for _ in range(2):
            result = self.run_cli("--setup")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("added 8 packages", result.stdout)
            self.assertNotIn("17. Salir", result.stdout)

    def test_setup_command_uses_the_boot_api(self):
        result = self.run_cli("--command", "setup")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("added 8 packages", result.stdout)

    def test_exports_keep_contract_and_do_not_overwrite_previous_report(self):
        destination = self.directory / "exports"
        for _ in range(2):
            result = self.run_cli("-c", "15", "--output-dir", str(destination))
            self.assertEqual(result.returncode, 0, result.stderr)
        reports = list(destination.glob("*.json"))
        self.assertEqual(len(reports), 2)
        for report in reports:
            rows = json.loads(report.read_text(encoding="utf-8"))
            self.assertTrue(rows)
            self.assertEqual(
                set(rows[0]),
                {"componente", "evidencia", "valor_numerico", "estado", "detalle", "recomendacion"},
            )
        result = self.run_cli("--export-html", "--output-dir", str(destination))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(list(destination.glob("*.html"))), 1)
        self.assertEqual(len(list(destination.glob("*.csv"))), 1)

    def test_cli_import_and_fixture_command_do_not_load_core(self):
        script = '''
import importlib.abc
import sys
class RejectCore(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(("diagnosqui.core", "diagnosqui.backends", "diagnosqui.diagnostico")):
            raise AssertionError("La UI intentó consultar módulos de hardware: " + fullname)
sys.meta_path.insert(0, RejectCore())
from diagnosqui.cli import main
raise SystemExit(main(["--command", "cpu"]))
'''
        result = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True,
            env=dict(self.environment, PYTHONIOENCODING="utf-8"), timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CPU", result.stdout)

    def test_html_export_escapes_diagnostic_text(self):
        results = terminal.get_fixture_results("cpu")
        results[0]["evidencia"] = '<script>alert("fixture")</script>'
        results[0]["recomendacion"] = ["Conservar <datos> & comprobar"]
        paths = terminal.export_fixture_report(results, self.directory, formats=("html",))
        html = paths["html"].read_text(encoding="utf-8")
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("&lt;datos&gt;", html)


if __name__ == "__main__":
    unittest.main()
