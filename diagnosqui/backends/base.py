"""
Clase base abstracta que define la interfaz de backends para DiagnosQui.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseBackend(ABC):
    """Interfaz estándar que deben implementar WindowsBackend y LinuxBackend."""

    @abstractmethod
    def is_elevated(self) -> bool:
        """Verifica si el proceso actual tiene permisos de Administrador o root."""
        pass

    @abstractmethod
    def get_system_info(self) -> Dict[str, Any]:
        """Obtiene información del sistema operativo, versión, arquitectura y tiempo encendido."""
        pass

    @abstractmethod
    def get_cpu_info(self) -> Dict[str, Any]:
        """Obtiene información de CPU (modelo, núcleos, frecuencias, uso por núcleo y total)."""
        pass

    @abstractmethod
    def get_memory_info(self) -> Dict[str, Any]:
        """Obtiene información de memoria RAM física y Swap."""
        pass

    @abstractmethod
    def get_disks_info(self) -> Dict[str, Any]:
        """Obtiene particiones montadas, estadísticas de E/S y discos físicos del sistema."""
        pass

    @abstractmethod
    def get_network_info(self) -> Dict[str, Any]:
        """Obtiene adaptadores de red, direcciones IP/MAC y estadísticas globales de paquetes."""
        pass

    @abstractmethod
    def get_usb_devices(self) -> Dict[str, Any]:
        """Obtiene lista de dispositivos USB conectados y dispositivos con problemas."""
        pass

    @abstractmethod
    def get_pci_devices(self) -> Dict[str, Any]:
        """Obtiene dispositivos PCI, PCIe, buses ACPI y dispositivos en buses secundarios."""
        pass

    @abstractmethod
    def get_drivers_info(self) -> Dict[str, Any]:
        """Obtiene lista de controladores (drivers) del sistema y controladores firmados/módulos."""
        pass

    @abstractmethod
    def get_problem_devices(self) -> Dict[str, Any]:
        """Obtiene dispositivos con estado de Error, Desconocido o Degradado."""
        pass

    @abstractmethod
    def get_gpu_info(self) -> Dict[str, Any]:
        """Obtiene tarjeta(s) gráfica(s), memoria VRAM, versión de controlador y estado."""
        pass

    @abstractmethod
    def get_io_delta(self, duration: int = 3) -> Dict[str, Any]:
        """Captura el delta de operaciones y bytes transferidos en disco y red en un intervalo."""
        pass
