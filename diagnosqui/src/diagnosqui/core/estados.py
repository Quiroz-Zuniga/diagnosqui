"""
Utilidades compartidas para clasificación de estados y umbrales.
Contrato de datos unificado para toda la capa de recolección.
"""
from typing import Any, Dict, List


def clasificar_porcentaje(valor: float) -> str:
    """Clasifica un porcentaje según umbrales estándar.
    
    Args:
        valor: Porcentaje (0-100)
        
    Returns:
        "NORMAL" | "ADVERTENCIA" | "CRITICO"
    """
    if valor >= 90:
        return "CRITICO"
    if valor >= 70:
        return "ADVERTENCIA"
    return "NORMAL"


def clasificar_estado_windows(status: str) -> str:
    """Clasifica estado de dispositivo Windows según regla del proyecto.
    
    Args:
        status: Valor de Status de Get-PnpDevice (OK, Warning, Unknown, Error, Degraded, etc.)
        
    Returns:
        "NORMAL" | "ADVERTENCIA" | "CRITICO"
    """
    if not status:
        return "ADVERTENCIA"
    s = status.strip().lower()
    if s == "ok":
        return "NORMAL"
    if s in ("warning", "unknown"):
        return "ADVERTENCIA"
    return "CRITICO"


def detectar_apipa(ipv4_list: List[str]) -> bool:
    """Detecta si alguna IPv4 es APIPA (169.254.x.x)."""
    for ip in ipv4_list:
        if ip.startswith("169.254."):
            return True
    return False


def crear_contrato_base(
    componente: str,
    evidencia: str,
    valor_numerico: float,
    estado: str,
    detalle: Dict[str, Any] = None,
    recomendacion: List[str] = None
) -> Dict[str, Any]:
    """Crea el diccionario base del contrato de datos unificado."""
    return {
        "componente": componente,
        "evidencia": evidencia,
        "valor_numerico": valor_numerico,
        "estado": estado,
        "detalle": detalle or {},
        "recomendacion": recomendacion or []
    }


def contrato_error(componente: str, error: Exception, contexto: str = "") -> Dict[str, Any]:
    """Genera contrato de error estándar (ADVERTENCIA + detalle)."""
    msg = f"{type(error).__name__}: {error}"
    if contexto:
        msg = f"{contexto} - {msg}"
    return crear_contrato_base(
        componente=componente,
        evidencia="Error en recolección",
        valor_numerico=0,
        estado="ADVERTENCIA",
        detalle={"error": msg},
        recomendacion=["Verificar permisos y dependencias del sistema"]
    )