"""Regresiones del sistema visual: plataforma, contraste, persistencia y geometría."""
from __future__ import annotations
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QSettings, QTimer, Qt
from PySide6.QtGui import QPalette
from PySide6.QtTest import QTest
from diagnosqui.gui.app import create_application
from diagnosqui.gui.controller import Controller
from diagnosqui.gui.main_window import MainWindow
from diagnosqui.gui.platform_theme import PlatformIdentity, detect_platform, read_os_release
from diagnosqui.gui.services.diagnostic_service import COMPONENTS, DiagnosticService
from diagnosqui.gui.theme import COLORS, format_percentage, percentage_state, state_color
from diagnosqui.gui.visual_tokens import PALETTES, build_tokens, contrast_ratio
from diagnosqui.gui.widgets.icons import DIRECTORY, NAV_ICONS, icon
from diagnosqui.core.telemetry import MetricSnapshot, PerformanceSnapshot


def result(title):
    return dict(componente=title, evidencia='Lectura de prueba', valor_numerico=42,
                estado='NORMAL', detalle={'fuente': 'fixture'}, recomendacion=['No se requieren acciones.'])


class TestPlatformTokens(unittest.TestCase):
    def test_platform_detection_is_independent_from_hardware_and_commands(self):
        with patch('subprocess.run', side_effect=AssertionError('No ejecutar comandos')):
            self.assertEqual(detect_platform('Windows', {'ID': 'ubuntu'}).key, 'windows')
            for distro in ('ubuntu', 'debian'):
                self.assertEqual(detect_platform('Linux', {'ID': distro}).key, distro)
            for release in ({}, {'ID': 'arch'}, {'ID': 'mint', 'ID_LIKE': 'ubuntu debian'}):
                self.assertEqual(detect_platform('Linux', release).key, 'linux')

    def test_os_release_is_data_and_malformed_lines_are_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'os-release'
            path.write_text('ID="ubuntu"\nPRETTY_NAME="Ubuntu Linux"\nNAME="broken\nEVIL=$(touch bad)\n')
            self.assertEqual(read_os_release(path), {'ID': 'ubuntu', 'PRETTY_NAME': 'Ubuntu Linux'})
            self.assertEqual(read_os_release(Path(directory) / 'missing'), {})

    def test_requested_palettes_and_semantic_colors_are_preserved(self):
        self.assertEqual(COLORS, {'NORMAL': '#218739', 'ADVERTENCIA': '#B77900', 'CRITICO': '#C42B1C'})
        for platform, palette in PALETTES.items():
            tokens = build_tokens(platform)
            self.assertEqual((tokens.bg, tokens.surface, tokens.sidebar, tokens.text_primary,
                              tokens.text_secondary, tokens.accent, tokens.accent_soft, tokens.border), palette)
            self.assertNotEqual(tokens.accent, COLORS['CRITICO'])

    def test_text_contrast_in_all_platforms_and_modes(self):
        for platform in PALETTES:
            for mode in ('light', 'dark'):
                tokens = build_tokens(platform, mode)
                for foreground, background in ((tokens.text_primary, tokens.bg),
                        (tokens.text_secondary, tokens.bg), (tokens.text_secondary, tokens.surface),
                        (tokens.accent_ink, tokens.accent_soft), (tokens.on_accent, tokens.accent)):
                    with self.subTest(platform=platform, mode=mode, pair=(foreground, background)):
                        self.assertGreaterEqual(contrast_ratio(foreground, background), 4.5)
                for state in COLORS:
                    self.assertGreaterEqual(contrast_ratio(tokens.state_ink(state), tokens.surface), 4.5)
                self.assertGreaterEqual(contrast_ratio(tokens.focus, tokens.bg), 3)

    def test_thresholds_and_rounding_do_not_change_diagnostic_states(self):
        for value, state, shown in ((69.99, 'NORMAL', '69.9 %'), (70, 'ADVERTENCIA', '70.0 %'),
                (85, 'ADVERTENCIA', '85.0 %'), (89.99, 'ADVERTENCIA', '89.9 %'), (90, 'CRITICO', '90.0 %')):
            self.assertEqual(percentage_state(value), state)
            self.assertEqual(format_percentage(value), shown)
        self.assertEqual(format_percentage(None), 'N/D')


class TestVisualDesktop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_application()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        settings = QSettings(str(Path(self.directory.name) / 'settings.ini'), QSettings.Format.IniFormat)
        settings.setValue('confirm_close', False)
        settings.setValue('animations', False)
        providers = {key: (lambda name=title: result(name)) for key, (title, _) in COMPONENTS.items()}
        self.service = DiagnosticService(providers)
        self.window = MainWindow(self.service, Mock(sample=Mock(return_value={})), settings, auto_start=False)
        self.window.controller._completed('full', self.service.collect_all(), '')
        metric = MetricSnapshot(42, 'Medición de prueba')
        self.window.controller._completed('telemetry', {'performance': PerformanceSnapshot(metric, metric, metric, metric)}, '')
        self.window.show()
        self.app.processEvents()
        self.original_platform = self.app.theme_manager.platform

    def tearDown(self):
        self.window.close()
        for _ in range(200):
            self.app.processEvents()
            if self.window.controller.workers.finished():
                break
            QTest.qWait(5)
        self.assertTrue(self.window.controller.workers.finished())
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()
        self.app.theme_manager.platform = self.original_platform
        self.app.theme_manager.apply('light')
        self.directory.cleanup()

    def test_default_light_and_persisted_appearance(self):
        self.assertEqual(self.app.property('appearance'), 'light')
        page = self.window.preferences
        page.appearance.setCurrentIndex(page.appearance.findData('dark'))
        page.save()
        self.assertEqual(self.app.property('appearance'), 'dark')
        self.assertEqual(self.window.settings.value('appearance'), 'dark')
        self.assertEqual(self.app.palette().color(QPalette.ColorRole.Window).name(), '#242629')
        page.appearance.setCurrentIndex(page.appearance.findData('light'))
        page.save()
        self.assertEqual(self.app.property('appearance'), 'light')

    def test_system_preference_follows_qt_without_overriding_explicit_mode(self):
        manager = self.app.theme_manager
        manager.apply('system')
        expected = 'dark' if self.app.styleHints().colorScheme() == Qt.ColorScheme.Dark else 'light'
        self.assertEqual(manager.tokens.mode, expected)
        manager.apply('light')
        before = manager.tokens
        manager._system_changed()
        self.assertEqual(manager.tokens, before)

    def test_theme_changes_repaint_states_without_losing_data_or_timers(self):
        def own_timers():
            return [t for t in self.window.findChildren(QTimer)
                    if isinstance(t.parent(), (MainWindow, Controller))]

        saved = dict(self.window.controller.results)
        history = list(self.window.monitor.charts['cpu'].history)
        timers = len(own_timers())
        for platform in PALETTES:
            self.app.theme_manager.platform = PlatformIdentity(platform, platform.capitalize())
            for mode in ('light', 'dark'):
                self.app.theme_manager.apply(mode)
                self.app.processEvents()
                self.assertEqual(self.window.platform_label.text(), platform.capitalize())
                self.assertEqual(self.window.controller.results, saved)
                self.assertEqual(list(self.window.monitor.charts['cpu'].history), history)
                self.assertIn(state_color('NORMAL'), self.window.components['cpu'].badge.text.styleSheet())
                self.assertEqual(len(own_timers()), timers)

    def test_all_pages_fit_requested_resolutions(self):
        for width, height in ((1366, 768), (1600, 900), (1920, 1080), (2560, 1440)):
            self.window.resize(width, height)
            for key in self.window.pages:
                self.window.navigate(key)
                self.app.processEvents()
                with self.subTest(resolution=(width,height), page=key):
                    self.assertEqual((self.window.width(),self.window.height()), (width,height))
                    self.assertEqual(self.window.stack.currentWidget(), self.window.pages[key])
            self.window.navigate('inicio')
            self.app.processEvents()
            self.assertEqual(self.window.dashboard.scroll.horizontalScrollBar().maximum(), 0)
            self.assertEqual(self.window.dashboard.scroll.verticalScrollBar().maximum(), 0)

    def test_long_details_scroll_instead_of_expanding_window(self):
        long = result('CPU')
        long['recomendacion'] = ['Una recomendación extensa y legible.'] * 60
        self.window.components['cpu'].set_result(long)
        self.window.navigate('cpu')
        self.app.processEvents()
        self.assertEqual(self.window.height(), 768)
        self.assertGreater(self.window.components['cpu'].scroll.verticalScrollBar().maximum(), 0)

    def test_collapsed_navigation_preserves_keyboard_and_accessible_names(self):
        self.window.toggle_sidebar()
        self.assertTrue(all(not category.isVisible() for category in self.window.nav_categories))
        self.assertFalse(self.window.side_footer.isVisible())
        target = self.window.nav_buttons['cpu']
        self.assertEqual(target.accessibleName(), 'CPU')
        self.assertEqual(target.text(), '')
        target.setFocus()
        QTest.keyClick(target, Qt.Key.Key_Space)
        self.assertEqual(self.window.current_page, 'cpu')
        self.window.toggle_sidebar()
        self.assertEqual(target.text(), 'CPU')

    def test_svg_resources_are_bundled_and_render(self):
        self.assertTrue((DIRECTORY / 'LICENSE').is_file())
        for name in set(NAV_ICONS.values()):
            self.assertFalse(icon(name).isNull(), name)
        self.assertFalse(self.window.components['cpu'].badge.icon.pixmap().isNull())


if __name__ == '__main__':
    unittest.main()
