# -*- coding: utf-8 -*-
"""Tests evaluar_pedido, semáforo y snapshot (Fase A — TDD)."""
from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase

from ecom.services.credito_pedidos.evaluacion import (
    MOTIVO_DIAS,
    MOTIVO_MONTO,
    SEMAFORO_ROJO,
    SEMAFORO_VERDE,
    evaluar_pedido,
)
from ecom.services.credito_pedidos.politica import PoliticaCredito
from ecom.services.mayorista_credito import AUTORIZADO, NO_AUTORIZADO


class FakeEvalCursor:
    def __init__(self, *, politica_row=None, capas=None, atraso=None):
        self.politica_row = politica_row
        self.capas = capas or {}
        self.atraso = atraso
        self.inserts = []
        self.lastrowid = 99

    def execute(self, sql, params=None):
        low = " ".join(sql.split()).lower()
        if "from ecom_credito_politica" in low:
            self._last = self.politica_row
        elif "from cliente" in low and "saldo" in low:
            self._last = {"monto": self.capas.get("cxc", 0)}
        elif "tipocomprobante = 'ped'" in low:
            self._last = {"monto": self.capas.get("ped_abiertos", 0)}
        elif "from cuentacliente" in low:
            self._last = {"ultimaf": self.atraso}
        elif "insert into ecom_credito_evaluacion" in low:
            self.inserts.append(params)
        else:
            self._last = {"monto": 0}

    def fetchone(self):
        return getattr(self, "_last", None)


def _politica_default():
    return PoliticaCredito(
        id=0,
        id_cliente=0,
        canal="PED",
        limite_dias=None,
        capa_cxc=True,
        capa_ped_abiertos=False,
        capa_remitos_nf=False,
        capa_cheques=False,
        capa_doc_actual=True,
        incluir_mora=True,
    )


class CreditoEvaluacionTests(SimpleTestCase):
    @patch("ecom.services.credito_pedidos.evaluacion.resolver_politica", return_value=_politica_default())
    @patch("ecom.services.credito_pedidos.evaluacion.dias_atraso", return_value=None)
    def test_credito_cero_no_rechaza_por_monto(self, _dias, _pol):
        cur = FakeEvalCursor(capas={"cxc": Decimal("0")})
        res = evaluar_pedido(
            cur,
            id_cliente=10,
            canal="PED",
            total_pedido=Decimal("500000"),
            credito_cliente=Decimal("0"),
            credito_limite_dias=30,
        )
        self.assertEqual(res.autorizacion, AUTORIZADO)
        self.assertTrue(res.sin_tope_monetario)
        self.assertNotIn(MOTIVO_MONTO, res.motivos)
        self.assertIsNone(res.disponible)

    @patch("ecom.services.credito_pedidos.evaluacion.resolver_politica", return_value=_politica_default())
    @patch("ecom.services.credito_pedidos.evaluacion.dias_atraso", return_value=None)
    def test_exceso_monto_no_autorizado_semaforo_rojo(self, _dias, _pol):
        cur = FakeEvalCursor(capas={"cxc": Decimal("8000")})
        res = evaluar_pedido(
            cur,
            id_cliente=10,
            canal="PED",
            total_pedido=Decimal("5000"),
            credito_cliente=Decimal("10000"),
            credito_limite_dias=30,
        )
        self.assertEqual(res.autorizacion, NO_AUTORIZADO)
        self.assertIn(MOTIVO_MONTO, res.motivos)
        self.assertEqual(res.semaforo, SEMAFORO_ROJO)
        self.assertEqual(res.exposicion, Decimal("13000"))

    @patch("ecom.services.credito_pedidos.evaluacion.resolver_politica", return_value=_politica_default())
    @patch("ecom.services.credito_pedidos.evaluacion.dias_atraso", return_value=45)
    def test_mora_excedida_motivo_dias(self, _dias, _pol):
        cur = FakeEvalCursor()
        res = evaluar_pedido(
            cur,
            id_cliente=10,
            canal="PED",
            total_pedido=Decimal("100"),
            credito_cliente=Decimal("50000"),
            credito_limite_dias=30,
        )
        self.assertEqual(res.autorizacion, NO_AUTORIZADO)
        self.assertIn(MOTIVO_DIAS, res.motivos)

    @patch("ecom.services.credito_pedidos.evaluacion.resolver_politica", return_value=_politica_default())
    @patch("ecom.services.credito_pedidos.evaluacion.dias_atraso", return_value=None)
    def test_dentro_cupo_autorizado_verde(self, _dias, _pol):
        cur = FakeEvalCursor(capas={"cxc": Decimal("1000")})
        res = evaluar_pedido(
            cur,
            id_cliente=10,
            canal="PED",
            total_pedido=Decimal("500"),
            credito_cliente=Decimal("10000"),
            credito_limite_dias=30,
        )
        self.assertEqual(res.autorizacion, AUTORIZADO)
        self.assertEqual(res.semaforo, SEMAFORO_VERDE)
        self.assertEqual(res.disponible, Decimal("8500"))

    @patch("ecom.services.credito_pedidos.evaluacion.resolver_politica", return_value=_politica_default())
    @patch("ecom.services.credito_pedidos.evaluacion.dias_atraso", return_value=None)
    def test_persistir_snapshot_evaluacion(self, _dias, _pol):
        cur = FakeEvalCursor(capas={"cxc": Decimal("0")})
        res = evaluar_pedido(
            cur,
            id_cliente=10,
            canal="PED",
            total_pedido=Decimal("100"),
            credito_cliente=Decimal("5000"),
            credito_limite_dias=30,
            persistir=True,
            codigo_movimiento=1234,
        )
        self.assertEqual(res.evaluacion_id, 99)
        self.assertEqual(len(cur.inserts), 1)
        self.assertEqual(cur.inserts[0][0], 1234)
        self.assertEqual(cur.inserts[0][3], AUTORIZADO)
