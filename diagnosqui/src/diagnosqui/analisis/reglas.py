"""
Motor de reglas de DiagnosQui: clasificación de estados y umbrales.

Módulo autocontenido (sin dependencias de ``core`` ni de la capa de
recolección) para que pueda usarse desde la terminal, los reportes y las
pruebas sin arrastrar hardware. Centraliza los umbrales del enunciado:
CPU/RAM 0-70/71-89/90-100 y la regla de estados PnP (OK/Warning/Error).

Estados posibles del contrato unificado: ``NORMAL``, ``ADVERTENCIA``,
``CRITICO``.
"""
from __future__ import annotations

from typing import Union

UMBRAL_ADVERTENCIA = 70.0
UMBRAL_CRITICO = 90.0

NORMAL = "NORMAL"
ADVERTENCIA = "ADVERTENCIA"
CRITICO = "CRITICO"

ESTADOS_VALIDOS = frozenset({NORMAL, ADVERTENCIA, CRITICO})

# Regla PnP de Windows: los estados del Administrador de dispositivos
# mapean a la misma escala de severidad del resto del programa.
ESTADOS_OK = frozenset({"ok", "normal", "activo", "passed"})
ESTADOS_ADVERTENCIA = frozenset({"warning", "warn", "unknown", "degraded", "alerta"})
ESTADOS_CRITICO = frozenset({"error", "critical", "critico", "falla", "failed"})


def analizar_estado(valor: Union[float, int], tipo: str = "porcentaje") -> str:
    """Clasifica un valor según el tipo de regla.

    Args:
        valor: Valor a clasificar.
        tipo:
            - ``porcentaje``: umbrales 70 (advertencia) / 90 (crítico).
            - ``conteo``: crítico si es mayor que 0 (incidencias).

    Returns:
        ``NORMAL``, ``ADVERTENCIA`` o ``CRITICO``.
    """
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return ADVERTENCIA
    if tipo == "porcentaje":
        if numero >= UMBRAL_CRITICO:
            return CRITICO
        if numero >= UMBRAL_ADVERTENCIA:
            return ADVERTENCIA
        return NORMAL
    if tipo == "conteo":
        return CRITICO if numero > 0 else NORMAL
    return ADVERTENCIA


def clasificar_pnp(status: str) -> str:
    """Clasifica el estado de un dispositivo PnP según la regla del enunciado.

    ``OK`` es normal; ``Warning``/``Unknown`` son advertencia; cualquier
    otro valor (``Error``, ``Degraded``, vacío) se trata como crítico a
    menos que sea explícitamente un estado degradado con menos severidad.
    """
    if not status:
        return ADVERTENCIA
    normalizado = status.strip().lower()
    if normalizado in ESTADOS_OK:
        return NORMAL
    if normalizado in ESTADOS_ADVERTENCIA or normalizado == "degraded":
        return ADVERTENCIA
    if normalizado in ESTADOS_CRITICO:
        return CRITICO
    return CRITICO


def estado_mas_severo(estados) -> str:
    """Devuelve el estado más severo de una secuencia de estados."""
    prioridad = {NORMAL: 0, ADVERTENCIA: 1, CRITICO: 2}
    mejor = NORMAL
    for estado in estados:
        if estado not in prioridad:
            continue
        if prioridad[estado] > prioridad[mejor]:
            mejor = estado
    return mejor


def estado_valido(estado: str) -> bool:
    """Verifica que un estado pertenezca a la escala del contrato."""
    return estado in ESTADOS_VALIDOS


def traducir_estado(estado: str) -> str:
    """Normaliza alias (OK, ALERTA, ERROR…) a la escala del contrato."""
    if not estado:
        return ADVERTENCIA
    normalizado = estado.strip().lower()
    if normalizado in ESTADOS_OK:
        return NORMAL
    if normalizado in ESTADOS_ADVERTENCIA:
        return ADVERTENCIA
    if normalizado in ESTADOS_CRITICO:
        return CRITICO
    return ADVERTENCIA