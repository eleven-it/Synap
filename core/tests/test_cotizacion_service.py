# -*- coding: utf-8 -*-
"""Tests cotizacion_service (MySQL mock)."""
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase

from core.services.cotizacion_service import historial, registrar_manual, resolver_tc


class ResolverTcUnitTest(SimpleTestCase):
    @patch("core.services.cotizacion_service.get_connection")
    def test_carry_forward_historial(self, mock_conn_ctx):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [(Decimal("1180"),), None]
        conn = MagicMock()
        conn.cursor.return_value = cursor
        mock_conn_ctx.return_value.__enter__.return_value = conn

        tc = resolver_tc("empresa_test", "2026-08-02", id_cotizacion=1)
        self.assertEqual(tc, 1180.0)

    @patch("core.services.cotizacion_service.get_connection")
    def test_sin_historial_usa_maestro(self, mock_conn_ctx):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [None, (Decimal("1200"),)]
        conn = MagicMock()
        conn.cursor.return_value = cursor
        mock_conn_ctx.return_value.__enter__.return_value = conn

        tc = resolver_tc("empresa_test", "2026-08-02")
        self.assertEqual(tc, 1200.0)

    @patch("core.services.cotizacion_service.get_connection")
    def test_sin_datos_retorna_none(self, mock_conn_ctx):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [None, None]
        conn = MagicMock()
        conn.cursor.return_value = cursor
        mock_conn_ctx.return_value.__enter__.return_value = conn

        self.assertIsNone(resolver_tc("empresa_test", "2026-08-02"))


class CotizacionServiceWriteTest(TestCase):
    @patch("core.services.cotizacion_service.get_connection")
    def test_registrar_manual_ejecuta_update_e_upsert(self, mock_conn_ctx):
        cursor = MagicMock()
        conn = MagicMock()
        conn.cursor.return_value = cursor
        mock_conn_ctx.return_value.__enter__.return_value = conn

        res = registrar_manual("emp_test", valor=1150.0, id_usuario=7, observacion="Test")
        self.assertEqual(res["valor"], 1150.0)
        self.assertEqual(res["origen"], "manual")
        self.assertTrue(cursor.execute.called)
        conn.commit.assert_called_once()

    @patch("core.services.cotizacion_service.get_connection")
    def test_historial_formatea_fecha_es(self, mock_conn_ctx):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            (1, date(2026, 8, 1), Decimal("1180"), "bcra_referencia", "bcra_sugerido", 1, "-", None),
        ]
        conn = MagicMock()
        conn.cursor.return_value = cursor
        mock_conn_ctx.return_value.__enter__.return_value = conn

        filas = historial("emp_test", limite=5)
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["fecha_es"], "01/08/2026")
