# -*- coding: utf-8 -*-
"""Tests fix naming crédito en pedido masivo matriz (Fase A — TDD)."""
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from ecom.services.pedido_masivo_matriz import credito_cliente_masivo


class PedidoMasivoMatrizCreditoTests(SimpleTestCase):
    @patch("ecom.services.pedido_masivo_matriz.get_mysql_pool")
    def test_separa_cupo_monetario_y_limite_dias(self, mock_pool):
        conn = MagicMock()
        cursor = MagicMock()
        mock_pool.return_value.get_connection.return_value.__enter__.return_value = conn
        conn.cursor.return_value = cursor
        cursor.execute.return_value = None
        cursor.fetchone.return_value = (Decimal("1500.50"), Decimal("50000"), 30)

        res = credito_cliente_masivo("emp1", 42)

        self.assertEqual(res["saldo"], 1500.50)
        self.assertEqual(res["credito_cupo"], 50000.0)
        self.assertEqual(res["credito_limite_dias"], 30)
        self.assertNotEqual(res["credito_cupo"], res["credito_limite_dias"])
        sql = cursor.execute.call_args[0][0].lower()
        self.assertIn("credito_limite_dias", sql)
        self.assertIn("cliente.credito", sql)

    @patch("ecom.services.pedido_masivo_matriz.get_mysql_pool")
    def test_cliente_inexistente_devuelve_ceros(self, mock_pool):
        conn = MagicMock()
        cursor = MagicMock()
        mock_pool.return_value.get_connection.return_value.__enter__.return_value = conn
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = None

        res = credito_cliente_masivo("emp1", 99)

        self.assertEqual(res, {"saldo": 0.0, "credito_cupo": 0.0, "credito_limite_dias": 0})
