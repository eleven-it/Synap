"""Tests del tablero KPI de control MPR (flujo diario)."""

from unittest.mock import patch

from django.test import SimpleTestCase

from mpr.presentacion_operativa import enriquecer_resumen_tablero_kpi_presentacion
from mpr.services import construir_resumen_tablero_kpi


class TestConstruirResumenTableroKpi(SimpleTestCase):
    """Resumen KPI sin dependencias OPT/OPP."""

    @patch("mpr.services._fetch_descripciones_articulo", return_value={99: ("PK-99", "Pack prueba"), 88: ("PK-88", "Otro")})
    @patch("mpr.services.listar_tablero_por_articulo")
    @patch("mpr.services.listar_demanda_pack_desde_pedidos")
    def test_agrega_kpis_desde_fuentes_diarias(self, mock_demanda, mock_tablero, _desc):
        mock_demanda.return_value = [
            {
                "id_articulo": 99,
                "cantidad_urgente_abs": 5,
                "cantidad_a_fabricar": 8,
                "stock_terminado": 2,
            },
            {"id_articulo": 88, "cantidad_urgente_abs": 0, "cantidad_a_fabricar": 3, "stock_terminado": 0},
        ]
        mock_tablero.return_value = [
            {
                "id_articulo": 10,
                "codigo_manual": "C-10",
                "descripcion_articulo": "Comp Diez",
                "resta_urgente": 20.0,
                "resta_urgente_ped": 15.0,
                "pendiente": 20.0,
                "enviado": 5.0,
                "total": 3.0,
            },
        ]
        res = construir_resumen_tablero_kpi("empresa_test")
        self.assertEqual(res["kpi_componentes_pendientes"], 1)
        self.assertEqual(res["kpi_pending_units"], 20)
        self.assertEqual(res["kpi_pending_units_ped"], 15)
        self.assertEqual(res["kpi_packs_demanda"], 2)
        self.assertEqual(res["kpi_urgent_items"], 1)
        self.assertEqual(len(res["componentes_pendientes"]), 1)
        self.assertEqual(res["componentes_pendientes"][0]["codigo"], "C-10")
        self.assertEqual(res["componentes_pendientes"][0]["resta_urgente"], 20)
        self.assertEqual(res["componentes_pendientes"][0]["resta_urgente_ped"], 15)
        self.assertEqual(len(res["top_packs_pendientes"]), 2)
        # Resta pack = Urgente (a_fabricar); PED resta = cantidad_urgente_abs
        self.assertEqual(res["top_packs_pendientes"][0]["resta_urgente"], 8)
        self.assertEqual(res["top_packs_pendientes"][0]["resta_urgente_ped"], 5)
        self.assertEqual(res["top_packs_pendientes"][0]["a_fabricar"], 8)

    def test_base_vacia_retorna_ceros(self):
        res = construir_resumen_tablero_kpi("")
        self.assertEqual(res["kpi_componentes_pendientes"], 0)
        self.assertEqual(res["kpi_pending_units_ped"], 0)
        self.assertEqual(res["componentes_pendientes"], [])


class TestPresentacionTableroKpi(SimpleTestCase):
    """Toggle Docenas|Pares en Tablero de control."""

    def test_enriquecer_docenas(self):
        resumen = {
            "kpi_pending_units": 240,
            "kpi_pending_units_ped": 120,
            "componentes_pendientes": [
                {
                    "codigo": "C-1",
                    "descripcion": "A",
                    "resta_urgente": 120,
                    "resta_urgente_ped": 96,
                    "fabricando": 24,
                },
            ],
            "top_packs_pendientes": [
                {
                    "codigo": "P-1",
                    "descripcion": "Pack",
                    "stock_terminado": 36,
                    "resta_urgente": 48,
                    "resta_urgente_ped": 24,
                    "a_fabricar": 60,
                },
            ],
        }
        out = enriquecer_resumen_tablero_kpi_presentacion(resumen, "docenas")
        self.assertEqual(out["unidad_cantidad_label"], "docenas")
        self.assertEqual(out["kpi_pending_units_display"], "20")
        self.assertEqual(out["kpi_pending_units_ped_display"], "10")
        self.assertEqual(out["componentes_pendientes"][0]["resta_urgente_display"], "10")
        self.assertEqual(out["componentes_pendientes"][0]["resta_urgente_ped_display"], "8")
        self.assertEqual(out["top_packs_pendientes"][0]["stock_terminado_display"], "3")
        self.assertEqual(out["top_packs_pendientes"][0]["resta_urgente_display"], "4")
        self.assertEqual(out["top_packs_pendientes"][0]["resta_urgente_ped_display"], "2")
        self.assertEqual(out["top_packs_pendientes"][0]["a_fabricar_display"], "5")
        # Crudos en pares se conservan
        self.assertEqual(out["kpi_pending_units"], 240)

    def test_enriquecer_pares(self):
        resumen = {
            "kpi_pending_units": 20,
            "kpi_pending_units_ped": 12,
            "componentes_pendientes": [
                {
                    "codigo": "C-1",
                    "descripcion": "A",
                    "resta_urgente": 20,
                    "resta_urgente_ped": 12,
                    "fabricando": 0,
                },
            ],
            "top_packs_pendientes": [],
        }
        out = enriquecer_resumen_tablero_kpi_presentacion(resumen, "unidades")
        self.assertEqual(out["unidad_cantidad_label"], "pares")
        self.assertEqual(out["kpi_pending_units_display"], "20")
        self.assertEqual(out["kpi_pending_units_ped_display"], "12")
        self.assertEqual(out["componentes_pendientes"][0]["resta_urgente_display"], "20")
        self.assertEqual(out["componentes_pendientes"][0]["resta_urgente_ped_display"], "12")

    def test_display_con_separador_miles_sin_decimales(self):
        resumen = {
            "kpi_pending_units": 433706,
            "kpi_pending_units_ped": 400001,
            "componentes_pendientes": [
                {
                    "codigo": "C-1",
                    "descripcion": "A",
                    "resta_urgente": 24466,
                    "resta_urgente_ped": 20001,
                    "fabricando": 0,
                },
            ],
            "top_packs_pendientes": [
                {
                    "codigo": "P-1",
                    "descripcion": "Pack",
                    "stock_terminado": 3474,
                    "resta_urgente": 6576,
                    "resta_urgente_ped": 0,
                    "a_fabricar": 6576,
                },
            ],
        }
        out = enriquecer_resumen_tablero_kpi_presentacion(resumen, "unidades")
        self.assertEqual(out["kpi_pending_units_display"], "433.706")
        self.assertEqual(out["kpi_pending_units_ped_display"], "400.001")
        self.assertEqual(out["componentes_pendientes"][0]["resta_urgente_display"], "24.466")
        self.assertEqual(out["componentes_pendientes"][0]["resta_urgente_ped_display"], "20.001")
        self.assertEqual(out["top_packs_pendientes"][0]["stock_terminado_display"], "3.474")
        self.assertEqual(out["top_packs_pendientes"][0]["a_fabricar_display"], "6.576")
        self.assertNotIn(",", out["kpi_pending_units_display"])
        self.assertNotIn(",", out["componentes_pendientes"][0]["resta_urgente_display"])
