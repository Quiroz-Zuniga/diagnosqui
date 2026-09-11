"""
Ajustes de telemetría de Windows (mecanismos oficiales y reversibles).

Se automatizan únicamente mecanismos que Microsoft documenta y que tienen
contraparte ``revertir_*``. No se toca el árbol del sistema fuera de las
claves y servicios listados y nada se ejecuta sin confirmación previa.

Fuera de Windows estas funciones son de solo lectura y devuelven
"No disponible".
"""
from __future__ import annotations

import platform
import shutil
import subprocess
from typing import Dict, List, Optional

from diagnosqui.optimizacion.safety import registrar_log

TIMEOUT_SEGUNDOS = 15


def _powershell(comando: str, timeout: int = TIMEOUT_SEGUNDOS) -> str:
    """Ejecuta un comando PowerShell y devuelve stdout recortado."""
    if platform.system() != "Windows" or not shutil.which("powershell"):
        return ""
    try:
        proceso = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", comando],
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        return proceso.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _es_windows() -> bool:
    return platform.system() == "Windows"


def _leer_registro(clave: str, nombre: str) -> Optional[str]:
    comando = (
        f"$v = Get-ItemProperty -Path '{clave}' -Name '{nombre}' -ErrorAction SilentlyContinue; "
        f"if ($v) {{ Write-Output $v.'{nombre}' }}"
    )
    valor = _powershell(comando)
    return valor or None


def _estado_tarea(nombre: str) -> str:
    comando = (
        f"$t = Get-ScheduledTask -TaskName '{nombre}' -ErrorAction SilentlyContinue; "
        f"if ($t -and -not $t.State) {{ 'Habilitada' }} "
        f"elseif ($t) {{ $t.State }} else {{ 'No encontrada' }}"
    )
    return _powershell(comando) or "No encontrada"


def _estado_servicio(servicio: str) -> str:
    comando = (
        f"$s = Get-Service -Name '{servicio}' -ErrorAction SilentlyContinue; "
        f"if ($s) {{ $s.Status }} else {{ 'No existe' }}"
    )
    return _powershell(comando) or "No existe"


CLAVE_TELEMETRIA = r"HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection"
TAREA_COMBATIBILIDAD = r"Microsoft\Windows\Application Experience\Microsoft Compatibility Appraiser"
TAREA_CEIP = r"Microsoft\Windows\Customer Experience Improvement Program\Consolidator"
SERVICIO_DIAGTRACK = "DiagTrack"


def _fila(nombre: str, actual: str, propuesto: str, aplicar: str, revertir: str) -> Dict:
    return {
        "accion": nombre,
        "estado_actual": actual,
        "estado_propuesto": propuesto,
        "aplicar": aplicar,
        "revertir": revertir,
        "aplicable": _es_windows() and bool(actual) and actual not in ("No existe", "No encontrada"),
    }


def consultar_estado() -> List[Dict]:
    """Consulta el estado actual de los mecanismos de telemetría.

    Returns:
        Lista de filas ``{accion, estado_actual, estado_propuesto, aplicar,
        revertir, aplicable}``. En Linux todo queda como "No disponible".
    """
    if not _es_windows():
        return [
            _fila(
                "Telemetría de Windows",
                "No disponible",
                "No aplica fuera de Windows",
                "",
                "",
            )
        ]

    nivel = _leer_registro(CLAVE_TELEMETRIA, "AllowTelemetry")
    actual_nivel = f"{nivel} (registro)" if nivel is not None else "No configurado (1 por defecto en Home)"

    filas = [
        _fila(
            "AllowTelemetry (registro)",
            actual_nivel,
            "0 (Seguridad/Básico)",
            f"Set-ItemProperty -Path '{CLAVE_TELEMETRIA}' -Name 'AllowTelemetry' -Value 0",
            f"Set-ItemProperty -Path '{CLAVE_TELEMETRIA}' -Name 'AllowTelemetry' -Value 1",
        ),
        _fila(
            "Tarea: Compatibility Appraiser",
            _estado_tarea(TAREA_COMBATIBILIDAD),
            "Deshabilitada",
            f"Disable-ScheduledTask -TaskName '{TAREA_COMBATIBILIDAD}'",
            f"Enable-ScheduledTask -TaskName '{TAREA_COMBATIBILIDAD}'",
        ),
        _fila(
            "Tarea: CEIP Consolidator",
            _estado_tarea(TAREA_CEIP),
            "Deshabilitada",
            f"Disable-ScheduledTask -TaskName '{TAREA_CEIP}'",
            f"Enable-ScheduledTask -TaskName '{TAREA_CEIP}'",
        ),
        _fila(
            "Servicio: DiagTrack (telemetría conectada)",
            f"{_estado_servicio(SERVICIO_DIAGTRACK)} / Automático",
            "Detenido / Deshabilitado",
            f"Stop-Service '{SERVICIO_DIAGTRACK}' -Force; "
            f"Set-Service '{SERVICIO_DIAGTRACK}' -StartupType Disabled",
            f"Set-Service '{SERVICIO_DIAGTRACK}' -StartupType Manual; "
            f"Start-Service '{SERVICIO_DIAGTRACK}'",
        ),
    ]
    return filas


def aplicar_telemetria(dry_run: bool = True) -> List[Dict]:
    """Aplica la deshabilitación de los mecanismos; con dry-run solo reporta."""
    resultados = []
    for fila in consultar_estado():
        if not fila["aplicable"]:
            resultados.append({**fila, "resultado": "no aplica"})
            continue
        if dry_run:
            resultados.append({**fila, "resultado": "dry-run (no ejecutado)"})
            continue
        salida = _powershell(fila["aplicar"])
        ok = "error" not in salida.lower()
        mensaje = "ok" if ok else (salida or "sin confirmación")
        registrar_log(
            "telemetria/deshabilitar",
            detalle=f"{fila['accion']} -> {fila['estado_propuesto']}",
            estado="OK" if ok else "ERR",
        )
        resultados.append({**fila, "resultado": mensaje})
    return resultados


def revertir_telemetria(dry_run: bool = True) -> List[Dict]:
    """Revierte la deshabilitación; con dry-run solo reporta."""
    resultados = []
    for fila in consultar_estado():
        if not fila["aplicable"]:
            resultados.append({**fila, "resultado": "no aplica"})
            continue
        if dry_run:
            resultados.append({**fila, "resultado": "dry-run (no ejecutado)"})
            continue
        salida = _powershell(fila["revertir"])
        ok = "error" not in salida.lower()
        registrar_log(
            "telemetria/revertir",
            detalle=f"{fila['accion']} -> valor por defecto",
            estado="OK" if ok else "ERR",
        )
        resultados.append({**fila, "resultado": "ok" if ok else (salida or "sin confirmación")})
    return resultados


__all__ = [
    "consultar_estado",
    "aplicar_telemetria",
    "revertir_telemetria",
]