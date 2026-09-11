"""
Pruebas unitarias para los módulos base de DiagnosQui.
"""
import os
import unittest
from contextlib import ExitStack
from unittest.mock import patch
from diagnosqui.core.estados import crear_contrato_base, clasificar_porcentaje
from diagnosqui.core.platform_utils import get_backend
from diagnosqui.backends.base import BaseBackend
from diagnosqui.diagnostico.matriz import build_diagnostic_matrix, diagnostico_final
from diagnosqui.core.reporte import generate_csv_report, generate_html_report


class DummyMockBackend(BaseBackend):
    """Backend simulado para verificar diagnósticos deterministas."""

    def __init__(self, cpu_high=False, usb_err=False, gpu_err=False):
        self.cpu_high = cpu_high
        self.usb_err = usb_err
        self.gpu_err = gpu_err

    def is_elevated(self) -> bool:
        return True

    def get_system_info(self):
        return {
            "os": "TestOS 1.0",
            "version": "1.0",
            "platform": "TestPlatform",
            "processor": "Mock Processor x86",
            "architecture": "x86_64",
            "hostname": "TestMachine",
            "python": "3.12",
            "uptime": "5h 12m",
            "uptime_seconds": 18720,
            "is_admin": True,
        }

    def get_cpu_info(self):
        return {
            "model": "Mock CPU",
            "physical_cores": 4,
            "logical_cores": 8,
            "freq_min": 2000.0,
            "freq_max": 4000.0,
            "freq_current": 3200.0,
            "per_cpu": [95.0, 96.0, 94.0, 95.0] if self.cpu_high else [10.0, 12.0, 8.0, 15.0],
            "total_percent": 95.0 if self.cpu_high else 12.0,
        }

    def get_memory_info(self):
        return {
            "total_gb": 16.0,
            "available_gb": 2.0 if self.cpu_high else 12.0,
            "used_gb": 14.0 if self.cpu_high else 4.0,
            "percent": 88.0 if self.cpu_high else 25.0,
            "swap_total_gb": 4.0,
            "swap_used_gb": 2.5 if self.cpu_high else 0.5,
            "swap_percent": 62.5 if self.cpu_high else 12.5,
        }

    def get_disks_info(self):
        return {
            "partitions": [{
                "device": "C:",
                "mountpoint": "C:\\",
                "fstype": "NTFS",
                "total_gb": 512.0,
                "used_gb": 200.0,
                "free_gb": 312.0,
                "percent": 39.0,
            }],
            "io_stats": {"read_count": 100, "write_count": 50, "read_mb": 10.0, "write_mb": 5.0},
            "physical_disks": [{"FriendlyName": "SSD Test", "MediaType": "SSD", "BusType": "NVMe", "HealthStatus": "Healthy", "Size": "512 GB"}],
        }

    def get_network_info(self):
        return {
            "interfaces": [{"name": "Ethernet", "is_up": True, "speed_mbps": 1000, "mtu": 1500, "ipv4": ["192.168.1.50"], "ipv6": [], "mac": "00:11:22:33:44:55"}],
            "global_io": {"sent_mb": 50.0, "recv_mb": 120.0, "packets_sent": 5000, "packets_recv": 8000, "errin": 0, "errout": 0, "dropin": 0, "dropout": 0}
        }

    def get_usb_devices(self):
        if self.usb_err:
            return {
                "devices": [{"FriendlyName": "Mouse", "Status": "OK"}],
                "problem_devices": [{"FriendlyName": "USB Hub", "Status": "Error", "Problem": "Code 43"}],
                "total_count": 2,
                "problem_count": 1,
            }
        return {"devices": [{"FriendlyName": "Mouse", "Status": "OK"}], "problem_devices": [], "total_count": 1, "problem_count": 0}

    def get_pci_devices(self):
        return {"pci_devices": [{"FriendlyName": "PCI Host", "Status": "OK", "Class": "Bridge"}], "usb_bus_devices": []}

    def get_drivers_info(self):
        return {"drivers": [{"Driver": "testdrv"}], "signed_drivers": [], "total_count": 1}

    def get_problem_devices(self):
        return {"errors": [], "degraded": [], "unknown_count": 0, "total_problematic": 0}

    def get_gpu_info(self):
        if self.gpu_err:
            return {
                "gpus": [{"name": "Generic Display Adapter", "vram_gb": 0.0, "driver_version": "1.0", "status": "Degraded", "processor": "N/D"}],
                "is_healthy": False,
            }
        return {
            "gpus": [{"name": "Dedicated GPU 8GB", "vram_gb": 8.0, "driver_version": "535.10", "status": "OK", "processor": "Dedicated GPU"}],
            "is_healthy": True,
        }

    def get_io_delta(self, duration: int = 3):
        return {"duration": duration, "disk": {}, "net": {}}

    def get_connectivity_info(self):
        return crear_contrato_base("Conectividad", "Conectividad de prueba", 3, "NORMAL")


def fixture_matrix(backend):
    """La matriz actual llama recolectores sin argumentos, que reciben contratos."""
    cpu = backend.get_cpu_info()
    memory = backend.get_memory_info()
    disk = backend.get_disks_info()
    usb = backend.get_usb_devices()
    gpu = backend.get_gpu_info()
    problems = backend.get_problem_devices()
    contracts = {
        "cpu": crear_contrato_base("CPU", f"{cpu['total_percent']}%", cpu['total_percent'], clasificar_porcentaje(cpu['total_percent'])),
        "memoria": crear_contrato_base("Memoria", f"{memory['percent']}%", memory['percent'], clasificar_porcentaje(memory['percent'])),
        "discos": crear_contrato_base("Almacenamiento", "39%", 39, "NORMAL", disk),
        "usb": crear_contrato_base("USB", "USB de prueba", usb['problem_count'], "ADVERTENCIA" if usb['problem_count'] else "NORMAL", usb),
        "gpu": crear_contrato_base("GPU", "GPU de prueba", 0 if gpu['is_healthy'] else 1, "NORMAL" if gpu['is_healthy'] else "CRITICO", gpu),
        "problemas": crear_contrato_base("Problemas", "Sin incidencias", 0, "NORMAL", problems),
    }
    with ExitStack() as patches:
        for name, contract in contracts.items():
            patches.enter_context(patch(f"diagnosqui.diagnostico.matriz.recolectar_{name}", return_value=contract))
        return build_diagnostic_matrix()


class TestDiagnosQuiCore(unittest.TestCase):

    def test_backend_detection(self):
        backend = get_backend()
        self.assertIsInstance(backend, BaseBackend)
        sys_info = backend.get_system_info()
        self.assertIn("os", sys_info)
        self.assertIn("processor", sys_info)

    def test_matrix_and_verdict_healthy(self):
        backend = DummyMockBackend(cpu_high=False, usb_err=False, gpu_err=False)
        matrix = fixture_matrix(backend)
        self.assertEqual(len(matrix), 6)

        verdict = diagnostico_final(matrix)
        self.assertTrue(verdict["is_healthy"])

    def test_matrix_and_verdict_reto_scenario(self):
        # Caso reto: CPU alta + USB error + GPU error
        backend = DummyMockBackend(cpu_high=True, usb_err=True, gpu_err=True)
        matrix = fixture_matrix(backend)
        verdict = diagnostico_final(matrix)

        self.assertFalse(verdict["is_healthy"])
        # Verificar que se detectó la combinación del reto
        combined_detected = any("Chipset/GPU" in c for c in verdict["causas"])
        self.assertTrue(combined_detected, "No se detectó el cruce de causas del caso reto.")

    def test_report_exports(self):
        backend = DummyMockBackend()
        sys_info = backend.get_system_info()
        matrix = fixture_matrix(backend)
        verdict = diagnostico_final(matrix)

        test_csv = "test_report.csv"
        test_html = "test_report.html"

        try:
            csv_path = generate_csv_report(matrix, verdict, filename=test_csv)
            self.assertTrue(os.path.exists(csv_path))
            with open(csv_path, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn("Componente,Evidencia,Estado,Posible Problema", content)

            html_path = generate_html_report(matrix, verdict, sys_info, filename=test_html)
            self.assertTrue(os.path.exists(html_path))
            with open(html_path, "r", encoding="utf-8") as f:
                html_content = f.read()
                self.assertIn("DiagnosQui ⚡ Reporte de Hardware", html_content)
                self.assertIn("Matriz de Diagnóstico", html_content)
        finally:
            if os.path.exists(test_csv):
                os.remove(test_csv)
            if os.path.exists(test_html):
                os.remove(test_html)


if __name__ == "__main__":
    unittest.main()
