"""
Backend para sistemas Linux usando /proc, /sys, lspci, lsusb, lsmod y psutil.
Implementa el CONTRATO UNIFICADO de recolección de datos.
"""
import os
import platform
import socket
import subprocess
import time
from typing import Any, Dict, List
import psutil

from diagnosqui.backends.base import BaseBackend
from diagnosqui.core.estados import (
    clasificar_porcentaje,
    crear_contrato_base,
    contrato_error,
    detectar_apipa,
)


class LinuxBackend(BaseBackend):
    """Implementación de telemetría de hardware para sistemas Linux con contrato unificado."""

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
        except (FileNotFoundError, PermissionError, subprocess.SubprocessError) as e:
            return f"__ERROR__: {e}"

    def is_elevated(self) -> bool:
        """Comprueba si el proceso corre como root (UID 0)."""
        try:
            return os.geteuid() == 0
        except AttributeError:
            return False

    def get_system_info(self) -> Dict[str, Any]:
        """Obtiene información del sistema operativo (sin contrato, es metadata)."""
        try:
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
        except Exception as e:
            return {"error": str(e)}

    def get_cpu_info(self) -> Dict[str, Any]:
        """Obtiene información de CPU y devuelve CONTRATO UNIFICADO."""
        try:
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

            estado = clasificar_porcentaje(total_use)
            recomendacion = []
            if estado != "NORMAL":
                recomendacion.append("Identificar procesos con alto consumo de CPU (top/htop)")
                recomendacion.append("Verificar si hay procesos en bucle o malware")

            return crear_contrato_base(
                componente="CPU",
                evidencia=f"{total_use:.1f}% uso",
                valor_numerico=total_use,
                estado=estado,
                detalle={
                    "modelo": model,
                    "nucleos_fisicos": physical_cores,
                    "nucleos_logicos": logical_cores,
                    "frecuencia_actual_mhz": freq.current if freq else 0.0,
                    "frecuencia_min_mhz": freq.min if freq else 0.0,
                    "frecuencia_max_mhz": freq.max if freq else 0.0,
                    "por_nucleo": per_cpu,
                },
                recomendacion=recomendacion
            )
        except Exception as e:
            return contrato_error("CPU", e, "psutil.cpu_percent /proc/cpuinfo")

    def get_memory_info(self) -> Dict[str, Any]:
        """Obtiene información de memoria RAM y devuelve CONTRATO UNIFICADO."""
        try:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()

            total_gb = mem.total / (1024 ** 3)
            available_gb = mem.available / (1024 ** 3)
            used_gb = mem.used / (1024 ** 3)
            percent = mem.percent

            estado = clasificar_porcentaje(percent)
            recomendacion = []
            if estado != "NORMAL":
                recomendacion.append("Cerrar aplicaciones con fuga de memoria")
                recomendacion.append("Considerar ampliar RAM física o configurar swap")

            return crear_contrato_base(
                componente="Memoria",
                evidencia=f"{percent:.1f}% ({used_gb:.1f}/{total_gb:.1f} GB)",
                valor_numerico=percent,
                estado=estado,
                detalle={
                    "total_gb": round(total_gb, 2),
                    "disponible_gb": round(available_gb, 2),
                    "usada_gb": round(used_gb, 2),
                    "swap_total_gb": round(swap.total / (1024 ** 3), 2),
                    "swap_usada_gb": round(swap.used / (1024 ** 3), 2),
                    "swap_porcentaje": round(swap.percent, 1),
                },
                recomendacion=recomendacion
            )
        except Exception as e:
            return contrato_error("Memoria", e, "psutil.virtual_memory")

    def get_disks_info(self) -> Dict[str, Any]:
        """Obtiene información de almacenamiento y devuelve CONTRATO UNIFICADO."""
        try:
            partitions = []
            max_pct = 0.0
            max_desc = "Sin unidades montadas"

            for p in psutil.disk_partitions(all=False):
                try:
                    usage = psutil.disk_usage(p.mountpoint)
                    pct = usage.percent
                    partitions.append({
                        "device": p.device,
                        "mountpoint": p.mountpoint,
                        "fstype": p.fstype,
                        "total_gb": round(usage.total / (1024 ** 3), 2),
                        "used_gb": round(usage.used / (1024 ** 3), 2),
                        "free_gb": round(usage.free / (1024 ** 3), 2),
                        "percent": round(pct, 1),
                    })
                    if pct > max_pct:
                        max_pct = pct
                        max_desc = f"{p.device} al {pct:.1f}%"
                except Exception as e:
                    partitions.append({
                        "device": p.device,
                        "mountpoint": p.mountpoint,
                        "fstype": p.fstype,
                        "error": f"Acceso restringido: {e}"
                    })

            io_stats = None
            try:
                io = psutil.disk_io_counters()
                if io:
                    io_stats = {
                        "read_count": io.read_count,
                        "write_count": io.write_count,
                        "read_mb": round(io.read_bytes / (1024 ** 2), 2),
                        "write_mb": round(io.write_bytes / (1024 ** 2), 2),
                    }
            except Exception:
                pass

            # Discos físicos con lsblk
            lsblk_out = self._run_cmd(["lsblk", "-o", "NAME,TYPE,SIZE,MODEL,TRAN", "-d", "-n"])
            physical_disks = []
            if lsblk_out and not lsblk_out.startswith("__ERROR__"):
                for line in lsblk_out.splitlines():
                    parts = line.split(maxsplit=4)
                    if len(parts) >= 3:
                        bus_type = parts[4] if len(parts) > 4 else "SATA/NVMe"
                        physical_disks.append({
                            "FriendlyName": parts[3] if len(parts) > 3 else parts[0],
                            "MediaType": parts[1],
                            "BusType": bus_type.upper(),
                            "HealthStatus": "Healthy",
                            "Size": parts[2],
                        })

            estado = clasificar_porcentaje(max_pct)
            recomendacion = []
            if estado != "NORMAL":
                recomendacion.append("Liberar espacio en la partición más llena")
                if max_pct >= 90:
                    recomendacion.append("URGENTE: Espacio crítico, riesgo de fallo de sistema")

            return crear_contrato_base(
                componente="Almacenamiento",
                evidencia=max_desc,
                valor_numerico=max_pct,
                estado=estado,
                detalle={
                    "particiones": partitions,
                    "discos_fisicos": physical_disks,
                    "io_stats": io_stats,
                },
                recomendacion=recomendacion
            )
        except Exception as e:
            return contrato_error("Almacenamiento", e, "psutil.disk_partitions/usage lsblk")

    def get_network_info(self) -> Dict[str, Any]:
        """Obtiene información de interfaces de red y devuelve CONTRATO UNIFICADO."""
        try:
            adapters_stats = psutil.net_if_stats()
            adapters_addrs = psutil.net_if_addrs()
            net_io = psutil.net_io_counters()

            interfaces = []
            all_ipv4 = []
            active_count = 0

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
                            all_ipv4.extend(ipv4)
                        elif "AF_PACKET" in fam or "AF_LINK" in fam:
                            mac = addr.address

                is_up = stats.isup
                if is_up:
                    active_count += 1

                interfaces.append({
                    "name": name,
                    "is_up": is_up,
                    "speed_mbps": stats.speed,
                    "mtu": stats.mtu,
                    "ipv4": ipv4,
                    "ipv6": ipv6,
                    "mac": mac or "N/D",
                })

            apipa = detectar_apipa(all_ipv4)
            estado = "CRITICO" if apipa else ("ADVERTENCIA" if active_count == 0 else "NORMAL")
            recomendacion = []
            if apipa:
                recomendacion.append("IP APIPA detectada (169.254.x.x): sin servidor DHCP")
                recomendacion.append("Verificar conexión de red y servidor DHCP")
            elif active_count == 0:
                recomendacion.append("Ninguna interfaz de red activa")

            return crear_contrato_base(
                componente="Red",
                evidencia=f"{len(interfaces)} interfaces, {active_count} activas",
                valor_numerico=float(active_count),
                estado=estado,
                detalle={
                    "interfaces": interfaces,
                    "global_io": {
                        "sent_mb": round(net_io.bytes_sent / (1024 ** 2), 2),
                        "recv_mb": round(net_io.bytes_recv / (1024 ** 2), 2),
                        "packets_sent": net_io.packets_sent,
                        "packets_recv": net_io.packets_recv,
                        "errin": net_io.errin,
                        "errout": net_io.errout,
                        "dropin": net_io.dropin,
                        "dropout": net_io.dropout,
                    },
                    "apipa_detectada": apipa,
                },
                recomendacion=recomendacion
            )
        except Exception as e:
            return contrato_error("Red", e, "psutil.net_if_addrs/stats")

    def get_connectivity_info(self) -> Dict[str, Any]:
        """Obtiene información de conectividad (ping gateway, ping 8.8.8.8, DNS)."""
        try:
            # Obtener gateway por defecto
            gateway_ip = "N/D"
            try:
                route_out = self._run_cmd(["ip", "route", "show", "default"])
                if route_out and not route_out.startswith("__ERROR__"):
                    parts = route_out.split()
                    if "via" in parts:
                        gateway_ip = parts[parts.index("via") + 1]
            except Exception:
                pass

            checks = {"gateway": False, "internet": False, "dns": False}
            detalles = {"gateway_ip": gateway_ip, "dns_servers": []}

            # Ping gateway
            if gateway_ip != "N/D":
                try:
                    res = subprocess.run(
                        ["ping", "-c", "1", "-W", "2", gateway_ip],
                        capture_output=True, timeout=3
                    )
                    checks["gateway"] = (res.returncode == 0)
                except Exception:
                    pass

            # Ping 8.8.8.8
            try:
                res = subprocess.run(
                    ["ping", "-c", "1", "-W", "3", "8.8.8.8"],
                    capture_output=True, timeout=4
                )
                checks["internet"] = (res.returncode == 0)
            except Exception:
                pass

            # DNS resolution
            try:
                socket.gethostbyname("google.com")
                checks["dns"] = True
                # Obtener DNS servers de /etc/resolv.conf
                try:
                    if os.path.exists("/etc/resolv.conf"):
                        with open("/etc/resolv.conf", "r") as f:
                            for line in f:
                                if line.startswith("nameserver"):
                                    ip = line.split()[1]
                                    detalles["dns_servers"].append(ip)
                except Exception:
                    pass
            except Exception:
                pass

            exitos = sum(checks.values())
            if exitos == 3:
                estado = "NORMAL"
            elif exitos >= 1:
                estado = "ADVERTENCIA"
            else:
                estado = "CRITICO"

            recomendacion = []
            if not checks["gateway"]:
                recomendacion.append("No hay respuesta del gateway: verificar conexión física/router")
            if not checks["internet"]:
                recomendacion.append("Sin conectividad a Internet: verificar ISP / firewall")
            if not checks["dns"]:
                recomendacion.append("Fallo de resolución DNS: verificar /etc/resolv.conf")

            return crear_contrato_base(
                componente="Conectividad",
                evidencia=f"Gateway: {'OK' if checks['gateway'] else 'FAIL'}, Internet: {'OK' if checks['internet'] else 'FAIL'}, DNS: {'OK' if checks['dns'] else 'FAIL'}",
                valor_numerico=float(exitos),
                estado=estado,
                detalle=detalles,
                recomendacion=recomendacion
            )
        except Exception as e:
            return contrato_error("Conectividad", e, "ping/socket /etc/resolv.conf")

    def get_usb_devices(self) -> Dict[str, Any]:
        """Obtiene dispositivos USB y devuelve CONTRATO UNIFICADO."""
        try:
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
            problem_devices = []
            dmesg_usb = self._run_cmd(["dmesg", "--level=err,warn"])
            permiso_dmesg = True
            if dmesg_usb.startswith("__ERROR__"):
                permiso_dmesg = False
            elif "usb" in dmesg_usb.lower():
                for line in dmesg_usb.splitlines():
                    if "usb" in line.lower() and ("error" in line.lower() or "failed" in line.lower()):
                        problem_devices.append({
                            "FriendlyName": line[:60],
                            "Status": "Error",
                            "Problem": line,
                        })

            problem_count = len(problem_devices)
            estado = "NORMAL"
            if problem_count > 2:
                estado = "CRITICO"
            elif problem_count > 0:
                estado = "ADVERTENCIA"

            recomendacion = []
            if not permiso_dmesg:
                recomendacion.append("Requiere root para acceder a dmesg (ejecutar con sudo)")
            elif problem_count > 0:
                recomendacion.append("Revisar dmesg para detalles de errores USB")
                recomendacion.append("Probar puertos USB diferentes o hub alimentado")

            return crear_contrato_base(
                componente="USB",
                evidencia=f"{len(devices)} dispositivos, {problem_count} con problemas",
                valor_numerico=float(problem_count),
                estado=estado,
                detalle={
                    "dispositivos": devices,
                    "problemas": problem_devices,
                    "nota_permisos": "" if permiso_dmesg else "dmesg requiere root"
                },
                recomendacion=recomendacion
            )
        except Exception as e:
            return contrato_error("USB", e, "lsusb dmesg")

    def get_pci_devices(self) -> Dict[str, Any]:
        """Obtiene dispositivos PCI/PCIe y devuelve CONTRATO UNIFICADO."""
        try:
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

            return crear_contrato_base(
                componente="PCI",
                evidencia=f"{len(pci_devices)} dispositivos PCI detectados",
                valor_numerico=float(len(pci_devices)),
                estado="NORMAL",
                detalle={
                    "dispositivos": pci_devices,
                    "buses_usb": [],
                },
                recomendacion=[]
            )
        except Exception as e:
            return contrato_error("PCI", e, "lspci")

    def get_drivers_info(self) -> Dict[str, Any]:
        """Obtiene módulos del kernel y devuelve CONTRATO UNIFICADO."""
        try:
            lsmod_out = self._run_cmd(["lsmod"])
            drivers = []
            lines = lsmod_out.splitlines()
            if len(lines) > 1:
                for line in lines[1:]:
                    parts = line.split()
                    if parts:
                        # Intentar obtener más info con modinfo
                        modinfo_out = self._run_cmd(["modinfo", "-d", parts[0]])
                        desc = modinfo_out if modinfo_out and not modinfo_out.startswith("__ERROR__") else ""
                        drivers.append({
                            "Driver": parts[0],
                            "OriginalFileName": parts[0] + ".ko",
                            "ClassName": "KernelModule",
                            "ProviderName": f"Size: {parts[1]} bytes, Used by: {parts[2] if len(parts) > 2 else '0'}",
                            "Description": desc,
                        })

            return crear_contrato_base(
                componente="Controladores",
                evidencia=f"{len(drivers)} módulos de kernel cargados",
                valor_numerico=float(len(drivers)),
                estado="NORMAL",
                detalle={
                    "drivers": drivers,
                    "drivers_firmados": drivers[:25],
                },
                recomendacion=[]
            )
        except Exception as e:
            return contrato_error("Controladores", e, "lsmod modinfo")

    def get_problem_devices(self) -> Dict[str, Any]:
        """Obtiene dispositivos con problemas y devuelve CONTRATO UNIFICADO."""
        try:
            errors = []
            permiso_dmesg = True

            dmesg_err = self._run_cmd(["dmesg", "--level=err"])
            if dmesg_err.startswith("__ERROR__"):
                permiso_dmesg = False
            elif dmesg_err:
                for line in dmesg_err.splitlines()[:20]:
                    errors.append({
                        "FriendlyName": line[:60],
                        "Status": "Error",
                        "Class": "SystemLog",
                        "InstanceId": "dmesg",
                    })

            # También probar journalctl si está disponible
            journal_errors = []
            if not errors:
                journal_out = self._run_cmd(["journalctl", "-p", "3", "-n", "20", "--no-pager"])
                if not journal_out.startswith("__ERROR__") and journal_out:
                    for line in journal_out.splitlines()[:20]:
                        journal_errors.append({
                            "FriendlyName": line[:80],
                            "Status": "Error",
                            "Class": "Journal",
                            "InstanceId": "journalctl",
                        })

            total = len(errors) + len(journal_errors)
            estado = "NORMAL"
            if total > 2:
                estado = "CRITICO"
            elif total > 0:
                estado = "ADVERTENCIA"

            recomendacion = []
            if not permiso_dmesg:
                recomendacion.append("Requiere root para acceder a dmesg/journalctl (ejecutar con sudo)")
            elif total > 0:
                recomendacion.append("Revisar logs del sistema para identificar hardware problemático")

            return crear_contrato_base(
                componente="Problemas",
                evidencia=f"{total} incidente(s) en logs del sistema",
                valor_numerico=float(total),
                estado=estado,
                detalle={
                    "errores": errors,
                    "degradados": [],
                    "desconocidos": 0,
                    "journal_errores": journal_errors,
                    "nota_permisos": "" if permiso_dmesg else "dmesg/journalctl requieren root"
                },
                recomendacion=recomendacion
            )
        except Exception as e:
            return contrato_error("Problemas", e, "dmesg journalctl")

    def get_gpu_info(self) -> Dict[str, Any]:
        """Obtiene información de GPU y devuelve CONTRATO UNIFICADO."""
        try:
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

            # Intentar obtener info de driver con glxinfo si está disponible
            driver_version = "N/D"
            glxinfo_out = self._run_cmd(["glxinfo", "-B"])
            if glxinfo_out and not glxinfo_out.startswith("__ERROR__"):
                for line in glxinfo_out.splitlines():
                    if "OpenGL version" in line or "OpenGL renderer" in line:
                        driver_version = line.split(":", 1)[1].strip()
                        break

            estado = "NORMAL" if gpus else "CRITICO"
            recomendacion = []
            if not gpus:
                recomendacion.append("No se detectó GPU: verificar lspci y drivers de kernel")
            elif driver_version == "N/D":
                recomendacion.append("Instalar glxinfo (mesa-utils) para detalles de driver OpenGL")

            evid = gpus[0]["name"] if gpus else "No detectada"
            if gpus and driver_version != "N/D":
                evid += f" (OpenGL: {driver_version})"

            return crear_contrato_base(
                componente="GPU",
                evidencia=evid,
                valor_numerico=0.0 if gpus else 1.0,
                estado=estado,
                detalle={
                    "gpus": gpus,
                    "driver_version": driver_version,
                    "vram_gb": gpus[0]["vram_gb"] if gpus else 0.0,
                },
                recomendacion=recomendacion
            )
        except Exception as e:
            return contrato_error("GPU", e, "lspci glxinfo")

    def get_io_delta(self, duration: int = 3) -> Dict[str, Any]:
        """Captura delta de E/S en disco y red en un intervalo."""
        try:
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
                    "read_kb": round((d_after.read_bytes - d_before.read_bytes) / 1024, 2),
                    "write_kb": round((d_after.write_bytes - d_before.write_bytes) / 1024, 2),
                }

            net_delta = {}
            if n_before and n_after:
                net_delta = {
                    "sent_kb": round((n_after.bytes_sent - n_before.bytes_sent) / 1024, 2),
                    "recv_kb": round((n_after.bytes_recv - n_before.bytes_recv) / 1024, 2),
                    "packets_sent": n_after.packets_sent - n_before.packets_sent,
                    "packets_recv": n_after.packets_recv - n_before.packets_recv,
                }

            return {
                "duration": duration,
                "disk": disk_delta,
                "net": net_delta,
            }
        except Exception as e:
            return {"error": str(e), "duration": duration, "disk": {}, "net": {}}