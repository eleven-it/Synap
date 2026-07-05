"""Tests reporte_mpr_cadena_pipeline."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mpr.services import reporte_mpr_cadena_pipeline


class TestReporteMprCadenaPipeline(SimpleTestCase):
    @patch("mpr.services._fetch_descripciones_articulo")
    @patch("mpr.services.mysql_cursor")
    def test_estado_falta_parte(self, mock_cursor_ctx, mock_desc):
        mock_desc.return_value = {42: ("C-42", "Comp demo")}
        mock_cursor = MagicMock()
        mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.side_effect = [
            [{"id_articulo": 42, "total": 20}],
            [],
            [],
        ]
        r = reporte_mpr_cadena_pipeline("empresa92", "2026-07-01", "2026-07-07")
        self.assertEqual(r["filas"][0]["estado"], "falta_parte")
        self.assertEqual(r["kpis"]["componentes_gap"], 1)
