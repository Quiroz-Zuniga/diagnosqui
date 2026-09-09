"""
Matriz de correlación de diagnóstico y motor de veredicto automático.
Usa el CONTRATO UNIFICADO de la capa de recolección (core/*).
"""
from typing import Any, Dict, List
from diagnosqui.core.cpu import recolectar_cpu
from diagnosqui.core.memoria import recolectar_memoria
from diagnosqui.core.discos import recolectar_discos
from diagnosqui.core.usb import recolectar_usb
from diagnosqui.core.monitor import recolectar_gpu
from diagnosqui.core.problemas import recolectar_problemas


def build_diagnostic_matrix() -> List[Dict[str, Any]]:
    """Recolecta métricas de todos los subsistemas y construye la matriz de diagnóstico."""
    cpu_data = recolectar_cpu()
    mem_data = recolectar_memoria()
    disk_data = recolectar_discos()
    usb_data = recolectar_usb()
    gpu_data = recolectar_gpu()
    prob_data = recolectar_problemas()

    matrix = []

    # Mapear estados del contrato unificado a los estados de la matriz
    # Contrato: "NORMAL", "ADVERTENCIA", "CRITICO"
    # Matriz: "OK", "ALERTA", "CRITICO"
    def map_estado(estado_contrato: str) -> str:
        mapping = {
            "NORMAL": "OK",
            "ADVERTENCIA": "ALERTA",
            "CRITICO": "CRITICO"
        }
        return mapping.get(estado_contrato, "OK")

    # 1. CPU
    cpu_pct = cpu_data.get("valor_numerico", 0)
    cpu_estado = map_estado(cpu_data.get("estado", "NORMAL"))
    c_prob = cpu_data.get("recomendacion", ["—"])[0] if cpu_data.get("recomendacion") else "—"
    matrix.append({
        "componente": "CPU",
        "evidencia": cpu_data.get("evidencia", f"{cpu_pct:.1f}% uso"),
        "estado": cpu_estado,
        "problema": c_prob,
        "raw_val": cpu_pct
    })

    # 2. RAM
    mem_pct = mem_data.get("valor_numerico", 0)
    mem_estado = map_estado(mem_data.get("estado", "NORMAL"))
    m_prob = mem_data.get("recomendacion", ["—"])[0] if mem_data.get("recomendacion") else "—"
    matrix.append({
        "componente": "RAM",
        "evidencia": mem_data.get("evidencia", f"{mem_pct:.1f}%"),
        "estado": mem_estado,
        "problema": m_prob,
        "raw_val": mem_pct
    })

    # 3. SSD / HDD
    disk_pct = disk_data.get("valor_numerico", 0)
    disk_estado = map_estado(disk_data.get("estado", "NORMAL"))
    d_prob = disk_data.get("recomendacion", ["—"])[0] if disk_data.get("recomendacion") else "—"
    matrix.append({
        "componente": "SSD/HDD",
        "evidencia": disk_data.get("evidencia", "N/D"),
        "estado": disk_estado,
        "problema": d_prob,
        "raw_val": disk_pct
    })

    # 4. USB
    usb_probs = int(usb_data.get("valor_numerico", 0))
    usb_estado = map_estado(usb_data.get("estado", "NORMAL"))
    u_prob = usb_data.get("recomendacion", ["—"])[0] if usb_data.get("recomendacion") else "—"
    matrix.append({
        "componente": "USB",
        "evidencia": usb_data.get("evidencia", "N/D"),
        "estado": usb_estado,
        "problema": u_prob,
        "raw_val": usb_probs
    })

    # 5. GPU
    gpu_val = gpu_data.get("valor_numerico", 0)
    gpu_estado = map_estado(gpu_data.get("estado", "NORMAL"))
    g_prob = gpu_data.get("recomendacion", ["—"])[0] if gpu_data.get("recomendacion") else "—"
    matrix.append({
        "componente": "GPU",
        "evidencia": gpu_data.get("evidencia", "N/D"),
        "estado": gpu_estado,
        "problema": g_prob,
        "raw_val": gpu_val
    })

    # 6. Dispositivos del Sistema (PnP)
    prob_val = prob_data.get("valor_numerico", 0)
    prob_estado = map_estado(prob_data.get("estado", "NORMAL"))
    p_prob = prob_data.get("recomendacion", ["—"])[0] if prob_data.get("recomendacion") else "—"
    matrix.append({
        "componente": "Dispositivos PnP",
        "evidencia": prob_data.get("evidencia", "N/D"),
        "estado": prob_estado,
        "problema": p_prob,
        "raw_val": prob_val
    })

    return matrix


def diagnostico_final(matrix: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analiza la matriz y elabora un veredicto estructurado.
    Detecta automáticamente casos típicos como:
    - CPU/RAM alta + USB fallando + GPU degradada (caso del reto).
    """
    row_map = {row["componente"]: row for row in matrix}

    # Ahora los estados son "OK", "ALERTA", "CRITICO"
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