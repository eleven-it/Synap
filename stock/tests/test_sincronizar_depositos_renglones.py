"""Tests: sincronizar depósitos de renglones temporales al cambiar cabecera."""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from core.services.administranet_stock import sincronizar_depositos_renglones_temporales


class TestSincronizarDepositosRenglonesTemporales(SimpleTestCase):
    """REQ: al cambiar depósito de cabecera se actualizan CodDeposito de los temporales."""

    @patch("core.services.administranet_stock.mysql_cursor")
    def test_actualiza_cod_deposito_y_limpia_lotes(self, mock_cursor_cm):
        cursor = MagicMock()
        cursor.rowcount = 2
        mock_cursor_cm.return_value.__enter__.return_value = cursor

        err, afectadas = sincronizar_depositos_renglones_temporales(
            "administranet",
            12,
            6,
            None,
            limpiar_lotes=True,
        )

        self.assertIsNone(err)
        self.assertEqual(afectadas, 2)
        cursor.execute.assert_called_once()
        sql, params = cursor.execute.call_args[0]
        self.assertIn("CodDeposito = %s", sql)
        self.assertIn("id_lote = NULL", sql)
        self.assertEqual(params[0], 6)
        self.assertIsNone(params[1])
        self.assertEqual(params[2], 12)

    @patch("core.services.administranet_stock.mysql_cursor")
    def test_con_destino_transferencia(self, mock_cursor_cm):
        cursor = MagicMock()
        cursor.rowcount = 1
        mock_cursor_cm.return_value.__enter__.return_value = cursor

        err, afectadas = sincronizar_depositos_renglones_temporales(
            "administranet",
            5,
            1,
            6,
            limpiar_lotes=False,
        )

        self.assertIsNone(err)
        self.assertEqual(afectadas, 1)
        sql, params = cursor.execute.call_args[0]
        self.assertNotIn("id_lote = NULL", sql)
        self.assertEqual(list(params), [1, 6, 5])

    def test_sin_deposito_origen_error(self):
        err, afectadas = sincronizar_depositos_renglones_temporales(
            "administranet",
            12,
            None,
        )
        self.assertIsNotNone(err)
        self.assertIn("Depósito origen", err.get("error", ""))
        self.assertEqual(afectadas, 0)
