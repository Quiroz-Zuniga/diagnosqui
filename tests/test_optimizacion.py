"""
Pruebas del módulo de optimización de Windows.

``temporales`` se prueba con directorios temporales reales (dry-run y
borrado efectivo). ``telemetria`` se prueba con mocks para simular el uso
de PowerShell en Windows sin ejecutarlo en Linux. El flujo del menú se
verifica por ramas inyectables.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from diagnosqui.optimizacion.safety import (
    confirmar,
    direccion_estado,
    registrar_log,
    ubicacion_log,
)
from diagnosqui.optimizacion import telemetria
from diagnosqui.optimizacion.temporales import (
    contrato_estado,
    escanear_temporales,
    limpiar_temporales,
    resumen_temporales,
)
from diagnosqui.optimizacion.menu_optimizacion import run_optimizacion
from diagnosqui.ui import terminal


class TestSafety(unittest.TestCase):
    def test_direccion_estado_honra_variable_por_usuario(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with patch.dict(os.environ, {"DIAGNOSQUI_STATE_DIR": carpeta}):
                self.assertEqual(direccion_estado(), Path(carpeta))
                self.assertTrue(str(ubicacion_log()).startswith(carpeta))
                self.assertEqual(ubicacion_log().name, "optimizacion.log")

    def test_registrar_log_crea_entradas_auditables(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with patch.dict(os.environ, {"DIAGNOSQUI_STATE_DIR": carpeta}):
                ruta = registrar_log("temporales/limpiar", "bytes=1024", estado="OK")
                contenido = ruta.read_text(encoding="utf-8")
                self.assertIn("temporales/limpiar", contenido)
                self.assertIn("bytes=1024", contenido)
                self.assertIn("[", contenido)

    def test_confirmar_acepta_si_y_rechaza_no(self):
        with patch("builtins.input", return_value="s"):
            self.assertTrue(confirmar("¿Continuar?"))
        with patch("builtins.input", return_value="no"):
            self.assertFalse(confirmar("¿Continuar?", por_defecto=True))
        with patch("builtins.input", return_value="tal vez"):
            self.assertFalse(confirmar("¿Continuar?"))


class TestTemporales(unittest.TestCase):
    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(self.carpeta.cleanup)
        self.raiz = Path(self.carpeta.name)
        (self.raiz / "uno.tmp").write_text("a" * 100, encoding="utf-8")
        (self.raiz / "dos.tmp").write_text("b" * 200, encoding="utf-8")

    def test_escaneo_y_resumen(self):
        archivos = escanear_temporales([str(self.raiz)])
        self.assertEqual(len(archivos), 2)
        resumen = resumen_temporales([str(self.raiz)])
        self.assertEqual(resumen["total_archivos"], 2)
        self.assertEqual(resumen["bytes_totales"], 300)
        self.assertIn(str(self.raiz), resumen["por_ruta"])

    def test_dry_run_no_borra_y_reporta_prevision(self):
        archivos = escanear_temporales([str(self.raiz)])
        prevision = limpiar_temporales(archivos, dry_run=True)
        self.assertEqual(prevision["bytes_liberados"], 300)
        self.assertEqual(prevision["eliminados"], 2)
        self.assertTrue((self.raiz / "uno.tmp").exists())

    def test_limpieza_efectiva_remueve_archivos(self):
        archivos = escanear_temporales([str(self.raiz)])
        resultado = limpiar_temporales(archivos, dry_run=False)
        self.assertEqual(resultado["eliminados"], 2)
        self.assertEqual(resultado["bytes_liberados"], 300)
        self.assertFalse((self.raiz / "uno.tmp").exists())

    def test_contrato_de_estado_conserva_claves(self):
        contrato = contrato_estado([str(self.raiz)])
        self.assertEqual(
            set(contrato),
            {"componente", "evidencia", "valor_numerico", "estado", "detalle", "recomendacion"},
        )
        self.assertEqual(contrato["valor_numerico"], 2)


class TestTelemetria(unittest.TestCase):
    @patch.object(telemetria, "_es_windows", return_value=False)
    def test_consulta_fuera_de_windows_es_de_solo_lectura(self, _mock):
        filas = telemetria.consultar_estado()
        self.assertEqual(len(filas), 1)
        self.assertIn("No disponible", filas[0]["estado_actual"])
        self.assertFalse(filas[0]["aplicable"])

    @patch.object(telemetria, "_powershell", return_value="OK")
    @patch.object(telemetria, "_leer_registro", return_value="1")
    @patch.object(telemetria, "_estado_tarea", return_value="Habilitada")
    @patch.object(telemetria, "_estado_servicio", return_value="Running")
    @patch.object(telemetria, "_es_windows", return_value=True)
    def test_deshabilitar_en_dry_run_no_ejecuta(self, _win, _servicio, _tarea, _reg, _ps):
        filas = telemetria.consultar_estado()
        self.assertEqual(len(filas), 4)
        resultados = telemetria.aplicar_telemetria(dry_run=True)
        self.assertTrue(all("dry-run" in r["resultado"] for r in resultados))
        _ps.assert_not_called()


class TestMenuOptimizacion(unittest.TestCase):
    def test_fuera_de_windows_devuelve_codigo_de_error(self):
        with patch("diagnosqui.optimizacion.menu_optimizacion.estado_del_sistema",
                   return_value={"plataforma": "Linux", "es_administrador": True, "usuario": "t", "version_os": "1"}):
            self.assertEqual(run_optimizacion(confirmar_fn=lambda pregunta: False), 1)

    def test_sin_admin_no_intenta_cambios(self):
        with patch("diagnosqui.optimizacion.menu_optimizacion.estado_del_sistema",
                   return_value={"plataforma": "Windows", "es_administrador": False, "usuario": "t", "version_os": "1"}):
            self.assertEqual(run_optimizacion(confirmar_fn=lambda pregunta: True), 1)

    def test_dispatch_linux_mantiene_aviso_sin_llamar_al_motor(self):
        console, stream = _memory_console()
        fixture = Mock()
        terminal.dispatch_command(
            "16",
            console_instance=console,
            fixture_provider=fixture,
            system_name="Linux",
        )
        fixture.assert_not_called()
        self.assertIn("solo esta disponible en Windows", stream.getvalue())

    def test_dispatch_windows_usa_el_runner_inyectado(self):
        console, stream = _memory_console()
        runner = Mock(return_value=None)
        action = terminal.dispatch_command(
            "16",
            console_instance=console,
            fixture_provider=Mock(),
            optimization_runner=runner,
            system_name="Windows",
        )
        runner.assert_called_once()
        self.assertIsNot(action, terminal.ShellAction.EXIT)


from rich.console import Console  # noqa: E402


def _memory_console():
    import io

    from diagnosqui.ui import theme

    stream = io.StringIO()
    return Console(file=stream, theme=theme.DIAGNOSQUI_THEME, force_terminal=False,
                   color_system=None, width=180, legacy_windows=False), stream


if __name__ == "__main__":
    unittest.main()