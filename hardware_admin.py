import psutil
import platform
import subprocess
import time
import os


def get_powershell_output(cmd):
    try:
        result = subprocess.run(
            ["powershell", "-Command", cmd],
            capture_output=True, text=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW
        )
        return result.stdout.strip()
    except Exception:
        return ""


def sistema():
    print("\n" + "=" * 50)
    print("  INFORMACIÓN DEL SISTEMA")
    print("=" * 50)
    print(f"  Sistema operativo : {platform.system()} {platform.release()}")
    print(f"  Versión           : {platform.version()}")
    print(f"  Plataforma        : {platform.platform()}")
    print(f"  Procesador        : {platform.processor()}")
    print(f"  Arquitectura      : {platform.machine()}")
    print(f"  Nombre del equipo : {platform.node()}")
    print(f"  Python            : {platform.python_version()}")

    boot = psutil.boot_time()
    uptime = time.time() - boot
    horas = int(uptime // 3600)
    minutos = int((uptime % 3600) // 60)
    print(f"  Tiempo encendido  : {horas}h {minutos}m")
    print("=" * 50)


def cpu():
    print("\n" + "=" * 50)
    print("  INFORMACIÓN DE CPU")
    print("=" * 50)
    print(f"  Modelo            : {platform.processor()}")
    print(f"  Núcleos físicos   : {psutil.cpu_count(logical=False)}")
    print(f"  Núcleos lógicos   : {psutil.cpu_count(logical=True)}")
    print(f"  Frecuencia base   : {psutil.cpu_freq().min:.0f} MHz - {psutil.cpu_freq().max:.0f} MHz")

    print("\n  Uso por núcleo:")
    por_nucleo = psutil.cpu_percent(interval=1, percpu=True)
    for i, porcentaje in enumerate(por_nucleo):
        barra = "#" * int(porcentaje / 5) + "-" * (20 - int(porcentaje / 5))
        print(f"    Núcleo {i:>2}: [{barra}] {porcentaje:>5.1f}%")

    uso = psutil.cpu_percent(interval=2)
    print(f"\n  Uso total: {uso}%")
    if uso > 90:
        print("  [!] Estado: CRITICO - Carga CPU elevada")
    elif uso > 70:
        print("  [!] Estado: ALERTA - Carga CPU moderada-alta")
    else:
        print("  [OK] Estado: OK - Carga CPU normal")
    print("=" * 50)


def memoria():
    print("\n" + "=" * 50)
    print("  INFORMACIÓN DE MEMORIA RAM")
    print("=" * 50)
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    total_gb = mem.total / (1024 ** 3)
    disponible_gb = mem.available / (1024 ** 3)
    usado_gb = mem.used / (1024 ** 3)

    print(f"  Total             : {total_gb:.2f} GB")
    print(f"  Disponible        : {disponible_gb:.2f} GB")
    print(f"  Usado             : {usado_gb:.2f} GB")
    print(f"  Porcentaje uso    : {mem.percent}%")

    barra = "#" * int(mem.percent / 5) + "-" * (20 - int(mem.percent / 5))
    print(f"  Uso: [{barra}] {mem.percent:.1f}%")

    print(f"\n  Memoria swap:")
    print(f"    Total           : {swap.total / (1024 ** 3):.2f} GB")
    print(f"    Usada           : {swap.used / (1024 ** 3):.2f} GB")
    print(f"    Uso swap        : {swap.percent}%")

    if mem.percent > 90:
        print("\n  [!] Estado: CRITICO - Poca memoria disponible")
    elif mem.percent > 70:
        print("\n  [!] Estado: ALERTA - Memoria moderada")
    else:
        print("\n  [OK] Estado: OK - Memoria suficiente")
    print("=" * 50)


def discos():
    print("\n" + "=" * 50)
    print("  INFORMACIÓN DE ALMACENAMIENTO")
    print("=" * 50)

    particiones = psutil.disk_partitions()
    for p in particiones:
        try:
            uso = psutil.disk_usage(p.mountpoint)
            total_gb = uso.total / (1024 ** 3)
            usado_gb = uso.used / (1024 ** 3)
            libre_gb = uso.free / (1024 ** 3)

            print(f"\n  Unidad: {p.device}")
            print(f"    Montaje     : {p.mountpoint}")
            print(f"    Sistema     : {p.fstype}")
            print(f"    Total       : {total_gb:.2f} GB")
            print(f"    Usado       : {usado_gb:.2f} GB")
            print(f"    Libre       : {libre_gb:.2f} GB")
            print(f"    Uso         : {uso.percent}%")

            barra = "#" * int(uso.percent / 5) + "-" * (20 - int(uso.percent / 5))
            print(f"    Barra: [{barra}] {uso.percent:.1f}%")
        except PermissionError:
            print(f"\n  Unidad: {p.device} - Sin permisos de acceso")

    try:
        disk_io = psutil.disk_io_counters()
        print(f"\n  Estadísticas de E/S:")
        print(f"    Lecturas     : {disk_io.read_count}")
        print(f"    Escrituras   : {disk_io.write_count}")
        print(f"    Bytes leídos : {disk_io.read_bytes / (1024 ** 2):.2f} MB")
        print(f"    Bytes escritos: {disk_io.write_bytes / (1024 ** 2):.2f} MB")
    except Exception:
        pass

    disks_info = get_powershell_output(
        "Get-PhysicalDisk | Format-Table FriendlyName, MediaType, BusType, HealthStatus -AutoSize"
    )
    if disks_info:
        print(f"\n  Físicos:")
        print(disks_info)
    print("=" * 50)


def red():
    print("\n" + "=" * 50)
    print("  INFORMACIÓN DE RED")
    print("=" * 50)

    adapters = psutil.net_if_stats()
    addrs = psutil.net_if_addrs()

    for nombre, stats in adapters.items():
        print(f"\n  Adaptador: {nombre}")
        print(f"    Estado      : {'Activo' if stats.isup else 'Inactivo'}")
        print(f"    Velocidad   : {stats.speed} Mbps")
        print(f"    MTU         : {stats.mtu}")

        if nombre in addrs:
            for addr in addrs[nombre]:
                if addr.family.name == "AF_INET":
                    print(f"    IPv4        : {addr.address}")
                elif addr.family.name == "AF_INET6":
                    print(f"    IPv6        : {addr.address}")
                elif addr.family.name == "AF_LINK":
                    print(f"    MAC         : {addr.address}")

    io = psutil.net_io_counters()
    print(f"\n  Estadísticas globales:")
    print(f"    Bytes enviados   : {io.bytes_sent / (1024 ** 2):.2f} MB")
    print(f"    Bytes recibidos  : {io.bytes_recv / (1024 ** 2):.2f} MB")
    print(f"    Paquetes enviados: {io.packets_sent}")
    print(f"    Paquetes recibidos: {io.packets_recv}")
    print(f"    Errores entrada  : {io.errin}")
    print(f"    Errores salida   : {io.errout}")
    print(f"    Descartes entrada: {io.dropin}")
    print(f"    Descartes salida : {io.dropout}")
    print("=" * 50)


def usb():
    print("\n" + "=" * 50)
    print("  DISPOSITIVOS USB")
    print("=" * 50)

    usb_devices = get_powershell_output(
        "Get-PnpDevice -PresentOnly | Where-Object {$_.InstanceId -like 'USB*'} | "
        "Format-Table FriendlyName, Status, InstanceId -AutoSize"
    )
    if usb_devices:
        print(usb_devices)
    else:
        print("  No se detectaron dispositivos USB o no hay permisos.")

    problema = get_powershell_output(
        "Get-PnpDevice -PresentOnly | Where-Object {$_.InstanceId -like 'USB*' -and $_.Status -ne 'OK'} | "
        "Format-Table FriendlyName, Status, Problem -AutoSize"
    )
    if problema:
        print("  [!] Dispositivos USB con problemas:")
        print(problema)
    else:
        print("  [OK] Todos los dispositivos USB funcionan correctamente.")
    print("=" * 50)


def pci():
    print("\n" + "=" * 50)
    print("  DISPOSITIVOS PCI / PCIe")
    print("=" * 50)

    pci_devices = get_powershell_output(
        "Get-PnpDevice -PresentOnly | Where-Object {"
        "$_.InstanceId -like 'PCI*' -or $_.InstanceId -like 'ACPI*'} | "
        "Format-Table FriendlyName, Status, Class, InstanceId -AutoSize"
    )
    if pci_devices:
        print(pci_devices)
    else:
        print("  No se detectaron dispositivos PCI/PCIe.")

    bus_info = get_powershell_output(
        "Get-PnpDevice -PresentOnly -Bus USB | Format-Table FriendlyName, Status -AutoSize"
    )
    if bus_info:
        print("\n  Dispositivos en bus USB (emulación):")
        print(bus_info)
    print("=" * 50)


def controladores():
    print("\n" + "=" * 50)
    print("  CONTROLADORES (DRIVERS)")
    print("=" * 50)

    drivers = get_powershell_output(
        "driverquery /FO TABLE"
    )
    if drivers:
        print(drivers)
    else:
        print("  No se pudieron obtener los controladores.")

    print("\n  Controladores firmados:")
    firmados = get_powershell_output(
        "Get-WindowsDriver -Online -ErrorAction SilentlyContinue | "
        "Select-Object -First 20 Driver, OriginalFileName, ClassName, ProviderName | "
        "Format-Table -AutoSize"
    )
    if firmados:
        print(firmados)
    print("=" * 50)


def problemas():
    print("\n" + "=" * 50)
    print("  DISPOSITIVOS CON PROBLEMAS")
    print("=" * 50)

    errores = get_powershell_output(
        "Get-PnpDevice | Where-Object {$_.Status -eq 'Error'} | "
        "Format-Table FriendlyName, Status, Class, InstanceId -AutoSize"
    )
    if errores:
        print("  Dispositivos con ERROR:")
        print(errores)
    else:
        print("  [OK] No se detectaron dispositivos con errores.")

    desconocidos = get_powershell_output(
        "Get-PnpDevice | Where-Object {$_.Status -eq 'Unknown'} | "
        "Measure-Object | Select-Object -ExpandProperty Count"
    )
    if desconocidos and desconocidos.isdigit() and int(desconocidos) > 0:
        print(f"  Dispositivos con estado desconocido: {desconocidos}")

    degradados = get_powershell_output(
        "Get-PnpDevice | Where-Object {$_.Status -eq 'Degraded'} | "
        "Format-Table FriendlyName, Status, Class -AutoSize"
    )
    if degradados:
        print("  Dispositivos degradados:")
        print(degradados)
    print("=" * 50)


def monitor():
    print("\n" + "=" * 50)
    print("  INFORMACIÓN DE MONITOR / GPU")
    print("=" * 50)

    gpu = get_powershell_output(
        "Get-CimInstance Win32_VideoController | "
        "Format-Table Name, AdapterRAM, DriverVersion, Status, VideoProcessor -AutoSize"
    )
    if gpu:
        print(gpu)
    else:
        print("  No se detectó información de GPU.")

    try:
        gpu_info = get_powershell_output(
            "Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM, DriverVersion"
        )
        if gpu_info:
            for linea in gpu_info.splitlines():
                if "Name" in linea:
                    nombre = linea.split(":")[-1].strip()
                    print(f"  Tarjeta      : {nombre}")
                elif "AdapterRAM" in linea:
                    ram = linea.split(":")[-1].strip()
                    if ram.isdigit():
                        ram_gb = int(ram) / (1024 ** 3)
                        print(f"  VRAM         : {ram_gb:.2f} GB")
                elif "DriverVersion" in linea:
                    driver = linea.split(":")[-1].strip()
                    print(f"  Driver       : {driver}")
    except Exception:
        pass
    print("=" * 50)


def monitor_eos():
    print("\n" + "=" * 50)
    print("  MONITORIZACIÓN DE E/S (Entrada/Salida)")
    print("=" * 50)

    print("  Capturando datos de E/S (3 segundos)...")
    io_before = psutil.disk_io_counters()
    net_before = psutil.net_io_counters()
    time.sleep(3)
    io_after = psutil.disk_io_counters()
    net_after = psutil.net_io_counters()

    print(f"\n  Disco E/S (3s):")
    print(f"    Lecturas     : +{io_after.read_count - io_before.read_count}")
    print(f"    Escrituras   : +{io_after.write_count - io_before.write_count}")
    print(f"    Bytes leídos : +{(io_after.read_bytes - io_before.read_bytes) / 1024:.2f} KB")
    print(f"    Bytes escritos: +{(io_after.write_bytes - io_before.write_bytes) / 1024:.2f} KB")

    print(f"\n  Red E/S (3s):")
    print(f"    Enviados     : +{(net_after.bytes_sent - net_before.bytes_sent) / 1024:.2f} KB")
    print(f"    Recibidos    : +{(net_after.bytes_recv - net_before.bytes_recv) / 1024:.2f} KB")
    print(f"    Paq. enviados: +{net_after.packets_sent - net_before.packets_sent}")
    print(f"    Paq. recibidos: +{net_after.packets_recv - net_before.packets_recv}")

    print(f"\n  Periféricos de E/S:")
    print(f"    Teclado      : Detectado por SO")
    print(f"    Mouse        : Detectado por SO")
    print(f"    Monitor      : Consultar Win32_VideoController")
    print("=" * 50)


def generar_reporte():
    print("\n" + "=" * 50)
    print("  REPORTE DE DIAGNÓSTICO")
    print("=" * 50)

    cpu_pct = psutil.cpu_percent(interval=2)
    mem = psutil.virtual_memory()
    disk_root = psutil.disk_usage("C:\\")

    usb_problema = get_powershell_output(
        "Get-PnpDevice -PresentOnly | Where-Object {$_.InstanceId -like 'USB*' -and $_.Status -ne 'OK'} | "
        "Measure-Object | Select-Object -ExpandProperty Count"
    )
    usb_con_problema = int(usb_problema) if usb_problema.isdigit() else 0

    gpu_info = get_powershell_output(
        "Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion, Status"
    )
    gpu_ok = "OK" in gpu_info if gpu_info else True

    dispositivos_problema = get_powershell_output(
        "Get-PnpDevice | Where-Object {$_.Status -eq 'Error'} | "
        "Measure-Object | Select-Object -ExpandProperty Count"
    )
    n_problemas = int(dispositivos_problema) if dispositivos_problema.isdigit() else 0

    print(f"\n  {'Componente':<15} {'Evidencia':<20} {'Estado':<10} {'Posible problema'}")
    print(f"  {'-'*15} {'-'*20} {'-'*10} {'-'*30}")

    estado_cpu = "[!]" if cpu_pct > 70 else "OK"
    problema_cpu = "Carga elevada" if cpu_pct > 70 else "-"
    print(f"  {'CPU':<15} {cpu_pct:<20.1f}% {estado_cpu:<10} {problema_cpu}")

    estado_mem = "[!]" if mem.percent > 70 else "OK"
    problema_mem = "Poca memoria disponible" if mem.percent > 70 else "-"
    print(f"  {'RAM':<15} {mem.percent:<20.1f}% {estado_mem:<10} {problema_mem}")

    estado_disk = "[!]" if disk_root.percent > 85 else "OK"
    problema_disk = "Almacenamiento casi lleno" if disk_root.percent > 85 else "-"
    print(f"  {'SSD/HDD':<15} {disk_root.percent:<20.1f}% {estado_disk:<10} {problema_disk}")

    estado_usb = "[!]" if usb_con_problema > 0 else "OK"
    problema_usb = f"USB con errores ({usb_con_problema})" if usb_con_problema > 0 else "-"
    print(f"  {'USB':<15} {usb_con_problema:<20} {estado_usb:<10} {problema_usb}")

    estado_gpu = "[!]" if not gpu_ok else "OK"
    problema_gpu = "Driver antiguo/error" if not gpu_ok else "-"
    print(f"  {'GPU':<15} {'Verificar driver':<20} {estado_gpu:<10} {problema_gpu}")

    estado_disp = "[!]" if n_problemas > 0 else "OK"
    problema_disp = f"{n_problemas} dispositivos con fallas" if n_problemas > 0 else "-"
    print(f"  {'Dispositivos':<15} {n_problemas:<20} {estado_disp:<10} {problema_disp}")

    print(f"\n  {'='*50}")
    print(f"  DIAGNÓSTICO FINAL")
    print(f"  {'='*50}")

    problemas_encontrados = []
    if cpu_pct > 70:
        problemas_encontrados.append("CPU con carga elevada")
    if mem.percent > 70:
        problemas_encontrados.append("Memoria RAM casi agotada")
    if disk_root.percent > 85:
        problemas_encontrados.append("Disco casi lleno")
    if usb_con_problema > 0:
        problemas_encontrados.append(f"USB con errores ({usb_con_problema} dispositivos)")
    if not gpu_ok:
        problemas_encontrados.append("GPU con driver/problemático")
    if n_problemas > 0:
        problemas_encontrados.append(f"{n_problemas} dispositivos con problemas")

    if problemas_encontrados:
        print("\n  Causas mas probables:")
        for i, p in enumerate(problemas_encontrados, 1):
            print(f"    {i}. {p}")
        print("\n  Justificacion:")
        if mem.percent > 70:
            print("  -> La memoria RAM al estar casi llena obliga al sistema a usar")
            print("    el swap/paginacion, lo que ralentiza significativamente el equipo.")
        if cpu_pct > 70:
            print("  -> La CPU con alta carga impide que las aplicaciones se ejecuten")
            print("    de forma fluida, causando lentitud general.")
        if usb_con_problema > 0:
            print("  -> Los dispositivos USB con problemas pueden deberse a:")
            print("    controladores danados, conflicto de IRQ, o hardware defectuoso.")
        if not gpu_ok:
            print("  -> La GPU con problemas de driver afecta renderizado grafico")
            print("    y puede causar cai'das de rendimiento en aplicaciones visuales.")
    else:
        print("\n  [OK] No se encontraron problemas significativos.")
        print("       El sistema opera en condiciones normales.")

    print("\n" + "=" * 50)


def menu():
    while True:
        print("""
        ================================
        ADMINISTRADOR DE HARDWARE
        ================================

        1.  Sistema
        2.  CPU
        3.  Memoria
        4.  Discos
        5.  Red
        6.  USB
        7.  PCI/PCIe
        8.  Controladores
        9.  Problemas
        10. Monitor / GPU
        11. Monitorizar E/S
        12. Generar reporte
        0.  Salir
        """)

        opcion = input("Seleccione una opción: ")

        if opcion == "1":
            sistema()
        elif opcion == "2":
            cpu()
        elif opcion == "3":
            memoria()
        elif opcion == "4":
            discos()
        elif opcion == "5":
            red()
        elif opcion == "6":
            usb()
        elif opcion == "7":
            pci()
        elif opcion == "8":
            controladores()
        elif opcion == "9":
            problemas()
        elif opcion == "10":
            monitor()
        elif opcion == "11":
            monitor_eos()
        elif opcion == "12":
            generar_reporte()
        elif opcion == "0":
            print("\n  Programa finalizado.")
            break
        else:
            print("\n  Opción inválida. Intente de nuevo.")

        input("\n  Presione Enter para continuar...")


if __name__ == "__main__":
    menu()
