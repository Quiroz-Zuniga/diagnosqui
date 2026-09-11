"""
Casos integradores del enunciado y cobertura del motor de reglas.

Los cinco casos del plan resuelven mediante contratos sintéticos (no
consultan hardware) para mantener determinismo y ejecutarse en cualquier SO.
"""
from __future__ import annotations

import unittest

from diagnosqui.analisis.reglas import (
    ADVERTENCIA,
    CRITICO,
    NORMAL,
    analizar_estado,
    clasificar_pnp,
    estado_mas_severo,
    traducir_estado,
)
from diagnosqui.analisis.recomendaciones import (
    analizar_contrato,
    recomendacion_conectividad,
    recomendacion_pci,
    recomendacion_usb,
)


def contrato(componente, evidencia, valor, estado=NORMAL, detalle=None, recomendacion=None):
    return {
        "componente": componente,
        "evidencia": evidencia,
        "valor_numerico": valor,
        "estado": estado,
        "detalle": detalle or {},
        "recomendacion": recomendacion or [],
    }


class TestReglas(unittest.TestCase):
    def test_umbrales_porcentaje_en_los_límites(self):
        self.assertEqual(analizar_estado(0), NORMAL)
        self.assertEqual(analizar_estado(69.99), NORMAL)
        self.assertEqual(analizar_estado(70), ADVERTENCIA)
        self.assertEqual(analizar_estado(89.99), ADVERTENCIA)
        self.assertEqual(analizar_estado(90), CRITICO)
        self.assertEqual(analizar_estado(100), CRITICO)

    def test_regla_pnp_windows(self):
        self.assertEqual(clasificar_pnp("OK"), NORMAL)
        self.assertEqual(clasificar_pnp("Warning"), ADVERTENCIA)
        self.assertEqual(clasificar_pnp("Unknown"), ADVERTENCIA)
        self.assertEqual(clasificar_pnp("Error"), CRITICO)
        self.assertEqual(clasificar_pnp("Degraded"), ADVERTENCIA)
        self.assertEqual(clasificar_pnp(""), ADVERTENCIA)

    def test_estado_mas_severo_prioriza_critico(self):
        self.assertEqual(estado_mas_severo([NORMAL, ADVERTENCIA]), ADVERTENCIA)
        self.assertEqual(estado_mas_severo([NORMAL, ADVERTENCIA, CRITICO]), CRITICO)

    def test_traducir_estado_normaliza_alias(self):
        self.assertEqual(traducir_estado("OK"), NORMAL)
        self.assertEqual(traducir_estado("ALERTA"), ADVERTENCIA)
        self.assertEqual(traducir_estado("ERROR"), CRITICO)
        self.assertEqual(traducir_estado(""), ADVERTENCIA)

    def test_valores_invalidos_no_producen_critico_inventado(self):
        self.assertIn(analizar_estado(None), (NORMAL, ADVERTENCIA))


class TestCasosIntegradores(unittest.TestCase):

    def test_caso1_sin_red_dhcp_apipa(self):
        # Entrada: IP 169.254.x.x, gateway no disponible.
        red = contrato(
            "Red",
            "Dirección APIPA",
            0,
            detalle={"apipa_detectada": True, "interfaces": [{"ipv4": ["169.254.10.5"]}]},
        )
        result = analizar_contrato(red)
        self.assertEqual(result["estado"], CRITICO)
        self.assertEqual(result["detalle"]["certeza"], "alta")
        sugerencia = " ".join(result["recomendacion"])
        self.assertIn("ipconfig /release", sugerencia)
        self.assertIn("renew", sugerencia)

    def test_caso2_pcie_tarjeta_de_red_aisla_falla(self):
        # Entrada: adaptador PCIe en ERROR, resto OK.
        nic = contrato(
            "PCI / PCIe",
            "5 dispositivos, 1 con error",
            5,
            detalle={
                "dispositivos": [
                    {"FriendlyName": "Puente", "Status": "OK"},
                    {"FriendlyName": "Adaptador Gigabit", "Status": "OK"},
                    {"FriendlyName": "Tarjeta de red PCIe", "Status": "Error"},
                    {"FriendlyName": "SATA", "Status": "OK"},
                ]
            },
        )
        result = analizar_contrato(nic)
        self.assertEqual(result["estado"], CRITICO)
        self.assertEqual(result["detalle"]["certeza"], "alta")
        self.assertIn("1", result["detalle"]["deteccion"])
        self.assertIn("aisló la falla", result["detalle"]["diagnostico"])
        self.assertNotIn("sistema en general", result["detalle"]["diagnostico"].lower().replace(
            "no al sistema en general", ""))

        pars = recomendacion_pci(nic)
        self.assertEqual(pars["recomendacion"][0], "Verificar físicamente el componente de bus PCI.")

    def test_caso3_usb_no_reconocido_arbol_de_decision(self):
        # Entrada: controlador OK, dispositivo ERROR, unidad no aparece.
        usb = contrato(
            "USB",
            "1 dispositivo con problema",
            1,
            detalle={
                "problemas": [{"FriendlyName": "Disco externo", "Status": "Error", "Problem": "Code 43"}],
            },
        )
        result = analizar_contrato(usb)
        self.assertEqual(result["estado"], CRITICO)
        self.assertEqual(result["detalle"]["certeza"], "alta")
        sugerencia = " ".join(result["recomendacion"])
        self.assertIn("puerto", sugerencia)
        self.assertIn("cable", sugerencia)

        recomendacion_usb(usb)

    def test_caso4_alto_consumo_cpu_ram(self):
        from diagnosqui.analisis.general import diagnostico_semaforo

        cpu = contrato("CPU", "97% de uso", 97.0)
        ram = contrato("Memoria RAM", "91% utilizado", 91.0)
        semaforo = diagnostico_semaforo([cpu, ram], sintoma="El equipo va lento")

        self.assertEqual(semaforo["estado"], CRITICO)
        self.assertEqual(len(semaforo["errores_detectados"]), 2)
        self.assertIn("procesos", " ".join(semaforo["recomendaciones"]))

    def test_caso5_ambiguo_indicadores_ok_con_sintoma(self):
        from diagnosqui.analisis.general import diagnostico_semaforo

        cpu = contrato("CPU", "12% de uso", 12.0)
        ram = contrato("Memoria RAM", "30% utilizado", 30.0)
        semaforo = diagnostico_semaforo([cpu, ram], sintoma="Se reinicia solo")

        self.assertEqual(semaforo["estado"], NORMAL)
        self.assertTrue(semaforo["requiere_diagnostico_adicional"])
        self.assertEqual(semaforo["certeza"], "baja")
        self.assertNotIn(
            "parámetros normales",
            semaforo["resultado_final"],
        )
        self.assertIn("diagnóstico adicional", semaforo["resultado_final"])
        self.assertTrue(
            any("eventos del sistema" in rec for rec in semaforo["recomendaciones"])
        )

    def test_caso5_sin_sintoma_declara_normal_con_criterio(self):
        from diagnosqui.analisis.general import diagnostico_semaforo

        cpu = contrato("CPU", "12% de uso", 12.0)
        semaforo = diagnostico_semaforo([cpu])
        self.assertEqual(semaforo["estado"], NORMAL)
        self.assertFalse(semaforo["requiere_diagnostico_adicional"])


class TestMotorRecalculaContratos(unittest.TestCase):
    def test_analizar_contrato_conserva_las_seis_claves(self):
        contrato_cpu = contrato("CPU", "42%", 42.0)
        result = analizar_contrato(contrato_cpu)
        self.assertEqual(
            set(result),
            {"componente", "evidencia", "valor_numerico", "estado", "detalle", "recomendacion"},
        )
        self.assertEqual(result["estado"], NORMAL)
        self.assertEqual(result["detalle"]["certeza"], "media")
        self.assertTrue(result["recomendacion"])

    def test_memoria_en_advertencia_y_cpu_normal(self):
        memoria = contrato("Memoria RAM", "76% utilizado", 76.0)
        self.assertEqual(analizar_contrato(memoria)["estado"], ADVERTENCIA)

    def test_conectividad_fallida_devuelve_recomendaciones(self):
        conectividad = contrato(
            "Conectividad",
            "1/3 comprobaciones exitosas",
            1,
            detalle={"gateway_ok": False, "internet_ok": True, "dns_ok": False},
        )
        result = analizar_contrato(conectividad)
        self.assertEqual(result["estado"], CRITICO)
        self.assertEqual(result["detalle"]["certeza"], "alta")
        llamada = recomendacion_conectividad(conectividad)
        self.assertIn("Gateway", llamada["diagnostico"])
        self.assertIn("DNS", llamada["diagnostico"])


if __name__ == "__main__":
    unittest.main()