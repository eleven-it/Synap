"""Tests reporte_mpr_operario_parte."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mpr.services import reporte_mpr_operario_parte


class TestReporteMprOperarioParte(SimpleTestCase):
    def test_vacio_sin_empresa(self):
        r = reporte_mpr_operario_parte("")
        self.assertEqual(r["filas"], [])

    @patch("mpr.services.mysql_cursor")
    def test_ranking_pct(self, mock_cursor_ctx):
        mock_cursor = MagicMock()
        mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [
            {"id_operario": 1, "operario_nombre": "Ana", "unidades": 60, "partes": 2, "componentes": 2},
            {"id_operario": 2, "operario_nombre": "Bob", "unidades": 40, "partes": 1, "componentes": 1},
        ]
        r = reporte_mpr_operario_parte("empresa92", "2026-07-01", "2026-07-07")
        self.assertEqual(len(r["filas"]), 2)
        self.assertEqual(r["filas"][0]["pct_total"], 60.0)
        self.assertEqual(r["kpis"]["unidades_total"], 100)
