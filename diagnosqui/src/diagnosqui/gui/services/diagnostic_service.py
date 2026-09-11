"""Adaptadores de los recolectores de core; todas las llamadas se hacen en workers."""

from __future__ import annotations
from datetime import datetime
from threading import Event
from typing import Any, Callable, Optional

from diagnosqui.core import cpu, memoria, discos, red, sistema, usb, pci
from diagnosqui.core import controladores, problemas, monitor, io_monitor, reporte
from diagnosqui.gui.services.contracts import DiagnosticResult, normalize_result

COMPONENTS = {
    "sistema": ("Sistema", "Identidad del equipo, plataforma y tiempo de actividad"),
    "cpu": ("CPU", "Procesador, frecuencia y carga por núcleo"),
    "memoria": ("Memoria", "Uso de memoria física y espacio de intercambio"),
    "disco": (
        "Almacenamiento",
        "Particiones, capacidad y dispositivos de almacenamiento",
    ),
    "red": ("Red", "Interfaces, direcciones y estadísticas de tráfico"),
    "usb": ("USB", "Dispositivos USB y estado de sus conexiones"),
    "pci": ("PCI / PCIe", "Dispositivos y controladores del bus del sistema"),
    "gpu": ("GPU", "Adaptadores gráficos, memoria y controladores disponibles"),
    "controladores": ("Controladores", "Inventario de controladores del sistema"),
    "problemas": (
        "Dispositivos con problemas",
        "Incidencias de hardware y recomendaciones",
    ),
}


class DiagnosticService:
    def __init__(
        self, providers: Optional[dict[str, Callable[[], object]]] = None
    ) -> None:
        self.providers = (
            providers
            if providers is not None
            else {
                "sistema": sistema.recolectar_sistema,
                "cpu": cpu.recolectar_cpu,
                "memoria": memoria.recolectar_memoria,
                "disco": discos.recolectar_discos,
                "red": red.recolectar_red,
                "usb": usb.recolectar_usb,
                "pci": pci.recolectar_pci,
                "gpu": monitor.recolectar_gpu,
                "controladores": controladores.recolectar_controladores,
                "problemas": problemas.recolectar_problemas,
            }
        )

    def collect(self, key: str) -> DiagnosticResult:
        component = COMPONENTS.get(key, (key, ""))[0]
        try:
            raw = self.providers[key]()
            if key == "sistema" and isinstance(raw, dict) and "componente" not in raw:
                raw = dict(
                    componente="Sistema",
                    evidencia=raw.get("os", "N/D"),
                    estado="ADVERTENCIA" if "error" in raw or not raw else "NORMAL",
                    detalle=raw,
                    recomendacion=[],
                )
            result = normalize_result(raw, component)
        except Exception as error:
            result = normalize_result(
                {
                    "estado": "ADVERTENCIA",
                    "evidencia": "No se pudo completar la lectura",
                    "detalle": {"error": str(error)},
                    "recomendacion": [
                        "Reintentar y comprobar los permisos del sistema."
                    ],
                },
                component,
            )
        result["detalle"].setdefault("fuente", "real")
        result["detalle"]["ejecutado_en"] = (
            datetime.now().astimezone().isoformat(timespec="seconds")
        )
        return result

    def collect_all(
        self, cancelled: Optional[Event] = None
    ) -> dict[str, DiagnosticResult]:
        results = {}
        for key in COMPONENTS:
            if cancelled is not None and cancelled.is_set():
                break
            results[key] = self.collect(key)
        return results

    def collect_io(self) -> dict[str, Any]:
        """Lectura puntual de E/S disponible para la página de monitor."""
        return io_monitor.recolectar_io_delta(1)

    def export(
        self,
        results: dict[str, DiagnosticResult],
        directory: str,
        formats: tuple[str, ...],
    ) -> dict[str, str]:
        return reporte.export_diagnostic_results(
            list(results.values()), directory, formats
        )
