"""Tests reconstrucción stock a fecha (tabla legacy stock)."""
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase


class SaldosStockAFechaTest(SimpleTestCase):
    """REQ-INVDEP-07 / design stock_a_fecha: SUM(Entrada-Salida), corte inclusive, Anulado."""

    @patch("stock.services.stock_a_fecha.mysql_cursor")
    def test_suma_entradas_menos_salidas_hasta_corte(self, mock_cursor):
        from stock.services.stock_a_fecha import saldos_stock_a_fecha

        cursor = MagicMock()
        mock_cursor.return_value.__enter__.return_value = cursor
        cursor.fetchone.return_value = {"Tables_in_x": "stock"}
        cursor.fetchall.return_value = [
            {"IDArt": 10, "CodDeposito": 3, "saldo": Decimal("7")},
            {"IDArt": 20, "CodDeposito": 4, "saldo": Decimal("5")},
        ]

        with patch("stock.services.stock_a_fecha._nombre_tabla", return_value="stock"):
            resultado = saldos_stock_a_fecha("empresa92", date(2025, 6, 15))

        self.assertEqual(resultado[(10, 3)], Decimal("7"))
        self.assertEqual(resultado[(20, 4)], Decimal("5"))
        sql = cursor.execute.call_args[0][0]
        self.assertIn("DATE(", sql)
        self.assertIn("Fecha", sql)
        params = cursor.execute.call_args[0][1]
        self.assertEqual(params[0], "2025-06-15")

    @patch("stock.services.stock_a_fecha.mysql_cursor")
    def test_excluye_anulado_si(self, mock_cursor):
        from stock.services.stock_a_fecha import saldos_stock_a_fecha

        cursor = MagicMock()
        mock_cursor.return_value.__enter__.return_value = cursor
        cursor.fetchone.return_value = {"Tables_in_x": "stock"}
        cursor.fetchall.return_value = []

        with patch("stock.services.stock_a_fecha._nombre_tabla", return_value="stock"):
            saldos_stock_a_fecha("empresa92", date(2025, 1, 1))

        sql = cursor.execute.call_args[0][0]
        self.assertIn("Anulado", sql)
        self.assertIn("'Si'", sql)

    @patch("stock.services.stock_a_fecha.mysql_cursor")
    def test_filtro_depositos_opcional(self, mock_cursor):
        from stock.services.stock_a_fecha import saldos_stock_a_fecha

        cursor = MagicMock()
        mock_cursor.return_value.__enter__.return_value = cursor
        cursor.fetchone.return_value = {"Tables_in_x": "stock"}
        cursor.fetchall.return_value = []

        with patch("stock.services.stock_a_fecha._nombre_tabla", return_value="stock"):
            saldos_stock_a_fecha("empresa92", date(2025, 3, 1), id_depositos=[3, 4])

        sql = cursor.execute.call_args[0][0]
        self.assertIn("CodDeposito IN", sql)
        params = cursor.execute.call_args[0][1]
        self.assertIn(3, params)
        self.assertIn(4, params)

    @patch("stock.services.stock_a_fecha.mysql_cursor")
    def test_corte_inclusive_en_sql(self, mock_cursor):
        from stock.services.stock_a_fecha import saldos_stock_a_fecha

        cursor = MagicMock()
        mock_cursor.return_value.__enter__.return_value = cursor
        cursor.fetchone.return_value = {"Tables_in_x": "stock"}
        cursor.fetchall.return_value = [
            {"IDArt": 1, "CodDeposito": 1, "saldo": Decimal("12")},
        ]

        with patch("stock.services.stock_a_fecha._nombre_tabla", return_value="stock"):
            saldos_stock_a_fecha("empresa92", date(2024, 12, 31))

        sql = cursor.execute.call_args[0][0]
        self.assertIn("<=", sql)
