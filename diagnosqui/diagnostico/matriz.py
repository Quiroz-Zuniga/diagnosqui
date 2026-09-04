"""
Matriz de correlación de diagnóstico y motor de veredicto automático.
"""
from typing import Any, Dict, List
from diagnosqui.backends.base import BaseBackend


def build_diagnostic_matrix(backend: BaseBackend) -> List[Dict[str, Any]]:
    """Recolecta métricas de todos los subsistemas y construye la matriz de diagnóstico."""
    cpu_data = backend.get_cpu_info()
    mem_data = backend.get_memory_info()
    disk_data = backend.get_disks_info()
    usb_data = backend.get_usb_devices()
    gpu_data = backend.get_gpu_info()
    prob_data = backend.get_problem_devices()

    matrix = []

    # 1. CPU
    cpu_pct = cpu_data["total_percent"]
    if cpu_pct > 85:
        c_state, c_prob = "CRITICO", "Carga extrema / Proceso bloqueante"
    elif cpu_pct > 70:
        c_state, c_prob = "ALERTA", "Carga elevada"
    else:
        c_state, c_prob = "OK", "—"
    matrix.append({
        "componente": "CPU",
        "evidencia": f"{cpu_pct:.1f}% uso",
        "estado": c_state,
        "problema": c_prob,
        "raw_val": cpu_pct
    })

    # 2. RAM
    mem_pct = mem_data["percent"]
    if mem_pct > 85:
        m_state, m_prob = "CRITICO", "Memoria RAM casi agotada / Paginación severa"
    elif mem_pct > 70:
        m_state, m_prob = "ALERTA", "Poca memoria disponible"
    else:
        m_state, m_prob = "OK", "—"
    matrix.append({
        "componente": "RAM",
        "evidencia": f"{mem_pct:.1f}% ({mem_data['used_gb']:.1f}/{mem_data['total_gb']:.1f} GB)",
        "estado": m_state,
        "problema": m_prob,
        "raw_val": mem_pct
    })

    # 3. SSD / HDD
    max_disk_pct = 0.0
    disk_desc = "Sin unidades montadas"
    for p in disk_data["partitions"]:
        if "percent" in p and p["percent"] > max_disk_pct:
            max_disk_pct = p["percent"]
            disk_desc = f"{p['device']} al {p['percent']:.1f}%"

    if max_disk_pct > 90:
        d_state, d_prob = "CRITICO", "Almacenamiento crítico / Sin espacio para swap"
    elif max_disk_pct > 80:
        d_state, d_prob = "ALERTA", "Almacenamiento casi lleno"
    else:
        d_state, d_prob = "OK", "—"
    matrix.append({
        "componente": "SSD/HDD",
        "evidencia": disk_desc,
        "estado": d_state,
        "problema": d_prob,
        "raw_val": max_disk_pct
    })

    # 4. USB
    usb_probs = usb_data["problem_count"]
    if usb_probs > 0:
        u_state = "CRITICO" if usb_probs > 2 else "ALERTA"
        u_prob = f"Driver incompatible o conflicto de bus ({usb_probs} dispositivo(s))"
        u_evid = f"{usb_probs} fallo(s) detectado(s)"
    else:
        u_state, u_prob, u_evid = "OK", "—", f"{usb_data['total_count']} dispositivos OK"
    matrix.append({
        "componente": "USB",
        "evidencia": u_evid,
        "estado": u_state,
        "problema": u_prob,
        "raw_val": usb_probs
    })

    # 5. GPU
    gpus = gpu_data["gpus"]
    gpu_healthy = gpu_data["is_healthy"]
    if not gpus:
        g_state, g_prob, g_evid = "ALERTA", "Sin driver o GPU no reconocida", "No detectada"
    elif not gpu_healthy:
        g_state, g_prob, g_evid = "ALERTA", "Controlador con error o estado anómalo", gpus[0].get("name", "GPU")
    else:
        gpu_name = gpus[0]["name"] if gpus else "GPU"
        g_state, g_prob, g_evid = "OK", "—", f"{gpu_name} (Driver OK)"
    matrix.append({
        "componente": "GPU",
        "evidencia": g_evid,
        "estado": g_state,
        "problema": g_prob,
        "raw_val": 0 if gpu_healthy else 1
    })

    # 6. Dispositivos del Sistema (PnP)
    total_probs = prob_data["total_problematic"]
    if total_probs > 0:
        p_state = "CRITICO" if total_probs > 2 else "ALERTA"
        p_prob = f"{total_probs} dispositivo(s) con errores/desconocidos"
        p_evid = f"{total_probs} anomalía(s)"
    else:
        p_state, p_prob, p_evid = "OK", "—", "Árbol de hardware limpio"
    matrix.append({
        "componente": "Dispositivos PnP",
        "evidencia": p_evid,
        "estado": p_state,
        "problema": p_prob,
        "raw_val": total_probs
    })

    return matrix


def diagnostico_final(matrix: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analiza la matriz y elabora un veredicto estructurado.
    Detecta automáticamente casos típicos como:
    - CPU/RAM alta + USB fallando + GPU degradada (caso del reto).
    """
    row_map = {row["componente"]: row for row in matrix}

    cpu_alert = row_map["CPU"]["estado"] != "OK"
    ram_alert = row_map["RAM"]["estado"] != "OK"
    disk_alert = row_map["SSD/HDD"]["estado"] != "OK"
    usb_alert = row_map["USB"]["estado"] != "OK"
    gpu_alert = row_map["GPU"]["estado"] != "OK"
    pnp_alert = row_map["Dispositivos PnP"]["estado"] != "OK"

    causas = []
    justificaciones = []
    recomendaciones = []

    # Diagnóstico cruzado específico del reto: Sistema lento + USB fallando + GPU problemática
    if (cpu_alert or ram_alert) and usb_alert and gpu_alert:
        causas.append("Degradación combinada de controladores (Chipset/GPU) e interrupciones (IRQ) en buses.")
        justificaciones.append(
            "Se detecta concurrencia de alta latencia de procesamiento con errores en periféricos USB y subsistema gráfico. "
            "Esto suele deberse a controladores de chipset obsoletos que generan conflictos de asignación de recursos o fallas de bus."
        )
        recomendaciones.append("Reinstalar el paquete de controladores del chipset de la placa base y actualizar controladores gráficos oficiales.")

    if cpu_alert:
        causas.append("Saturación de ciclos de reloj en CPU.")
        justificaciones.append(
            f"El procesador opera al {row_map['CPU']['evidencia']}. Los hilos de ejecución están saturados, "
            "lo que retarda la respuesta a eventos de E/S y la interacción general de la interfaz de usuario."
        )
        recomendaciones.append("Identificar procesos en segundo plano con alto consumo de CPU mediante el administrador de tareas/top.")

    if ram_alert:
        causas.append("Presión crítica en la memoria física (RAM).")
        justificaciones.append(
            f"La memoria RAM reporta {row_map['RAM']['evidencia']}. Cuando la RAM supera el 75-80%, el sistema operativo "
            "recurre al swap o archivo de paginación en disco, cuya velocidad es órdenes de magnitud inferior a la RAM física."
        )
        recomendaciones.append("Cerrar aplicaciones con fuga de memoria o ampliar la capacidad física de RAM.")

    if disk_alert:
        causas.append("Almacenamiento secundario al límite de capacidad.")
        justificaciones.append(
            f"Unidad en {row_map['SSD/HDD']['evidencia']}. La falta de espacio libre impide la creación de archivos temporales "
            "y la expansión dinámica del archivo de intercambio (pagefile.sys / swap)."
        )
        recomendaciones.append("Liberar espacio en la partición raíz o desfragmentar/optimizar la unidad SSD.")

    if usb_alert:
        causas.append("Fallas de señalización o descriptor en el bus USB.")
        justificaciones.append(
            f"Se detectaron dispositivos USB no operativos ({row_map['USB']['evidencia']}). "
            "Las causas típicas comprenden puertos con alimentación insuficiente, daño de cableado o drivers corruptos."
        )
        recomendaciones.append("Reubicar el periférico a otro puerto raíz (directo a la placa base) y actualizar controladores de bus USB.")

    if gpu_alert:
        causas.append("Controlador de pantalla desactualizado o driver genérico.")
        justificaciones.append(
            f"El adaptador de video ({row_map['GPU']['evidencia']}) no presenta una configuración óptima. "
            "Esto provoca que la aceleración 2D/3D sea emulada por CPU (software rendering), aumentando la lentitud."
        )
        recomendaciones.append("Descargar el controlador WHQL más reciente del fabricante de la GPU (NVIDIA, AMD o Intel).")

    if pnp_alert and not usb_alert:
        causas.append("Dispositivos no reconocidos en el bus del sistema.")
        justificaciones.append(
            f"Existen dispositivos PnP con error ({row_map['Dispositivos PnP']['evidencia']}) pendientes de asignación de driver."
        )
        recomendaciones.append("Verificar el Administrador de dispositivos para instalar los drivers faltantes.")

    is_healthy = len(causas) == 0

    return {
        "is_healthy": is_healthy,
        "causas": causas if causas else ["El sistema se encuentra operando dentro de los parámetros normales de funcionamiento."],
        "justificaciones": justificaciones if justificaciones else ["No se encontraron anomalías significativas en los subsistemas analizados."],
        "recomendaciones": recomendaciones if recomendaciones else ["Mantener actualizados los controladores y monitorear periódicamente."],
    }
