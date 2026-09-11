"""
Seguridad del módulo de optimización: privilegios, confirmaciones y log.

Reglas del diseño (no negociables):
1. Nunca se ejecuta nada automáticamente al iniciar el programa.
2. Requiere Administrador/root; si no lo hay, se avisa y no se intenta.
3. Antes de cambiar nada se muestra qué se hará y se pide ``s/n``.
4. Todo queda registrado en ``logs/optimizacion.log`` (auditable).
5. Los cambios de telemetría son reversibles (cada acción tiene su revertir).
"""
from __future__ import annotations

import os
import platform
import sys
from datetime import datetime
from pathlib import Path

import psutil


def es_administrador() -> bool:
    """Verifica privilegios elevados (Administrador en Windows, root en Linux)."""
    try:
        if sys.platform == "win32":
            import ctypes

            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        return os.geteuid() == 0
    except (AttributeError, ImportError, OSError):
        return False


def estado_del_sistema() -> dict:
    """Devuelve un contrato con la identidad relevante para la optimización."""
    usuario = os.environ.get("USERNAME") or os.environ.get("USER") or "N/D"
    return {
        "plataforma": platform.system(),
        "es_administrador": es_administrador(),
        "usuario": usuario,
        "version_os": platform.release(),
    }


def confirmar(pregunta: str, por_defecto: bool = False) -> bool:
    """Pide confirmación ``s/n``. Nunca se confirma por omisión asumiendo sí."""
    marcador = " (s/n)" + (" [por defecto: n]" if not por_defecto else " [por defecto: s]")
    try:
        respuesta = input(f"{pregunta}{marcador}: ").strip().lower()
    except EOFError:
        return por_defecto
    if respuesta in ("s", "si", "sí", "y", "yes"):
        return True
    if respuesta in ("n", "no", "n"):
        return False
    return por_defecto


def direccion_estado() -> Path:
    """Directorio de estado por usuario (mismo convenio que la terminal)."""
    configurado = os.environ.get("DIAGNOSQUI_STATE_DIR")
    if configurado:
        return Path(configurado).expanduser()
    if platform.system() == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        return base / "DiagnosQui"
    base = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
    return base / "diagnosqui"


def ubicacion_log() -> Path:
    """Ruta del log auditable de optimización (``logs/optimizacion.log``)."""
    return direccion_estado() / "logs" / "optimizacion.log"


def registrar_log(accion: str, detalle: str = "", estado: str = "OK") -> Path:
    """Registra una acción en el log; nunca lanza por fallos de escritura."""
    ruta = ubicacion_log()
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        linea = f"[{datetime.now().astimezone().isoformat(timespec='seconds')}] {estado} | {accion} | {detalle}"
        with ruta.open("a", encoding="utf-8") as stream:
            stream.write(linea + "\n")
    except OSError:
        pass
    return ruta


def procesos_consumidores(limite_cpu: float = 5.0, limite_memoria: float = 5.0, limite: int = 10) -> list:
    """Procesos de mayor consumo; útil para sugerir qué revisar."""
    filas = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            info = proc.info
            if info["cpu_percent"] >= limite_cpu or (info["memory_percent"] or 0) >= limite_memoria:
                filas.append((info["pid"], info["name"], info["cpu_percent"], info["memory_percent"]))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    filas.sort(key=lambda fila: fila[2] + fila[3], reverse=True)
    return filas[:limite]


__all__ = [
    "es_administrador",
    "confirmar",
    "direccion_estado",
    "ubicacion_log",
    "registrar_log",
    "procesos_consumidores",
    "estado_del_sistema",
]