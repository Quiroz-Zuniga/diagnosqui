"""Normalización defensiva del contrato; no evalúa el hardware."""

from __future__ import annotations
import math
import unicodedata
from collections.abc import Mapping
from typing import Any, Optional, TypedDict


class DiagnosticResult(TypedDict):
    componente: str
    evidencia: str
    valor_numerico: Optional[float]
    estado: str
    detalle: dict[str, Any]
    recomendacion: list[str]


def normalize_result(raw: object, component: str = "N/D") -> DiagnosticResult:
    data = raw if isinstance(raw, Mapping) else {}
    detail = (
        dict(data.get("detalle")) if isinstance(data.get("detalle"), Mapping) else {}
    )
    state = (
        "".join(
            c
            for c in unicodedata.normalize("NFD", str(data.get("estado", "")))
            if not unicodedata.combining(c)
        )
        .upper()
        .strip()
    )
    state = {"OK": "NORMAL", "ALERTA": "ADVERTENCIA", "ERROR": "CRITICO"}.get(
        state, state
    )
    if state not in {"NORMAL", "ADVERTENCIA", "CRITICO"}:
        state = "ADVERTENCIA"
        detail.setdefault("nota", "El proveedor no informó un estado válido.")
    if not data:
        detail.setdefault("error", "El proveedor no devolvió información.")
    recommendations = data.get("recomendacion", [])
    if isinstance(recommendations, str):
        recommendations = [recommendations]
    if not isinstance(recommendations, (list, tuple)):
        recommendations = []
    value = data.get("valor_numerico")
    try:
        number = (
            float(value) if value is not None and not isinstance(value, bool) else None
        )
        if number is not None and not math.isfinite(number):
            number = None
    except (ValueError, TypeError, OverflowError):
        number = None
    if detail.get("error"):
        number = None
        if state == "NORMAL":
            state = "ADVERTENCIA"
    return DiagnosticResult(
        componente=str(data.get("componente") or component),
        evidencia=str(data.get("evidencia") or "N/D"),
        valor_numerico=number,
        estado=state,
        detalle=detail,
        recomendacion=[str(item) for item in recommendations if item],
    )
