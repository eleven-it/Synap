"""Código visual MPR: articulo.id_manual, no CodigoArticuloT."""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mpr.services import _fetch_descripciones_articulo, bulk_codigo_manual_articulo


class TestCodigoManualUi(SimpleTestCase):
    @patch("mpr.services.mysql_cursor")
    @patch("mpr.services._nombre_tabla", return_value="articulo")
    def test_fetch_descripciones_usa_id_manual(self, _tbl, mock_cursor_ctx):
        cursor = MagicMock()
        mock_cursor_ctx.return_value.__enter__.return_value = cursor
        cursor.fetchall.return_value = [
            {
                "id_articulo": 813,
                "codigo_manual": " 2.4.100 ",
                "descripcion": "Puma Sneakers",
            }
        ]
        result = _fetch_descripciones_articulo("empresa_test", [813])
        sql = cursor.execute.call_args[0][0]
        self.assertIn("id_manual", sql)
        self.assertNotIn("CodigoArticuloT", sql)
        self.assertEqual(result[813][0], "2.4.100")
        self.assertEqual(result[813][1], "Puma Sneakers")

    @patch("mpr.services.mysql_cursor")
    @patch("mpr.services._nombre_tabla", return_value="articulo")
    def test_bulk_codigo_manual_vacio_es_guion(self, _tbl, mock_cursor_ctx):
        cursor = MagicMock()
        mock_cursor_ctx.return_value.__enter__.return_value = cursor
        cursor.fetchall.return_value = [{"id_articulo": 1, "codigo_manual": ""}]
        result = bulk_codigo_manual_articulo("empresa_test", [1])
        self.assertEqual(result[1], "-")
