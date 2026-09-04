"""
Backend para sistemas Linux usando /proc, /sys, lspci, lsusb, lsmod y psutil.
"""
import os
import platform
import subprocess
import time
from typing import Any, Dict, List
import psutil

from diagnosqui.backends.base import BaseBackend


class LinuxBackend(BaseBackend):
    """Implementación de telemetría de hardware para sistemas Linux."""

    def _run_cmd(self, cmd_list: List[str], timeout: int = 10) -> str:
        """Ejecuta un comando de Linux de forma segura."""
        try:
            res = subprocess.run(
                cmd_list,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace"
            )
            return res.stdout.strip()
        except (FileNotFoundError, PermissionError, subprocess.SubprocessError):
            return ""

    def is_elevated(self) -> bool:
        """Comprueba si el proceso corre como root (UID 0)."""
        try:
            return os.geteuid() == 0
        except AttributeError:
            return False

    def get_system_info(self) -> Dict[str, Any]:
        boot = psutil.boot_time()
        uptime_secs = time.time() - boot
        horas = int(uptime_secs // 3600)
        minutos = int((uptime_secs % 3600) // 60)

        distro = "Linux"
        if os.path.exists("/etc/os-release"):
            try:
                with open("/etc/os-release", "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            distro = line.split("=", 1)[1].strip().strip('"')
                            break
            except Exception:
                pass

        return {
            "os": distro,
            "version": platform.release(),
            "platform": platform.platform(),
            "processor": platform.processor() or "x86_64",
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

        model = platform.processor()
        if os.path.exists("/proc/cpuinfo"):
            try:
                with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
                    for line in f:
                        if "model name" in line:
                            model = line.split(":", 1)[1].strip()
                            break
            except Exception:
                pass

        return {
            "model": model,
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
            except Exception:
                partitions.append({
                    "device": p.device,
                    "mountpoint": p.mountpoint,
                    "fstype": p.fstype,
                    "error": "Acceso restringido",
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

        # Discos físicos con lsblk
        lsblk_out = self._run_cmd(["lsblk", "-o", "NAME,TYPE,SIZE,MODEL", "-d", "-n"])
        physical_disks = []
        if lsblk_out:
            for line in lsblk_out.splitlines():
                parts = line.split(maxsplit=3)
                if len(parts) >= 3:
                    physical_disks.append({
                        "FriendlyName": parts[3] if len(parts) > 3 else parts[0],
                        "MediaType": parts[1],
                        "BusType": "SATA/NVMe",
                        "HealthStatus": "Healthy",
                        "Size": parts[2],
                    })

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
                    fam = getattr(addr.family, "name", str(addr.family))
                    if "AF_INET6" in fam:
                        ipv6.append(addr.address)
                    elif "AF_INET" in fam:
                        ipv4.append(addr.address)
                    elif "AF_PACKET" in fam or "AF_LINK" in fam:
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
        lsusb_out = self._run_cmd(["lsusb"])
        devices = []
        for line in lsusb_out.splitlines():
            if not line.strip():
                continue
            parts = line.split(maxsplit=6)
            name = parts[6] if len(parts) > 6 else line
            devices.append({
                "FriendlyName": name,
                "Status": "OK",
                "InstanceId": parts[1] + ":" + parts[3] if len(parts) > 3 else "USB",
                "Class": "USBDevice",
            })

        # Comprobar dmesg para errores de USB
        dmesg_usb = self._run_cmd(["dmesg", "--level=err,warn"])
        problem_devices = []
        if "usb" in dmesg_usb.lower():
            for line in dmesg_usb.splitlines():
                if "usb" in line.lower() and ("error" in line.lower() or "failed" in line.lower()):
                    problem_devices.append({
                        "FriendlyName": line[:60],
                        "Status": "Error",
                        "Problem": line,
                    })

        return {
            "devices": devices,
            "problem_devices": problem_devices,
            "total_count": len(devices),
            "problem_count": len(problem_devices),
        }

    def get_pci_devices(self) -> Dict[str, Any]:
        lspci_out = self._run_cmd(["lspci", "-mm"])
        pci_devices = []
        for line in lspci_out.splitlines():
            if not line.strip():
                continue
            parts = [p.strip('"') for p in line.split('" "')]
            slot = parts[0].replace('"', '')
            cls = parts[1] if len(parts) > 1 else "Unknown"
            vendor = parts[2] if len(parts) > 2 else ""
            device = parts[3] if len(parts) > 3 else ""
            pci_devices.append({
                "FriendlyName": f"{vendor} {device}".strip(),
                "Status": "OK",
                "Class": cls,
                "InstanceId": slot,
            })

        return {
            "pci_devices": pci_devices,
            "usb_bus_devices": [],
        }

    def get_drivers_info(self) -> Dict[str, Any]:
        lsmod_out = self._run_cmd(["lsmod"])
        drivers = []
        lines = lsmod_out.splitlines()
        if len(lines) > 1:
            for line in lines[1:]:
                parts = line.split()
                if parts:
                    drivers.append({
                        "Driver": parts[0],
                        "OriginalFileName": parts[0] + ".ko",
                        "ClassName": "KernelModule",
                        "ProviderName": f"Size: {parts[1]} bytes, Used by: {parts[2] if len(parts) > 2 else '0'}"
                    })

        return {
            "drivers": drivers,
            "signed_drivers": drivers[:25],
            "total_count": len(drivers),
        }

    def get_problem_devices(self) -> Dict[str, Any]:
        dmesg_err = self._run_cmd(["dmesg", "--level=err"])
        errors = []
        if dmesg_err:
            for line in dmesg_err.splitlines()[:20]:
                errors.append({
                    "FriendlyName": line[:60],
                    "Status": "Error",
                    "Class": "SystemLog",
                    "InstanceId": "dmesg",
                })

        return {
            "errors": errors,
            "degraded": [],
            "unknown_count": 0,
            "total_problematic": len(errors),
        }

    def get_gpu_info(self) -> Dict[str, Any]:
        lspci_vga = self._run_cmd(["lspci"])
        gpus = []
        for line in lspci_vga.splitlines():
            if "VGA" in line or "3D controller" in line or "Display controller" in line:
                name = line.split(":", 2)[-1].strip() if ":" in line else line
                gpus.append({
                    "name": name,
                    "vram_gb": 0.0,
                    "driver_version": "N/D (Consulte lshw/nvidia-smi)",
                    "status": "OK",
                    "processor": name
                })

        return {
            "gpus": gpus,
            "is_healthy": len(gpus) > 0,
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
