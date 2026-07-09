"""Tests del tablero KPI de control MPR (flujo diario)."""

from unittest.mock import patch

from django.test import SimpleTestCase

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
                "pendiente": 20.0,
                "enviado": 5.0,
                "total": 3.0,
            },
        ]
        res = construir_resumen_tablero_kpi("empresa_test")
        self.assertEqual(res["kpi_componentes_pendientes"], 1)
        self.assertEqual(res["kpi_pending_units"], 20)
        self.assertEqual(res["kpi_packs_demanda"], 2)
        self.assertEqual(res["kpi_urgent_items"], 1)
        self.assertEqual(len(res["componentes_pendientes"]), 1)
        self.assertEqual(res["componentes_pendientes"][0]["codigo"], "C-10")
        self.assertEqual(res["componentes_pendientes"][0]["resta_urgente"], 20)
        self.assertEqual(len(res["top_packs_pendientes"]), 2)
        self.assertEqual(res["top_packs_pendientes"][0]["resta_urgente"], 5)
        self.assertEqual(res["top_packs_pendientes"][0]["a_fabricar"], 8)

    def test_base_vacia_retorna_ceros(self):
        res = construir_resumen_tablero_kpi("")
        self.assertEqual(res["kpi_componentes_pendientes"], 0)
        self.assertEqual(res["componentes_pendientes"], [])
