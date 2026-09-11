"""
Diagnóstico general de DiagnosQui: semáforo global y reporte resumido.

Trabaja sobre contratos ya enriquecidos por el motor de recomendaciones
(``analisis.recomendaciones``). También resuelve el caso integrador 5:
cuando todos los indicadores están OK pero el usuario reporta un síntoma,
el resultado final no declara "sistema sin problemas".
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from diagnosqui.analisis.recomendaciones import analizar_conjunto
from diagnosqui.analisis.reglas import ADVERTENCIA, CRITICO, NORMAL, estado_mas_severo

CONTRATO = Dict[str, Any]


def _resumen_por_estado(estado: str) -> str:
    if estado == CRITICO:
        return "Se encontraron problemas críticos en los componentes consultados."
    if estado == ADVERTENCIA:
        return "Se encontraron componentes con niveles de advertencia."
    return "Los componentes consultados están dentro de parámetros normales."


def diagnostico_semaforo(contratos, sintoma: Optional[str] = None) -> Dict[str, Any]:
    """Construye el diagnóstico general con semáforo.

    Args:
        contratos: Lista de contratos unificados (componentes consultados).
        sintoma: Síntoma reportado por el usuario (opcional).

    Returns:
        Diccionario con ``estado``, ``resultados`` (enriquecidos),
        ``errores_detectados``, ``recomendaciones``, ``resultado_final``,
        ``certeza`` y el marcador ``requiere_diagnostico_adicional``.
    """
    resultados = analizar_conjunto(contratos, sintoma=sintoma)
    estados = [str(r.get("estado") or NORMAL) for r in resultados]
    estado = estado_mas_severo(estados)

    errores = [
        {
            "componente": r.get("componente", "N/D"),
            "evidencia": r.get("evidencia", "N/D"),
        }
        for r in resultados
        if r.get("estado") == CRITICO
    ]
    advertencias = [
        r.get("componente", "N/D")
        for r in resultados
        if r.get("estado") == ADVERTENCIA
    ]
    recomendaciones = list(
        dict.fromkeys(
            rec for r in resultados for rec in (r.get("recomendacion") or [])
        )
    )

    certeza = "media"
    requiere_adicional = False
    if sintoma and estado == NORMAL:
        certeza = "baja"
        requiere_adicional = True
        resultado_final = (
            "Sin anomalías en indicadores básicos, pero el usuario reporta un síntoma: "
            "se requiere diagnóstico adicional (temperatura, fuente de poder, "
            "controladores y eventos del sistema)."
        )
    else:
        resultado_final = _resumen_por_estado(estado)
        if sintoma and (errores or advertencias):
            resultado_final += (
                " Existen hallazgos que pueden estar relacionados con el síntoma reportado."
            )

    return {
        "estado": estado,
        "resultados": resultados,
        "errores_detectados": errores,
        "advertencias": advertencias,
        "recomendaciones": recomendaciones,
        "resultado_final": resultado_final,
        "certeza": certeza,
        "requiere_diagnostico_adicional": requiere_adicional,
        "sintoma_reportado": sintoma,
    }


def generar_json_general(
    contratos,
    meta: Optional[Dict[str, Any]] = None,
    sintoma: Optional[str] = None,
) -> Dict[str, Any]:
    """Genera la estructura JSON del reporte general (sección 30 del enunciado).

    ``meta`` puede aportar: ``equipo``, ``usuario`` y ``sistema_operativo``.
    """
    diag = diagnostico_semaforo(contratos, sintoma=sintoma)
    meta = meta or {}
    por_componente: Dict[str, Any] = {}
    for resultado in diag["resultados"]:
        nombre = str(resultado.get("componente") or "N/D")
        clave = nombre.split(" ")[0].upper()
        base = {
            "estado": resultado.get("estado"),
            "evidencia": resultado.get("evidencia"),
        }
        detalle = resultado.get("detalle") or {}
        if "deteccion" in detalle:
            base["deteccion"] = detalle["deteccion"]
        if "certeza" in detalle:
            base["certeza"] = detalle["certeza"]
        base["recomendaciones"] = resultado.get("recomendacion") or []
        por_componente.setdefault(clave, base)

    return {
        "fecha": datetime.now().astimezone().isoformat(timespec="seconds"),
        "equipo": meta.get("equipo", "N/D"),
        "usuario": meta.get("usuario", "N/D"),
        "sistema_operativo": meta.get("sistema_operativo", "N/D"),
        "diagnostico": {**por_componente, "errores_detectados": diag["errores_detectados"]},
        "recomendaciones": diag["recomendaciones"],
        "resultado_final": diag["resultado_final"],
        "certeza": diag["certeza"],
    }