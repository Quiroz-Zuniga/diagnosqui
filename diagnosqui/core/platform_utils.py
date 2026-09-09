"""
Utilidades de detección de plataforma y selección de backend para DiagnosQui.
"""
import sys
from typing import Any, Dict, Optional
from rich.panel import Panel
from rich.text import Text

from diagnosqui.backends.base import BaseBackend
from diagnosqui.backends.windows_backend import WindowsBackend
from diagnosqui.backends.linux_backend import LinuxBackend
from diagnosqui.ui.theme import console

_BACKEND_INSTANCE: Optional[BaseBackend] = None


def get_backend() -> BaseBackend:
    """Retorna la instancia del backend correspondiente al sistema operativo."""
    global _BACKEND_INSTANCE
    if _BACKEND_INSTANCE is not None:
        return _BACKEND_INSTANCE

    if sys.platform == "win32":
        _BACKEND_INSTANCE = WindowsBackend()
    else:
        _BACKEND_INSTANCE = LinuxBackend()

    return _BACKEND_INSTANCE


def get_connectivity_info() -> Dict[str, Any]:
    """Obtiene información de conectividad del backend actual."""
    backend = get_backend()
    return backend.get_connectivity_info()


def check_elevation_warning() -> None:
    """Imprime una advertencia si la aplicación no se está ejecutando con privilegios elevados."""
    backend = get_backend()
    if not backend.is_elevated():
        msg = Text()
        msg.append("⚠  AVISO DE PRIVILEGIOS: ", style="warning")
        if sys.platform == "win32":
            msg.append(
                "La aplicación no se está ejecutando como Administrador. "
                "Ciertas consultas de controladores, eventos PnP y discos físicos pueden omitirse o requerir elevación.",
                style="muted"
            )
        else:
            msg.append(
                "La aplicación no se está ejecutando con sudo/root. "
                "Ciertas lecturas de dmesg o lspci detallado podrían estar restringidas.",
                style="muted"
            )
        console.print(Panel(msg, border_style="yellow", expand=False))
