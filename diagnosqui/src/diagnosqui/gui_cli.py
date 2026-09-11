"""Entrada gráfica independiente; la terminal mantiene diagnosqui.cli:main."""

from __future__ import annotations
import argparse
import os
import subprocess
import sys
from typing import Optional, Sequence


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="DiagnosQui · Aplicación de escritorio"
    )
    parser.add_argument(
        "--detach",
        action="store_true",
        help="Abrir en un proceso independiente de esta terminal",
    )
    args = parser.parse_args(argv)
    if sys.platform.startswith("linux") and not any(
        os.environ.get(key) for key in ("DISPLAY", "WAYLAND_DISPLAY", "QT_QPA_PLATFORM")
    ):
        if sys.stderr is not None:
            print(
                "DiagnosQui necesita un entorno gráfico. Para pruebas usa QT_QPA_PLATFORM=offscreen.",
                file=sys.stderr,
            )
        return 1
    if args.detach:
        command = [sys.executable, "-m", "diagnosqui.gui_cli"]
        options = (
            {
                "creationflags": getattr(subprocess, "DETACHED_PROCESS", 0)
                | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            }
            if sys.platform == "win32"
            else {"start_new_session": True}
        )
        try:
            subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                **options,
            )
            return 0
        except OSError as error:
            if sys.stderr is not None:
                print(f"No se pudo iniciar DiagnosQui: {error}", file=sys.stderr)
            return 1
    try:
        from PySide6.QtWidgets import QApplication
        from diagnosqui.gui.app import create_application
        from diagnosqui.gui.main_window import MainWindow

        owned = QApplication.instance() is None
        app = create_application()
        window = MainWindow()
        # Mantener referencias si un anfitrión ya tiene su propio bucle Qt.
        app.diagnosqui_window = window
        window.show()
        return app.exec() if owned else 0
    except Exception as error:
        if sys.stderr is not None:
            print(f"No se pudo iniciar DiagnosQui: {error}", file=sys.stderr)
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox

            if QApplication.instance() is not None:
                QMessageBox.critical(None, "No se pudo iniciar DiagnosQui", str(error))
        except ImportError:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
