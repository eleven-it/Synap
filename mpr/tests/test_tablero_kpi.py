"""Tests del tablero KPI de control MPR (flujo diario)."""

from unittest.mock import patch

from django.test import SimpleTestCase

from mpr.services import construir_resumen_tablero_kpi


class TestConstruirResumenTableroKpi(SimpleTestCase):
    """Resumen KPI sin dependencias OPT/OPP."""

    @patch("mpr.services.listar_tablero_por_articulo")
    @patch("mpr.services.listar_demanda_pack_desde_pedidos")
    def test_agrega_kpis_desde_fuentes_diarias(self, mock_demanda, mock_tablero):
        mock_demanda.return_value = [
            {"cantidad_urgente_abs": 5},
            {"cantidad_urgente_abs": 0},
        ]
        mock_tablero.return_value = [
            {
                "id_articulo": 10,
                "codigo_manual": "C-10",
                "descripcion_articulo": "Comp Diez",
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
        self.assertEqual(len(res["top_urgencias"]), 1)
        self.assertEqual(res["top_urgencias"][0]["demand"], 20)

    def test_base_vacia_retorna_ceros(self):
        res = construir_resumen_tablero_kpi("")
        self.assertEqual(res["kpi_componentes_pendientes"], 0)
        self.assertEqual(res["componentes_pendientes"], [])
