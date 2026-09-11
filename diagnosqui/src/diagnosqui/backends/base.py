"""
Clase base abstracta que define la interfaz de backends para DiagnosQui.
Todos los métodos de recolección devuelven el CONTRATO UNIFICADO:
{
    "componente": str,
    "evidencia": str,
    "valor_numerico": float,
    "estado": "NORMAL" | "ADVERTENCIA" | "CRITICO",
    "detalle": dict,
    "recomendacion": list[str]
}
"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseBackend(ABC):
    """Interfaz estándar que deben implementar WindowsBackend y LinuxBackend.
    
    Cada método de recolección debe devolver el CONTRATO UNIFICADO.
    Ningún método debe lanzar excepciones: capturar y devolver contrato con estado ADVERTENCIA.
    """

    @abstractmethod
    def is_elevated(self) -> bool:
        """Verifica si el proceso actual tiene permisos de Administrador o root."""
        pass

    @abstractmethod
    def get_system_info(self) -> Dict[str, Any]:
        """Obtiene información del sistema operativo, versión, arquitectura y tiempo encendido.
        
        Returns:
            Dict con claves: os, version, platform, processor, architecture, hostname, python, uptime, uptime_seconds, is_admin
        """
        pass

    @abstractmethod
    def get_cpu_info(self) -> Dict[str, Any]:
        """Obtiene información de CPU y devuelve CONTRATO UNIFICADO.
        
        Returns:
            Contrato con:
            - componente: "CPU"
            - evidencia: "XX% uso"
            - valor_numerico: porcentaje total (float)
            - estado: "NORMAL" | "ADVERTENCIA" | "CRITICO" (según umbrales 70/90)
            - detalle: {"modelo": str, "nucleos_fisicos": int, "nucleos_logicos": int, "frecuencia_actual_mhz": float, "por_nucleo": list[float]}
            - recomendacion: list[str]
        """
        pass

    @abstractmethod
    def get_memory_info(self) -> Dict[str, Any]:
        """Obtiene información de memoria RAM y devuelve CONTRATO UNIFICADO.
        
        Returns:
            Contrato con:
            - componente: "Memoria"
            - evidencia: "XX% (Y.Z/Z.Z GB)"
            - valor_numerico: porcentaje uso RAM (float)
            - estado: "NORMAL" | "ADVERTENCIA" | "CRITICO" (según umbrales 70/90)
            - detalle: {"total_gb": float, "disponible_gb": float, "usada_gb": float, "swap_total_gb": float, "swap_usada_gb": float, "swap_porcentaje": float}
            - recomendacion: list[str]
        """
        pass

    @abstractmethod
    def get_disks_info(self) -> Dict[str, Any]:
        """Obtiene información de almacenamiento y devuelve CONTRATO UNIFICADO.
        
        Returns:
            Contrato con:
            - componente: "Almacenamiento"
            - evidencia: "Unidad X al YY%"
            - valor_numerico: mayor porcentaje de uso entre particiones (float)
            - estado: "NORMAL" | "ADVERTENCIA" | "CRITICO" (según umbrales 70/90)
            - detalle: {"particiones": list[dict], "discos_fisicos": list[dict], "io_stats": dict}
            - recomendacion: list[str]
        """
        pass

    @abstractmethod
    def get_network_info(self) -> Dict[str, Any]:
        """Obtiene información de interfaces de red y devuelve CONTRATO UNIFICADO.
        
        Returns:
            Contrato con:
            - componente: "Red"
            - evidencia: "N interfaces, M activas"
            - valor_numerico: número de interfaces activas (float)
            - estado: "NORMAL" | "ADVERTENCIA" | "CRITICO" (CRITICO si hay APIPA)
            - detalle: {"interfaces": list[dict], "global_io": dict, "apipa_detectada": bool}
            - recomendacion: list[str]
        """
        pass

    @abstractmethod
    def get_connectivity_info(self) -> Dict[str, Any]:
        """Obtiene información de conectividad (ping gateway, ping 8.8.8.8, DNS) y devuelve CONTRATO UNIFICADO.
        
        Returns:
            Contrato con:
            - componente: "Conectividad"
            - evidencia: "Gateway: OK/FAIL, Internet: OK/FAIL, DNS: OK/FAIL"
            - valor_numerico: 0-3 (número de checks exitosos)
            - estado: "NORMAL" | "ADVERTENCIA" | "CRITICO"
            - detalle: {"gateway_ok": bool, "internet_ok": bool, "dns_ok": bool, "gateway_ip": str, "dns_servers": list[str]}
            - recomendacion: list[str]
        """
        pass

    @abstractmethod
    def get_usb_devices(self) -> Dict[str, Any]:
        """Obtiene dispositivos USB y devuelve CONTRATO UNIFICADO.
        
        Returns:
            Contrato con:
            - componente: "USB"
            - evidencia: "N dispositivos, M con problemas"
            - valor_numerico: número de dispositivos con problemas (float)
            - estado: "NORMAL" | "ADVERTENCIA" | "CRITICO" (según regla Windows/Linux)
            - detalle: {"dispositivos": list[dict], "problemas": list[dict]}
            - recomendacion: list[str]
        """
        pass

    @abstractmethod
    def get_pci_devices(self) -> Dict[str, Any]:
        """Obtiene dispositivos PCI/PCIe/ACPI y devuelve CONTRATO UNIFICADO.
        
        Returns:
            Contrato con:
            - componente: "PCI"
            - evidencia: "N dispositivos detectados"
            - valor_numerico: total dispositivos (float)
            - estado: "NORMAL" | "ADVERTENCIA" | "CRITICO"
            - detalle: {"dispositivos": list[dict], "buses_usb": list[dict]}
            - recomendacion: list[str]
        """
        pass

    @abstractmethod
    def get_drivers_info(self) -> Dict[str, Any]:
        """Obtiene controladores del sistema y devuelve CONTRATO UNIFICADO.
        
        Returns:
            Contrato con:
            - componente: "Controladores"
            - evidencia: "N drivers cargados"
            - valor_numerico: total drivers (float)
            - estado: "NORMAL" | "ADVERTENCIA" | "CRITICO"
            - detalle: {"drivers": list[dict], "drivers_firmados": list[dict]}
            - recomendacion: list[str]
        """
        pass

    @abstractmethod
    def get_problem_devices(self) -> Dict[str, Any]:
        """Obtiene dispositivos con problemas y devuelve CONTRATO UNIFICADO.
        
        Returns:
            Contrato con:
            - componente: "Problemas"
            - evidencia: "N dispositivos con errores/desconocidos"
            - valor_numerico: total problemáticos (float)
            - estado: "NORMAL" | "ADVERTENCIA" | "CRITICO"
            - detalle: {"errores": list[dict], "degradados": list[dict], "desconocidos": int, "nota_permisos": str}
            - recomendacion: list[str]
        """
        pass

    @abstractmethod
    def get_gpu_info(self) -> Dict[str, Any]:
        """Obtiene información de GPU y devuelve CONTRATO UNIFICADO.
        
        Returns:
            Contrato con:
            - componente: "GPU"
            - evidencia: "Nombre GPU (Driver: versión, VRAM: X GB)"
            - valor_numerico: 0 si OK, 1 si problema (float)
            - estado: "NORMAL" | "ADVERTENCIA" | "CRITICO"
            - detalle: {"gpus": list[dict], "driver_version": str, "vram_gb": float}
            - recomendacion: list[str]
        """
        pass

    @abstractmethod
    def get_io_delta(self, duration: int = 3) -> Dict[str, Any]:
        """Captura delta de E/S en disco y red en un intervalo.
        
        Returns:
            Dict con: duration, disk: {reads, writes, read_kb, write_kb}, net: {sent_kb, recv_kb, packets_sent, packets_recv}
        """
        pass
