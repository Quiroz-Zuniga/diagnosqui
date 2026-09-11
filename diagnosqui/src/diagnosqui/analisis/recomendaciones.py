"""
Motor de recomendaciones de DiagnosQui.

Una función por dominio siguiendo el patrón del enunciado
DETECCIÓN → DIAGNÓSTICO → SOLUCIÓN. Ninguna función consulta hardware:
trabaja sobre contratos unificados ya recolectados (o fixtures de prueba).

Reglas de certeza (caso integrador 5):
    - Si los indicadores dicen OK pero el usuario reporta un síntoma,
      el resultado no declara "sistema sin problemas": baja ``certeza`` y
      pide diagnóstico adicional.
    - Un estado de error reportado por el propio PnP tiene ``certeza`` alta.
    - Una inferencia por porcentaje/umbrales tiene ``certeza`` media.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from diagnosqui.analisis.reglas import (
    ADVERTENCIA,
    CRITICO,
    NORMAL,
    analizar_estado,
    clasificar_pnp,
    estado_mas_severo,
)

TIPO_ANALISIS = Dict[str, Any]


def _porcentaje(contrato) -> float:
    """Porcentaje del contrato: ``valor_numerico`` o el del detalle."""
    valor = contrato.get("valor_numerico")
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return float(valor)
    return 0.0


def _diagnostico(estado: str) -> str:
    if estado == CRITICO:
        return "Se detectaron indicadores críticos; no se descarta falla de hardware."
    if estado == ADVERTENCIA:
        return "Los indicadores están por encima de los niveles recomendados."
    return "Sin anomalías en indicadores básicos."


def _recomendaciones_base(dominio: str, estado: str) -> List[str]:
    if estado == NORMAL:
        return ["No se requieren acciones inmediatas."]
    if estado == ADVERTENCIA:
        return [
            f"Revisar el componente de {dominio} y sus controladores.",
            "Monitorear el indicador de forma periódica.",
        ]
    return [
        f"Verificar físicamente el componente de {dominio}.",
        "Actualizar controladores desde la página oficial del fabricante.",
        "Si el indicador persiste, solicitar diagnóstico especializado.",
    ]


# --------------------------------------------------------------------------
# Análisis por dominio. Cada función retorna:
# {estado, deteccion, diagnostico, certeza, recomendacion}
# --------------------------------------------------------------------------

def recomendacion_cpu(contrato) -> TIPO_ANALISIS:
    uso = _porcentaje(contrato)
    estado = analizar_estado(uso)
    return {
        "estado": estado,
        "deteccion": f"Uso de CPU al {uso:.0f}%",
        "diagnostico": _diagnostico(estado),
        "certeza": "media",
        "recomendacion": _recomendaciones_base("procesador", estado)
        + (["Identificar los procesos de mayor consumo (administrador de tareas o top)."] if uso >= 70 else []),
    }


def recomendacion_memoria(contrato) -> TIPO_ANALISIS:
    uso = _porcentaje(contrato)
    estado = analizar_estado(uso)
    return {
        "estado": estado,
        "deteccion": f"Uso de memoria RAM al {uso:.0f}%",
        "diagnostico": _diagnostico(estado),
        "certeza": "media",
        "recomendacion": _recomendaciones_base("memoria RAM", estado)
        + (["Cerrar aplicaciones con consumo alto de memoria o ampliar la RAM."] if uso >= 90 else []),
    }


def recomendacion_disco(contrato) -> TIPO_ANALISIS:
    detalle = contrato.get("detalle") or {}
    particiones = detalle.get("particiones") or []
    maximo = max((float(p.get("percent") or 0) for p in particiones), default=0.0)
    ocupada = max(_porcentaje(contrato), maximo)
    estado = analizar_estado(ocupada)
    return {
        "estado": estado,
        "deteccion": f"Almacenamiento al {ocupada:.0f}% en la partición más ocupada",
        "diagnostico": _diagnostico(estado),
        "certeza": "media",
        "recomendacion": _recomendaciones_base("almacenamiento", estado)
        + (["Liberar espacio después de respaldar los archivos."] if ocupada >= 90 else []),
    }


def recomendacion_usb(contrato) -> TIPO_ANALISIS:
    detalle = contrato.get("detalle") or {}
    problemas = detalle.get("problemas") or detalle.get("problem_devices") or []
    estado = CRITICO if problemas else NORMAL
    return {
        "estado": estado,
        "deteccion": f"{len(problemas)} dispositivo(s) USB con error" if problemas else "Dispositivos USB reconocidos",
        "diagnostico": (
            "El bus USB reporta dispositivos con estado de error (posible controlador, puerto o cable)."
            if problemas else "Sin anomalías en indicadores básicos."
        ),
        "certeza": "alta" if problemas else "media",
        "recomendacion": _recomendaciones_base("bus USB", estado)
        + (["Probar el dispositivo en otro puerto y con otro cable."] if problemas else []),
    }


def recomendacion_pci(contrato) -> TIPO_ANALISIS:
    detalle = contrato.get("detalle") or {}
    dispositivos = detalle.get("dispositivos") or []
    con_error = [
        dev for dev in dispositivos
        if clasificar_pnp(str(dev.get("status") or dev.get("Status") or "")) != NORMAL
    ]
    estado = CRITICO if con_error else NORMAL
    return {
        "estado": estado,
        "deteccion": f"{len(dispositivos)} dispositivo(s) PCI/PCIe, {len(con_error)} con estado anómalo",
        "diagnostico": (
            "Se aisló la falla a un dispositivo puntual del bus PCI/PCIe, no al sistema en general."
            if con_error else "Sin anomalías en indicadores básicos."
        ),
        "certeza": "alta" if con_error else "media",
        "recomendacion": _recomendaciones_base("bus PCI", estado)
        + (["Reinstalar físicamente la tarjeta afectada y actualizar su controlador."] if con_error else []),
    }


def recomendacion_red(contrato) -> TIPO_ANALISIS:
    detalle = contrato.get("detalle") or {}
    apipa = bool(detalle.get("apipa_detectada"))
    estado = CRITICO if apipa else NORMAL
    return {
        "estado": estado,
        "deteccion": "Dirección APIPA (169.254.x.x) detectada" if apipa else "Interfaces de red operativas",
        "diagnostico": (
            "IP en rango APIPA: posible fallo de asignación DHCP. "
            "Se sugiere renovar la concesión (ipconfig /release y /renew)."
            if apipa else "Sin anomalías en indicadores básicos."
        ),
        "certeza": "alta" if apipa else "media",
        "recomendacion": _recomendaciones_base("red", estado)
        + (["Renovar la dirección IP con ipconfig /release y /renew."] if apipa else []),
    }


def recomendacion_conectividad(contrato) -> TIPO_ANALISIS:
    detalle = contrato.get("detalle") or {}
    gw = bool(detalle.get("gateway_ok", False))
    inet = bool(detalle.get("internet_ok", False))
    dns = bool(detalle.get("dns_ok", False))
    fallidas = [nombre for nombre, ok in
                (("Gateway", gw), ("Internet", inet), ("DNS", dns)) if not ok]
    estado = CRITICO if fallidas else NORMAL
    return {
        "estado": estado,
        "deteccion": f"{3 - len(fallidas)}/3 comprobaciones de conectividad exitosas",
        "diagnostico": (
            f"Fallo de conectividad en: {', '.join(fallidas)}."
            if fallidas else "Conectividad operativa."
        ),
        "certeza": "alta" if fallidas else "media",
        "recomendacion": _recomendaciones_base("conectividad", estado)
        + ([f"Verificar la configuración de {fallida}." for fallida in fallidas]),
    }


def recomendacion_gpu(contrato) -> TIPO_ANALISIS:
    detalle = contrato.get("detalle") or {}
    gpus = detalle.get("gpus") or []
    estados = [clasificar_pnp(str(g.get("status") or g.get("Status") or "OK")) for g in gpus]
    estado = estado_mas_severo(estados) if estados else NORMAL
    return {
        "estado": estado,
        "deteccion": f"{len(gpus)} adaptador(es) de vídeo",
        "diagnostico": _diagnostico(estado),
        "certeza": "alta" if estado == CRITICO else "media",
        "recomendacion": _recomendaciones_base("GPU", estado)
        + (["Descargar el controlador WHQL más reciente del fabricante (NVIDIA, AMD o Intel)."] if estado == CRITICO else []),
    }


def recomendacion_controladores(contrato) -> TIPO_ANALISIS:
    detalle = contrato.get("detalle") or {}
    drivers = detalle.get("drivers") or []
    con_error = [
        dev for dev in drivers
        if clasificar_pnp(str(dev.get("status") or dev.get("Status") or "OK")) != NORMAL
    ]
    estado = CRITICO if con_error else NORMAL
    return {
        "estado": estado,
        "deteccion": f"{len(drivers)} controladores inventariados, {len(con_error)} con estado anómalo",
        "diagnostico": _diagnostico(estado),
        "certeza": "alta" if con_error else "media",
        "recomendacion": _recomendaciones_base("controladores", estado)
        + (["Consultar el controlador afectado en la web del fabricante."] if con_error else []),
    }


def recomendacion_problemas(contrato) -> TIPO_ANALISIS:
    detalle = contrato.get("detalle") or {}
    errores = detalle.get("errores") or []
    degradados = detalle.get("degradados") or []
    total = len(errores) + len(degradados)
    estado = CRITICO if errores else (ADVERTENCIA if degradados else NORMAL)
    return {
        "estado": estado,
        "deteccion": f"{total} dispositivo(s) con incidencias",
        "diagnostico": _diagnostico(estado),
        "certeza": "alta" if errores or degradados else "media",
        "recomendacion": _recomendaciones_base("dispositivos", estado)
        + (["Revisar el Administrador de dispositivos para reinstalar controladores faltantes."] if total else []),
    }


# Orden de coincidencia: los dominios más específicos primero.
_ANALIZADORES = [
    (("CONECTIV",), recomendacion_conectividad),
    (("CPU",), recomendacion_cpu),
    (("MEMORIA", "RAM"), recomendacion_memoria),
    (("DISC", "DISCO", "SSD", "HDD", "ALMACENAMI"), recomendacion_disco),
    (("GPU", "GRÁFICO", "GRAFICO", "VIDEO", "PANTALLA"), recomendacion_gpu),
    (("CONTROLADOR", "DRIVER"), recomendacion_controladores),
    (("PROBLEMA", "INCIDE", "PNP"), recomendacion_problemas),
    (("USB",), recomendacion_usb),
    (("PCI",), recomendacion_pci),
    (("RED",), recomendacion_red),
]


def _analizador_para(componente: str):
    nombre = (componente or "").upper()
    for claves, funcion in _ANALIZADORES:
        if any(clave in nombre for clave in claves):
            return funcion
    return None


def analizar_contrato(contrato, sintoma: Optional[str] = None) -> Dict[str, Any]:
    """Aplica el motor a un contrato y devuelve un contrato enriquecido.

    Conserva las seis claves del contrato y agrega en ``detalle``:
    ``deteccion``, ``diagnostico`` y ``certeza``; reemplaza ``estado`` y
    ``recomendacion`` con el resultado del motor. Si el usuario reporta un
    síntoma y los indicadores están OK, baja ``certeza`` y pide diagnóstico
    adicional (regla del caso integrador 5).
    """
    resultado = dict(contrato or {})
    detalle = dict(resultado.get("detalle") or {})
    componente = str(resultado.get("componente", ""))

    analizador = _analizador_para(componente)
    if analizador is not None:
        analisis = analizador(resultado)
        detalle["deteccion"] = analisis["deteccion"]
        detalle["diagnostico"] = analisis["diagnostico"]
        detalle["certeza"] = analisis["certeza"]
        resultado["estado"] = analisis["estado"]
        resultado["recomendacion"] = list(analisis["recomendacion"])
    else:
        detalle.setdefault("diagnostico", _diagnostico(resultado.get("estado") or NORMAL))

    estado = resultado.get("estado") or NORMAL
    if sintoma and estado == NORMAL:
        detalle["certeza"] = "baja"
        detalle["diagnostico"] = (
            "Sin anomalías en indicadores básicos; se requiere diagnóstico adicional "
            "(temperatura, fuente de poder, controladores, eventos del sistema)."
        )
        recomendacion = list(resultado.get("recomendacion") or [])
        for extra in (
            ("El reporte del usuario señala un síntoma pese a indicadores OK: "
             "verificar temperatura y ventilación."),
            "Revisar la fuente de poder y el estado de los controladores relacionados.",
            "Consultar los eventos del sistema del período reportado.",
        ):
            if extra not in recomendacion:
                recomendacion.append(extra)
        resultado["recomendacion"] = recomendacion

    detalle.setdefault("fuente", "motor")
    resultado["detalle"] = detalle
    return resultado


def analizar_conjunto(contratos, sintoma: Optional[str] = None) -> List[Dict[str, Any]]:
    """Aplica el motor a una secuencia de contratos preservando el orden."""
    return [analizar_contrato(contrato, sintoma=sintoma) for contrato in contratos]