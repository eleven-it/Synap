"""La excepción fiscal toma la categoría vigente de contribuyentes."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from ecom.services.cliente_iva_pedido import es_cliente_iva_no_responsable


class TestClienteIvaPedido(SimpleTestCase):
    @patch("ecom.services.cliente_iva_pedido.get_connection")
    def test_categoria_9_es_no_responsable(self, mock_connection):
        cursor = MagicMock()
        cursor.fetchone.return_value = (9,)
        mock_connection.return_value.__enter__.return_value.cursor.return_value = cursor

        self.assertTrue(es_cliente_iva_no_responsable("empresa", 25))
        sql, params = cursor.execute.call_args.args
        self.assertIn("INNER JOIN contribuyentes", sql)
        self.assertEqual(params, [25])

    @patch("ecom.services.cliente_iva_pedido.get_connection")
    def test_otra_categoria_conserva_iva_del_articulo(self, mock_connection):
        cursor = MagicMock()
        cursor.fetchone.return_value = (1,)
        mock_connection.return_value.__enter__.return_value.cursor.return_value = cursor

        self.assertFalse(es_cliente_iva_no_responsable("empresa", 25))
