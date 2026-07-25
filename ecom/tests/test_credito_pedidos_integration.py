# -*- coding: utf-8 -*-
"""
Integración del flujo crédito: checkout → cola Finanzas → aprobar → gate preparación.

Ejecutar con Django: ``manage.py test ecom.tests.test_credito_pedidos_integration``
Ejecutar solo integración MySQL (pytest): ``pytest -m integration ecom/tests/test_credito_pedidos_integration.py``
"""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from ecom.services.credito_pedidos.aprobacion import (
    ESTADO_PENDIENTE,
    aplicar_estado_credito_checkout,
    puede_avanzar_a_preparacion,
    resolver_finanzas,
)
from ecom.services.logistica_estado_pedidos_relay import validar_gate_credito_preparacion
from ecom.services.mayorista_credito import NO_AUTORIZADO

try:
    import pytest

    pytestmark = pytest.mark.integration
except ImportError:  # pragma: no cover
    pytest = None


class _FlujoIntegracionCursor:
    """Cursor in-memory que simula ``comp_ped`` + eventos para la cadena de servicios."""

    def __init__(self):
        self.pedidos: dict[int, dict] = {}
        self.eventos: list[tuple] = []

    def execute(self, sql, params=None):
        low = " ".join(sql.split()).lower()
        params = params or ()
        if "update comp_ped" in low:
            cod_mov = params[-1]
            ped = self.pedidos.setdefault(
                int(cod_mov),
                {
                    "credito_hold_prep": "No",
                    "estado_credito_finanzas": "-",
                    "autorizacion_sistema": NO_AUTORIZADO,
                    "Anulado": "No",
                },
            )
            if "estado_credito_finanzas" in low and "autorizacion_sistema" in low:
                ped["estado_credito_finanzas"] = params[0]
                ped["autorizacion_sistema"] = "Autorizado"
                ped["credito_hold_prep"] = "No"
            elif "estado_credito_finanzas" in low and "credito_hold_prep" in low:
                ped["estado_credito_finanzas"] = params[0]
                ped["credito_hold_prep"] = params[1]
            elif "estado_credito_finanzas" in low:
                ped["estado_credito_finanzas"] = params[0]
        elif "insert into ecom_credito_evento" in low:
            self.eventos.append(params)
        elif "select trim(coalesce(credito_hold_prep" in low:
            cod_mov = params[0]
            ped = self.pedidos.get(int(cod_mov), {"credito_hold_prep": "No"})
            self._last = {"credito_hold_prep": ped.get("credito_hold_prep", "No")}
        else:
            self._last = None

    def fetchone(self):
        return getattr(self, "_last", None)

    def close(self):
        pass


def _fetch_ped_side_effect(cursor_state, base, cod_mov):
    ped = cursor_state.pedidos.get(int(cod_mov))
    if not ped:
        return None
    return {
        "CodigoMovimiento": cod_mov,
        "Codigo": 10,
        "estado_credito_finanzas": ped.get("estado_credito_finanzas", ESTADO_PENDIENTE),
        "credito_hold_prep": ped.get("credito_hold_prep", "Si"),
        "autorizacion_sistema": ped.get("autorizacion_sistema", NO_AUTORIZADO),
        "Anulado": "No",
    }


class TestCreditoPedidosFlujoIntegracion(SimpleTestCase):
    @patch("ecom.services.credito_pedidos.aprobacion.credito_pedidos_activo", return_value=True)
    @patch("ecom.services.credito_pedidos.aprobacion.credito_hold_prep_activo", return_value=True)
    def test_checkout_finanzas_aprobar_libera_preparacion(self, _hold, _flag):
        cursor = _FlujoIntegracionCursor()
        cod_mov = 88001

        estado = aplicar_estado_credito_checkout(
            cursor,
            "emp_int",
            cod_mov=cod_mov,
            cod_solicita=42,
            autorizacion_sistema=NO_AUTORIZADO,
        )
        self.assertEqual(estado, ESTADO_PENDIENTE)

        ok_prep, msg = puede_avanzar_a_preparacion(cursor, cod_mov)
        self.assertFalse(ok_prep)
        self.assertIn("crédito", msg.lower())

        with patch(
            "ecom.services.credito_pedidos.aprobacion._fetch_ped_credito",
            side_effect=lambda base, cm: _fetch_ped_side_effect(cursor, base, cm),
        ), patch("ecom.services.credito_pedidos.aprobacion.get_mysql_pool") as mock_pool:
            conn = MagicMock()
            conn.cursor.return_value = cursor
            mock_pool.return_value.get_connection.return_value.__enter__ = lambda s: conn
            mock_pool.return_value.get_connection.return_value.__exit__ = MagicMock(
                return_value=False
            )

            sess = {"synap_permisos": ["finance.credito.aprobar"], "id_usuario": 99}
            ok, msg, payload = resolver_finanzas(
                "emp_int", cod_mov, "aprobar", 99, "-", sess_user=sess
            )

        self.assertTrue(ok, msg)
        self.assertEqual(payload.get("estado_credito_finanzas"), "aprobado")
        self.assertEqual(cursor.pedidos[cod_mov]["autorizacion_sistema"], "Autorizado")
        self.assertEqual(cursor.pedidos[cod_mov]["credito_hold_prep"], "No")

        ok_prep, msg = puede_avanzar_a_preparacion(cursor, cod_mov)
        self.assertTrue(ok_prep)
        self.assertEqual(msg, "")

    @patch("ecom.services.logistica_estado_pedidos_relay.credito_pedidos_activo", return_value=True)
    @patch("ecom.services.logistica_estado_pedidos_relay.mysql_cursor")
    def test_validar_gate_preparacion_delega_en_aprobacion(self, mock_mc, _flag):
        inner = _FlujoIntegracionCursor()
        inner.pedidos[88002] = {"credito_hold_prep": "Si"}
        mock_mc.return_value.__enter__ = lambda s: inner
        mock_mc.return_value.__exit__ = MagicMock(return_value=False)

        ok, msg = validar_gate_credito_preparacion("emp_int", 88002)
        self.assertFalse(ok)
        self.assertIn("crédito", msg.lower())


def _existe_tabla(conn, tabla: str) -> bool:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name = %s",
            [tabla],
        )
        return bool(cursor.fetchone()[0])


@unittest.skipUnless(
    os.environ.get("SYNAP_TEST_MYSQL_CREDITO") == "1",
    "Integración DDL MySQL desactivada (definir SYNAP_TEST_MYSQL_CREDITO=1).",
)
class TestCreditoPedidosDDLIntegracion(SimpleTestCase):
    """Verificación opcional contra MySQL legacy, sin crear base de pruebas."""

    databases = {"mysql"} if os.environ.get("SYNAP_TEST_MYSQL_CREDITO") == "1" else set()

    def test_tablas_credito_presentes_si_mysql_disponible(self):
        from django.db import connections

        try:
            conn = connections["mysql"]
            conn.ensure_connection()
        except Exception as exc:
            self.skipTest(f"MySQL legacy no disponible: {exc}")

        faltantes = [
            t
            for t in (
                "ecom_credito_politica",
                "ecom_credito_evaluacion",
                "ecom_credito_evento",
                "ecom_credito_plantilla_aviso",
                "ecom_credito_aviso_log",
            )
            if not _existe_tabla(conn, t)
        ]
        if faltantes:
            self.skipTest(f"Base sin tablas crédito: {', '.join(faltantes)}")
