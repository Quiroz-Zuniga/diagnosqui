"""Creación de QApplication y carga de recursos empaquetados."""

from __future__ import annotations
from typing import Optional
from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
from PySide6.QtWidgets import QApplication
from diagnosqui import __version__
from diagnosqui.gui.theme_manager import ThemeManager


def create_application(argv: Optional[list[str]] = None) -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication(argv or [])
    app.setApplicationName("DiagnosQui")
    app.setApplicationDisplayName("DiagnosQui")
    app.setOrganizationName("DiagnosQui")
    app.setApplicationVersion(__version__)
    QLocale.setDefault(QLocale(QLocale.Language.Spanish))
    if not hasattr(app, "diagnosqui_translator"):
        translator = QTranslator(app)
        translations = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        if translator.load("qtbase_es", translations):
            app.installTranslator(translator)
        app.diagnosqui_translator = translator
    if not hasattr(app, "theme_manager"):
        app.setStyle("Fusion")
        app.theme_manager = ThemeManager(app)
        app.theme_manager.apply("light")
    return app
