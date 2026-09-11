"""
Backend para sistemas Microsoft Windows usando PowerShell, WMI/CIM y psutil.
Implementa el CONTRATO UNIFICADO de recolección de datos.
"""
import ctypes
import platform
import subprocess
import time
from typing import Any, Dict, List
import psutil

from diagnosqui.backends.base import BaseBackend
from diagnosqui.core.estados import (
    clasificar_porcentaje,
    clasificar_estado_windows,
    crear_contrato_base,
    contrato_error,
    detectar_apipa,
)


class WindowsBackend(BaseBackend):
    """Implementación de telemetría de hardware para Windows con contrato unificado."""

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
        except Exception as e:
            return f"__ERROR__: {e}"

    def _parse_csv_pnp(self, csv_data: str) -> List[Dict[str, str]]:
        """Auxiliar para convertir salida CSV de PowerShell en diccionarios."""
        if not csv_data or csv_data.startswith("__ERROR__"):
            return []
        lines = [l.strip() for l in csv_data.splitlines() if l.strip()]
        if len(lines) < 2:
            return []

        import csv
        import io
        try:
            reader = csv.DictReader(io.StringIO(csv_data))
            return [dict(row) for row in reader]
        except Exception:
            return []

    def is_elevated(self) -> bool:
        """Comprueba si el proceso corre con privilegios de Administrador."""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    def get_system_info(self) -> Dict[str, Any]:
        """Obtiene información del sistema operativo (sin contrato, es metadata)."""
        try:
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

            modelo = platform.processor()
            estado = clasificar_porcentaje(total_use)
            recomendacion = []
            if estado != "NORMAL":
                recomendacion.append("Identificar procesos con alto consumo de CPU")
                recomendacion.append("Verificar si hay procesos en bucle o malware")

            return crear_contrato_base(
                componente="CPU",
                evidencia=f"{total_use:.1f}% uso",
                valor_numerico=total_use,
                estado=estado,
                detalle={
                    "modelo": modelo,
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
            return contrato_error("CPU", e, "psutil.cpu_percent")

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
                recomendacion.append("Considerar ampliar RAM física")

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
                except (PermissionError, Exception) as e:
                    partitions.append({
                        "device": p.device,
                        "mountpoint": p.mountpoint,
                        "fstype": p.fstype,
                        "error": f"Acceso denegado: {e}"
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

            # Discos físicos usando PowerShell
            cmd_physical = (
                "Get-PhysicalDisk | Select-Object FriendlyName, MediaType, BusType, HealthStatus, Size | "
                "ConvertTo-Csv -NoTypeInformation"
            )
            csv_out = self._run_powershell(cmd_physical)
            physical_disks = []
            if csv_out and not csv_out.startswith("__ERROR__"):
                lines = [l.strip().strip('"') for l in csv_out.splitlines() if l.strip()]
                if len(lines) > 1:
                    headers = [h.strip('"') for h in lines[0].split('","')]
                    for row in lines[1:]:
                        vals = [v.strip('"') for v in row.split('","')]
                        d = dict(zip(headers, vals))
                        physical_disks.append(d)

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
            return contrato_error("Almacenamiento", e, "psutil.disk_partitions/usage")

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
                        family_name = getattr(addr.family, "name", str(addr.family))
                        if "AF_INET6" in family_name:
                            ipv6.append(addr.address)
                        elif "AF_INET" in family_name:
                            ipv4.append(addr.address)
                            all_ipv4.extend(addr.address)
                        elif "AF_LINK" in family_name or "AF_PACKET" in family_name:
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
            import socket

            # Obtener gateway por defecto
            gateway_ip = "N/D"
            try:
                route_out = self._run_powershell(
                    "Get-NetRoute -DestinationPrefix '0.0.0.0/0' | Select-Object -ExpandProperty NextHop"
                )
                if route_out and not route_out.startswith("__ERROR__"):
                    gateway_ip = route_out.strip()
            except Exception:
                pass

            checks = {"gateway": False, "internet": False, "dns": False}
            detalles = {"gateway_ip": gateway_ip, "dns_servers": []}

            # Ping gateway
            if gateway_ip != "N/D":
                try:
                    res = subprocess.run(
                        ["ping", "-n", "1", "-w", "1000", gateway_ip],
                        capture_output=True, timeout=3, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                    )
                    checks["gateway"] = (res.returncode == 0)
                except Exception:
                    pass

            # Ping 8.8.8.8
            try:
                res = subprocess.run(
                    ["ping", "-n", "1", "-w", "2000", "8.8.8.8"],
                    capture_output=True, timeout=4, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                )
                checks["internet"] = (res.returncode == 0)
            except Exception:
                pass

            # DNS resolution
            try:
                socket.gethostbyname("google.com")
                checks["dns"] = True
                # Obtener DNS servers
                try:
                    dns_out = self._run_powershell(
                        "Get-DnsClientServerAddress -AddressFamily IPv4 | Where-Object {$_.ServerAddresses} | Select-Object -ExpandProperty ServerAddresses"
                    )
                    if dns_out and not dns_out.startswith("__ERROR__"):
                        detalles["dns_servers"] = [ip.strip() for ip in dns_out.splitlines() if ip.strip()]
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
                recomendacion.append("Fallo de resolución DNS: verificar configuración DNS")

            return crear_contrato_base(
                componente="Conectividad",
                evidencia=f"Gateway: {'OK' if checks['gateway'] else 'FAIL'}, Internet: {'OK' if checks['internet'] else 'FAIL'}, DNS: {'OK' if checks['dns'] else 'FAIL'}",
                valor_numerico=float(exitos),
                estado=estado,
                detalle=detalles,
                recomendacion=recomendacion
            )
        except Exception as e:
            return contrato_error("Conectividad", e, "ping/socket")

    def get_usb_devices(self) -> Dict[str, Any]:
        """Obtiene dispositivos USB y devuelve CONTRATO UNIFICADO."""
        try:
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

            # Clasificar estados según regla Windows
            problem_count = 0
            for d in devices:
                d["estado_clasificado"] = clasificar_estado_windows(d.get("Status", ""))
                if d["estado_clasificado"] != "NORMAL":
                    problem_count += 1

            for p in problem_devices:
                p["estado_clasificado"] = clasificar_estado_windows(p.get("Status", ""))

            estado = "NORMAL"
            if problem_count > 2:
                estado = "CRITICO"
            elif problem_count > 0:
                estado = "ADVERTENCIA"

            recomendacion = []
            if problem_count > 0:
                recomendacion.append("Reubicar periféricos a puertos raíz (directo a placa base)")
                recomendacion.append("Actualizar controladores de bus USB desde Administrador de dispositivos")

            return crear_contrato_base(
                componente="USB",
                evidencia=f"{len(devices)} dispositivos, {problem_count} con problemas",
                valor_numerico=float(problem_count),
                estado=estado,
                detalle={
                    "dispositivos": devices,
                    "problemas": problem_devices,
                },
                recomendacion=recomendacion
            )
        except Exception as e:
            return contrato_error("USB", e, "Get-PnpDevice USB")

    def get_pci_devices(self) -> Dict[str, Any]:
        """Obtiene dispositivos PCI/PCIe/ACPI y devuelve CONTRATO UNIFICADO."""
        try:
            cmd_pci = (
                "Get-PnpDevice -PresentOnly | Where-Object {$_.InstanceId -like 'PCI*' -or $_.InstanceId -like 'ACPI*'} | "
                "Select-Object FriendlyName, Status, Class, InstanceId | ConvertTo-Csv -NoTypeInformation"
            )
            cmd_bus = (
                "Get-PnpDevice -PresentOnly -Bus USB | Select-Object FriendlyName, Status, InstanceId | ConvertTo-Csv -NoTypeInformation"
            )

            pci_devs = self._parse_csv_pnp(self._run_powershell(cmd_pci))
            bus_devs = self._parse_csv_pnp(self._run_powershell(cmd_bus))

            # Clasificar estados
            problem_count = 0
            for d in pci_devs:
                d["estado_clasificado"] = clasificar_estado_windows(d.get("Status", ""))
                if d["estado_clasificado"] != "NORMAL":
                    problem_count += 1

            for b in bus_devs:
                b["estado_clasificado"] = clasificar_estado_windows(b.get("Status", ""))

            estado = "NORMAL"
            if problem_count > 2:
                estado = "CRITICO"
            elif problem_count > 0:
                estado = "ADVERTENCIA"

            return crear_contrato_base(
                componente="PCI",
                evidencia=f"{len(pci_devs)} dispositivos PCI/ACPI detectados",
                valor_numerico=float(len(pci_devs)),
                estado=estado,
                detalle={
                    "dispositivos": pci_devs,
                    "buses_usb": bus_devs,
                },
                recomendacion=[]
            )
        except Exception as e:
            return contrato_error("PCI", e, "Get-PnpDevice PCI/ACPI")

    def get_drivers_info(self) -> Dict[str, Any]:
        """Obtiene controladores del sistema y devuelve CONTRATO UNIFICADO."""
        try:
            # driverquery
            drivers = []
            try:
                res = subprocess.run(
                    ["driverquery", "/FO", "CSV"],
                    timeout=15,
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

            return crear_contrato_base(
                componente="Controladores",
                evidencia=f"{len(drivers)} drivers cargados",
                valor_numerico=float(len(drivers)),
                estado="NORMAL",
                detalle={
                    "drivers": drivers,
                    "drivers_firmados": signed,
                },
                recomendacion=[]
            )
        except Exception as e:
            return contrato_error("Controladores", e, "driverquery/Get-WindowsDriver")

    def get_problem_devices(self) -> Dict[str, Any]:
        """Obtiene dispositivos con problemas y devuelve CONTRATO UNIFICADO."""
        try:
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

            total = len(errors) + len(degraded) + unk_count
            estado = "NORMAL"
            if total > 2:
                estado = "CRITICO"
            elif total > 0:
                estado = "ADVERTENCIA"

            recomendacion = []
            if total > 0:
                recomendacion.append("Revisar Administrador de dispositivos para instalar drivers faltantes")
                recomendacion.append("Verificar conexión física de periféricos con error")

            return crear_contrato_base(
                componente="Problemas",
                evidencia=f"{total} dispositivo(s) con errores/desconocidos",
                valor_numerico=float(total),
                estado=estado,
                detalle={
                    "errores": errors,
                    "degradados": degraded,
                    "desconocidos": unk_count,
                    "nota_permisos": "" if self.is_elevated() else "Requiere Administrador para ver todos los dispositivos"
                },
                recomendacion=recomendacion
            )
        except Exception as e:
            return contrato_error("Problemas", e, "Get-PnpDevice Error/Degraded/Unknown")

    def get_gpu_info(self) -> Dict[str, Any]:
        """Obtiene información de GPU y devuelve CONTRATO UNIFICADO."""
        try:
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
                    "vram_gb": round(ram_gb, 2),
                    "driver_version": driver,
                    "status": status,
                    "processor": g.get("VideoProcessor", "N/D")
                })

            estado = "NORMAL" if gpu_ok and parsed_gpus else "ADVERTENCIA"
            if not parsed_gpus:
                estado = "CRITICO"

            recomendacion = []
            if not gpu_ok:
                recomendacion.append("Actualizar controlador gráfico desde fabricante (NVIDIA/AMD/Intel)")
            if not parsed_gpus:
                recomendacion.append("No se detectó GPU: verificar conexión y drivers")

            evid = parsed_gpus[0]["name"] if parsed_gpus else "No detectada"
            if parsed_gpus:
                evid += f" (Driver: {parsed_gpus[0]['driver_version']}, VRAM: {parsed_gpus[0]['vram_gb']:.2f} GB)"

            return crear_contrato_base(
                componente="GPU",
                evidencia=evid,
                valor_numerico=0.0 if gpu_ok else 1.0,
                estado=estado,
                detalle={
                    "gpus": parsed_gpus,
                    "driver_version": parsed_gpus[0]["driver_version"] if parsed_gpus else "N/D",
                    "vram_gb": parsed_gpus[0]["vram_gb"] if parsed_gpus else 0.0,
                },
                recomendacion=recomendacion
            )
        except Exception as e:
            return contrato_error("GPU", e, "Get-CimInstance Win32_VideoController")

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