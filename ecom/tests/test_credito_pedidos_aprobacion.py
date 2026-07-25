# -*- coding: utf-8 -*-
"""Cola Finanzas, hold prep y resolución crédito (Fase B)."""

import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from ecom.services.credito_pedidos.aprobacion import (
    ESTADO_PENDIENTE,
    aplicar_estado_credito_checkout,
    puede_avanzar_a_preparacion,
    resolver_finanzas,
)
from ecom.services.mayorista_credito import NO_AUTORIZADO


def _capturar_sql(cursor):
    return [str(c[0][0]).lower() for c in cursor.execute.call_args_list if c[0]]


class TestAplicarEstadoCreditoCheckout(unittest.TestCase):
    @patch("ecom.services.credito_pedidos.aprobacion.credito_pedidos_activo", return_value=True)
    @patch("ecom.services.credito_pedidos.aprobacion.credito_hold_prep_activo", return_value=True)
    def test_no_autorizado_pendiente_y_hold(self, _hold, _flag):
        cursor = MagicMock()
        aplicar_estado_credito_checkout(
            cursor,
            "emp1",
            cod_mov=9001,
            cod_solicita=42,
            autorizacion_sistema=NO_AUTORIZADO,
        )
        sqls = _capturar_sql(cursor)
        joined = " ".join(sqls)
        self.assertIn("estado_credito_finanzas", joined)
        self.assertIn("credito_hold_prep", joined)
        self.assertIn("ecom_credito_evento", joined)
        update_call = next(c for c in cursor.execute.call_args_list if "update comp_ped" in str(c[0][0]).lower())
        self.assertIn(ESTADO_PENDIENTE, update_call[0][1])
        self.assertIn("Si", update_call[0][1])

    @patch("ecom.services.credito_pedidos.aprobacion.credito_pedidos_activo", return_value=True)
    @patch("ecom.services.credito_pedidos.aprobacion.credito_hold_prep_activo", return_value=False)
    def test_autorizado_no_crea_cola(self, _hold, _flag):
        cursor = MagicMock()
        aplicar_estado_credito_checkout(
            cursor,
            "emp1",
            cod_mov=9002,
            cod_solicita=42,
            autorizacion_sistema="Autorizado",
        )
        cursor.execute.assert_not_called()


class TestResolverFinanzas(unittest.TestCase):
    @patch("ecom.services.credito_pedidos.aprobacion.credito_pedidos_activo", return_value=True)
    @patch("ecom.services.credito_pedidos.aprobacion._fetch_ped_credito")
    @patch("ecom.services.credito_pedidos.aprobacion.get_mysql_pool")
    def test_aprobar_libera_ped_sin_mutar_cliente(self, mock_pool, mock_fetch, _flag):
        mock_fetch.return_value = {
            "CodigoMovimiento": 9001,
            "Codigo": 10,
            "estado_credito_finanzas": ESTADO_PENDIENTE,
            "Anulado": "No",
        }
        cursor = MagicMock()
        conn = MagicMock()
        conn.cursor.return_value = cursor
        mock_pool.return_value.get_connection.return_value.__enter__ = lambda s: conn
        mock_pool.return_value.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        sess = {"synap_permisos": ["finance.credito.aprobar"], "id_usuario": 5}
        ok, msg, payload = resolver_finanzas(
            "emp1", 9001, "aprobar", 99, "-", sess_user=sess
        )
        self.assertTrue(ok)
        sqls = _capturar_sql(cursor)
        joined = " ".join(sqls)
        self.assertIn("autorizacion_sistema", joined)
        self.assertIn("credito_hold_prep", joined)
        self.assertNotIn("update cliente", joined)
        self.assertNotIn("cliente set", joined)
        self.assertEqual(payload.get("estado_credito_finanzas"), "aprobado")

    @patch("ecom.services.credito_pedidos.aprobacion.credito_pedidos_activo", return_value=True)
    @patch("ecom.services.credito_pedidos.aprobacion.get_mysql_pool")
    def test_sin_permiso_rechaza(self, mock_pool, _flag):
        cursor = MagicMock()
        conn = MagicMock()
        conn.cursor.return_value = cursor
        mock_pool.return_value.get_connection.return_value.__enter__ = lambda s: conn
        mock_pool.return_value.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        sess = {"synap_permisos": ["ecom.pedidos.aprobar"]}
        ok, msg, _ = resolver_finanzas(
            "emp1", 9001, "aprobar", 99, "-", sess_user=sess
        )
        self.assertFalse(ok)
        self.assertIn("permiso", msg.lower())
        cursor.execute.assert_not_called()


class TestHoldPrepGate(unittest.TestCase):
    def test_hold_si_bloquea_preparacion(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = {"credito_hold_prep": "Si"}
        ok, msg = puede_avanzar_a_preparacion(cursor, 9001)
        self.assertFalse(ok)
        self.assertIn("crédito", msg.lower())

    def test_hold_no_permite_preparacion(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = {"credito_hold_prep": "No"}
        ok, msg = puede_avanzar_a_preparacion(cursor, 9001)
        self.assertTrue(ok)
        self.assertEqual(msg, "")
