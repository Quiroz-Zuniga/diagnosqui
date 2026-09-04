"""
Backend para sistemas Microsoft Windows usando PowerShell, WMI/CIM y psutil.
"""
import ctypes
import os
import platform
import subprocess
import time
from typing import Any, Dict, List
import psutil

from diagnosqui.backends.base import BaseBackend


class WindowsBackend(BaseBackend):
    """Implementación de telemetría de hardware para Windows."""

    def __init__(self):
        self._powershell_cmd = "powershell"

    def _run_powershell(self, cmd: str, timeout: int = 15) -> str:
        """Ejecuta un comando en PowerShell sin mostrar ventana emergente."""
        try:
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            utf8_cmd = f"$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; {cmd}"
            result = subprocess.run(
                [self._powershell_cmd, "-NoProfile", "-NonInteractive", "-Command", utf8_cmd],
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=creationflags,
                encoding="utf-8",
                errors="replace"
            )
            return result.stdout.strip()
        except Exception:
            return ""

    def is_elevated(self) -> bool:
        """Comprueba si el proceso corre con privilegios de Administrador."""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    def get_system_info(self) -> Dict[str, Any]:
        boot = psutil.boot_time()
        uptime_secs = time.time() - boot
        horas = int(uptime_secs // 3600)
        minutos = int((uptime_secs % 3600) // 60)

        return {
            "os": f"{platform.system()} {platform.release()}",
            "version": platform.version(),
            "platform": platform.platform(),
            "processor": platform.processor(),
            "architecture": platform.machine(),
            "hostname": platform.node(),
            "python": platform.python_version(),
            "uptime": f"{horas}h {minutos}m",
            "uptime_seconds": uptime_secs,
            "is_admin": self.is_elevated(),
        }

    def get_cpu_info(self) -> Dict[str, Any]:
        physical_cores = psutil.cpu_count(logical=False) or 1
        logical_cores = psutil.cpu_count(logical=True) or 1
        freq = psutil.cpu_freq()
        per_cpu = psutil.cpu_percent(interval=1, percpu=True)
        total_use = psutil.cpu_percent(interval=1)

        return {
            "model": platform.processor(),
            "physical_cores": physical_cores,
            "logical_cores": logical_cores,
            "freq_min": freq.min if freq else 0.0,
            "freq_max": freq.max if freq else 0.0,
            "freq_current": freq.current if freq else 0.0,
            "per_cpu": per_cpu,
            "total_percent": total_use,
        }

    def get_memory_info(self) -> Dict[str, Any]:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        return {
            "total_gb": mem.total / (1024 ** 3),
            "available_gb": mem.available / (1024 ** 3),
            "used_gb": mem.used / (1024 ** 3),
            "percent": mem.percent,
            "swap_total_gb": swap.total / (1024 ** 3),
            "swap_used_gb": swap.used / (1024 ** 3),
            "swap_percent": swap.percent,
        }

    def get_disks_info(self) -> Dict[str, Any]:
        partitions = []
        for p in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(p.mountpoint)
                partitions.append({
                    "device": p.device,
                    "mountpoint": p.mountpoint,
                    "fstype": p.fstype,
                    "total_gb": usage.total / (1024 ** 3),
                    "used_gb": usage.used / (1024 ** 3),
                    "free_gb": usage.free / (1024 ** 3),
                    "percent": usage.percent,
                })
            except (PermissionError, Exception):
                partitions.append({
                    "device": p.device,
                    "mountpoint": p.mountpoint,
                    "fstype": p.fstype,
                    "error": "Acceso denegado"
                })

        io_stats = None
        try:
            io = psutil.disk_io_counters()
            if io:
                io_stats = {
                    "read_count": io.read_count,
                    "write_count": io.write_count,
                    "read_mb": io.read_bytes / (1024 ** 2),
                    "write_mb": io.write_bytes / (1024 ** 2),
                }
        except Exception:
            pass

        # Discos físicos usando PowerShell
        cmd_physical = (
            "Get-PhysicalDisk | Select-Object FriendlyName, MediaType, BusType, HealthStatus, Size | "
            "ConvertTo-Csv -NoTypeInformation"
        )
        csv_out = self._run_powershell(cmd_physical)
        physical_disks = []
        if csv_out:
            lines = [l.strip().strip('"') for l in csv_out.splitlines() if l.strip()]
            if len(lines) > 1:
                headers = [h.strip('"') for h in lines[0].split('","')]
                for row in lines[1:]:
                    vals = [v.strip('"') for v in row.split('","')]
                    d = dict(zip(headers, vals))
                    physical_disks.append(d)

        return {
            "partitions": partitions,
            "io_stats": io_stats,
            "physical_disks": physical_disks,
        }

    def get_network_info(self) -> Dict[str, Any]:
        adapters_stats = psutil.net_if_stats()
        adapters_addrs = psutil.net_if_addrs()
        net_io = psutil.net_io_counters()

        interfaces = []
        for name, stats in adapters_stats.items():
            ipv4 = []
            ipv6 = []
            mac = None
            if name in adapters_addrs:
                for addr in adapters_addrs[name]:
                    family_name = getattr(addr.family, "name", str(addr.family))
                    if "AF_INET6" in family_name:
                        ipv6.append(addr.address)
                    elif "AF_INET" in family_name:
                        ipv4.append(addr.address)
                    elif "AF_LINK" in family_name or "AF_PACKET" in family_name:
                        mac = addr.address

            interfaces.append({
                "name": name,
                "is_up": stats.isup,
                "speed_mbps": stats.speed,
                "mtu": stats.mtu,
                "ipv4": ipv4,
                "ipv6": ipv6,
                "mac": mac or "N/D",
            })

        return {
            "interfaces": interfaces,
            "global_io": {
                "sent_mb": net_io.bytes_sent / (1024 ** 2),
                "recv_mb": net_io.bytes_recv / (1024 ** 2),
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "errin": net_io.errin,
                "errout": net_io.errout,
                "dropin": net_io.dropin,
                "dropout": net_io.dropout,
            }
        }

    def get_usb_devices(self) -> Dict[str, Any]:
        cmd_all = (
            "Get-PnpDevice -PresentOnly | Where-Object {$_.InstanceId -like 'USB*'} | "
            "Select-Object FriendlyName, Status, InstanceId, Class | ConvertTo-Csv -NoTypeInformation"
        )
        cmd_prob = (
            "Get-PnpDevice -PresentOnly | Where-Object {$_.InstanceId -like 'USB*' -and $_.Status -ne 'OK'} | "
            "Select-Object FriendlyName, Status, InstanceId, Problem | ConvertTo-Csv -NoTypeInformation"
        )

        devices = self._parse_csv_pnp(self._run_powershell(cmd_all))
        problem_devices = self._parse_csv_pnp(self._run_powershell(cmd_prob))

        return {
            "devices": devices,
            "problem_devices": problem_devices,
            "total_count": len(devices),
            "problem_count": len(problem_devices),
        }

    def get_pci_devices(self) -> Dict[str, Any]:
        cmd_pci = (
            "Get-PnpDevice -PresentOnly | Where-Object {$_.InstanceId -like 'PCI*' -or $_.InstanceId -like 'ACPI*'} | "
            "Select-Object FriendlyName, Status, Class, InstanceId | ConvertTo-Csv -NoTypeInformation"
        )
        cmd_bus = (
            "Get-PnpDevice -PresentOnly -Bus USB | Select-Object FriendlyName, Status, InstanceId | ConvertTo-Csv -NoTypeInformation"
        )

        pci_devs = self._parse_csv_pnp(self._run_powershell(cmd_pci))
        bus_devs = self._parse_csv_pnp(self._run_powershell(cmd_bus))

        return {
            "pci_devices": pci_devs,
            "usb_bus_devices": bus_devs,
        }

    def get_drivers_info(self) -> Dict[str, Any]:
        # driverquery
        try:
            res = subprocess.run(
                ["driverquery", "/FO", "CSV"],
                capture_output=True,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                encoding="utf-8",
                errors="replace"
            )
            raw_csv = res.stdout.strip()
            drivers = self._parse_csv_pnp(raw_csv)
        except Exception:
            drivers = []

        cmd_signed = (
            "Get-WindowsDriver -Online -ErrorAction SilentlyContinue | "
            "Select-Object -First 25 Driver, OriginalFileName, ClassName, ProviderName | "
            "ConvertTo-Csv -NoTypeInformation"
        )
        signed = self._parse_csv_pnp(self._run_powershell(cmd_signed))

        return {
            "drivers": drivers,
            "signed_drivers": signed,
            "total_count": len(drivers),
        }

    def get_problem_devices(self) -> Dict[str, Any]:
        cmd_err = (
            "Get-PnpDevice | Where-Object {$_.Status -eq 'Error'} | "
            "Select-Object FriendlyName, Status, Class, InstanceId | ConvertTo-Csv -NoTypeInformation"
        )
        cmd_deg = (
            "Get-PnpDevice | Where-Object {$_.Status -eq 'Degraded'} | "
            "Select-Object FriendlyName, Status, Class, InstanceId | ConvertTo-Csv -NoTypeInformation"
        )
        cmd_unk = (
            "Get-PnpDevice | Where-Object {$_.Status -eq 'Unknown'} | "
            "Measure-Object | Select-Object -ExpandProperty Count"
        )

        errors = self._parse_csv_pnp(self._run_powershell(cmd_err))
        degraded = self._parse_csv_pnp(self._run_powershell(cmd_deg))
        unk_str = self._run_powershell(cmd_unk)
        unk_count = int(unk_str) if unk_str.isdigit() else 0

        return {
            "errors": errors,
            "degraded": degraded,
            "unknown_count": unk_count,
            "total_problematic": len(errors) + len(degraded) + (1 if unk_count > 0 else 0),
        }

    def get_gpu_info(self) -> Dict[str, Any]:
        cmd_gpu = (
            "Get-CimInstance Win32_VideoController | "
            "Select-Object Name, AdapterRAM, DriverVersion, Status, VideoProcessor | "
            "ConvertTo-Csv -NoTypeInformation"
        )
        gpus = self._parse_csv_pnp(self._run_powershell(cmd_gpu))

        parsed_gpus = []
        gpu_ok = True
        for g in gpus:
            name = g.get("Name", "Adaptador de pantalla")
            ram_str = g.get("AdapterRAM", "0")
            ram_gb = 0.0
            if ram_str and ram_str.isdigit():
                ram_gb = int(ram_str) / (1024 ** 3)
            driver = g.get("DriverVersion", "N/D")
            status = g.get("Status", "OK")
            if status != "OK":
                gpu_ok = False
            parsed_gpus.append({
                "name": name,
                "vram_gb": ram_gb,
                "driver_version": driver,
                "status": status,
                "processor": g.get("VideoProcessor", "N/D")
            })

        return {
            "gpus": parsed_gpus,
            "is_healthy": gpu_ok and len(parsed_gpus) > 0,
        }

    def get_io_delta(self, duration: int = 3) -> Dict[str, Any]:
        d_before = psutil.disk_io_counters()
        n_before = psutil.net_io_counters()
        time.sleep(duration)
        d_after = psutil.disk_io_counters()
        n_after = psutil.net_io_counters()

        disk_delta = {}
        if d_before and d_after:
            disk_delta = {
                "reads": d_after.read_count - d_before.read_count,
                "writes": d_after.write_count - d_before.write_count,
                "read_kb": (d_after.read_bytes - d_before.read_bytes) / 1024,
                "write_kb": (d_after.write_bytes - d_before.write_bytes) / 1024,
            }

        net_delta = {}
        if n_before and n_after:
            net_delta = {
                "sent_kb": (n_after.bytes_sent - n_before.bytes_sent) / 1024,
                "recv_kb": (n_after.bytes_recv - n_before.bytes_recv) / 1024,
                "packets_sent": n_after.packets_sent - n_before.packets_sent,
                "packets_recv": n_after.packets_recv - n_before.packets_recv,
            }

        return {
            "duration": duration,
            "disk": disk_delta,
            "net": net_delta,
        }

    def _parse_csv_pnp(self, csv_data: str) -> List[Dict[str, str]]:
        """Auxiliar para convertir salida CSV de PowerShell en diccionarios."""
        if not csv_data:
            return []
        lines = [l.strip() for l in csv_data.splitlines() if l.strip()]
        if len(lines) < 2:
            return []

        import csv
        import io
        reader = csv.DictReader(io.StringIO(csv_data))
        return [dict(row) for row in reader]
