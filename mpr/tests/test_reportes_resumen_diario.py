"""Tests reporte_mpr_resumen_diario."""

from datetime import date
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mpr.services import reporte_mpr_resumen_diario


class TestReporteMprResumenDiario(SimpleTestCase):
    def test_base_vacia(self):
        r = reporte_mpr_resumen_diario("")
        self.assertEqual(r["kpis"]["enviado"], 0)
        self.assertEqual(r["dias"], [])

    @patch("mpr.services.mysql_cursor")
    def test_agrega_gap_envio_parte(self, mock_cursor_ctx):
        mock_cursor = MagicMock()
        mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.side_effect = [
            [{"d": date(2026, 7, 1), "total": 10}],
            [{"d": date(2026, 7, 1), "total": 0}],
            [],
        ]
        r = reporte_mpr_resumen_diario("empresa92", "2026-07-01", "2026-07-01")
        fila = next(x for x in r["dias"] if x["fecha"] == date(2026, 7, 1))
        self.assertEqual(fila["gap_envio_parte"], 10)
