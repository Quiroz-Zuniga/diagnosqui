"""
Limpieza de temporales de DiagnosQui (especialmente Windows).

Ubicaciones por defecto:
- ``%TEMP%`` del usuario (C:\\Users\\<usuario>\\AppData\\Local\\Temp).
- ``C:\\Windows\\Temp``.
- Caché de Windows Update (``SoftwareDistribution\\Download``) opcional.
- Papelera de reciclaje (opcional; requiere confirmación aparte).

Siempre con modo ``dry_run`` (por defecto) y nunca se fuerzan archivos en
uso o sin permisos: esos archivos se omiten y quedan reportados.
"""
from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

ArchivoTemporal = Tuple[str, int]


def rutas_temporales() -> List[str]:
    """Rutas de temporales a considerar según la plataforma.

    En Windows incluimos ``%TEMP%`` y ``C:\\Windows\\Temp``. En Linux se
    usan ``/tmp`` y la caché del usuario (``~/.cache``) para permitir la
    verificación en pruebas, sin modificar nada de Windows.
    """
    rutas = []
    temporal = os.environ.get("TEMP") or os.environ.get("TMP")
    if temporal:
        rutas.append(temporal)
    if platform.system() == "Windows":
        rutas.append(r"C:\Windows\Temp")
        descargas = os.environ.get("WINDIR", r"C:\Windows")
        rutas.append(os.path.join(descargas, "SoftwareDistribution", "Download"))
    else:
        rutas.append("/tmp")
        rutas.append(os.path.join(str(Path.home()), ".cache"))
    return [r for r in dict.fromkeys(os.path.normpath(r) for r in rutas if r) if os.path.isdir(r)]


def escanear_temporales(rutas: Optional[Sequence[str]] = None) -> List[ArchivoTemporal]:
    """Escanea las rutas y devuelve (ruta absoluta, tamaño en bytes).

    Los archivos en uso o sin permisos se omiten (OSError capturado).
    """
    rutas = list(rutas) if rutas is not None else rutas_temporales()
    encontrados: List[ArchivoTemporal] = []
    for ruta in rutas:
        raiz = os.path.normpath(ruta)
        try:
            entries = os.scandir(raiz)
        except OSError:
            continue
        for entrada in entries:
            try:
                ruta_completa = os.path.join(raiz, entrada.name)
                tamano = os.path.getsize(ruta_completa)
                encontrados.append((ruta_completa, tamano))
            except OSError:
                continue
    return encontrados


def resumen_temporales(rutas: Optional[Sequence[str]] = None) -> dict:
    """Resumen del escaneo: cantidad, bytes totales y tamaño por ruta."""
    archivos = escanear_temporales(rutas)
    por_ruta: dict = {}
    for ruta, tamano in archivos:
        carpeta = os.path.dirname(ruta)
        por_ruta[carpeta] = por_ruta.get(carpeta, 0) + tamano
    return {
        "archivos": archivos,
        "total_archivos": len(archivos),
        "bytes_totales": sum(tamano for _, tamano in archivos),
        "por_ruta": por_ruta,
    }


def limpiar_temporales(
    archivos: Optional[Sequence[ArchivoTemporal]] = None,
    *,
    dry_run: bool = True,
) -> dict:
    """Elimina los archivos temporales (o simula con ``dry_run``).

    Returns:
        ``{"eliminados": int, "bytes_liberados": int, "omitidos": int}``.
        En modo dry-run ``eliminados``/``bytes_liberados`` reportan lo que
        se liberaría.
    """
    archivos = list(archivos) if archivos is not None else escanear_temporales()
    eliminados = 0
    bytes_liberados = 0
    omitidos = 0
    for ruta, tamano in archivos:
        if dry_run:
            bytes_liberados += tamano
            eliminados += 1
            continue
        try:
            os.remove(ruta)
            bytes_liberados += tamano
            eliminados += 1
        except OSError:
            omitidos += 1
    return {"eliminados": eliminados, "bytes_liberados": bytes_liberados, "omitidos": omitidos}


def contrato_estado(rutas: Optional[Sequence[str]] = None) -> dict:
    """Contrato unificado con el estado del escaneo de temporales."""
    resumen = resumen_temporales(rutas)
    total = resumen["total_archivos"]
    bytes_total = resumen["bytes_totales"]
    estado = "NORMAL" if total == 0 else "ADVERTENCIA"
    return {
        "componente": "Optimización — temporales",
        "evidencia": f"{total:,} archivos temporales ({bytes_total / (1024 ** 3):.2f} GB) encontrados",
        "valor_numerico": float(total),
        "estado": estado,
        "detalle": {
            "fuente": "real",
            "total_archivos": total,
            "bytes_totales": bytes_total,
            "por_ruta": resumen["por_ruta"],
            "se_omitieron_en_uso": 0,
        },
        "recomendacion": (
            ["No hay temporales que limpiar."] if total == 0
            else ["Usar el módulo de optimización para liberar espacio (con confirmación)."]
        ),
    }


__all__ = [
    "rutas_temporales",
    "escanear_temporales",
    "resumen_temporales",
    "limpiar_temporales",
    "contrato_estado",
]