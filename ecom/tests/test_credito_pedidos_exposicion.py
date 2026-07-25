# -*- coding: utf-8 -*-
"""Tests calcular_exposicion (Fase A — TDD)."""
from decimal import Decimal

from django.test import SimpleTestCase

from ecom.services.credito_pedidos.exposicion import (
    CAPA_CXC,
    CAPA_PED_ABIERTOS,
    calcular_exposicion,
)
from ecom.services.credito_pedidos.politica import PoliticaCredito


class FakeExposicionCursor:
    def __init__(self, responses):
        self.responses = responses
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        low = " ".join(sql.split()).lower()
        if "from cliente" in low and "saldo" in low:
            self._last = {"monto": self.responses.get("cxc", 0)}
        elif "tipocomprobante = 'ped'" in low:
            self._last = {"monto": self.responses.get("ped_abiertos", 0)}
        elif "tipocomprobante = 'rem'" in low:
            self._last = {"monto": self.responses.get("remitos_nf", 0)}
        elif "credito_cheque" in low:
            self._last = {"monto": self.responses.get("cheques", 0)}
        else:
            self._last = {"monto": 0}

    def fetchone(self):
        return getattr(self, "_last", None)


def _politica(**kwargs):
    base = {
        "id": 1,
        "id_cliente": 0,
        "canal": "PED",
        "limite_dias": None,
        "capa_cxc": True,
        "capa_ped_abiertos": True,
        "capa_remitos_nf": False,
        "capa_cheques": False,
        "capa_doc_actual": True,
        "incluir_mora": True,
    }
    base.update(kwargs)
    return PoliticaCredito(**base)


class CreditoExposicionTests(SimpleTestCase):
    def test_capas_parciales_on_off(self):
        cur = FakeExposicionCursor({"cxc": 1000, "ped_abiertos": 500, "cheques": 200})
        pol = _politica(capa_cxc=True, capa_ped_abiertos=True, capa_cheques=False)
        res = calcular_exposicion(cur, 10, pol, doc_actual=Decimal("0"))
        self.assertEqual(res.capas[CAPA_CXC], Decimal("1000"))
        self.assertEqual(res.capas[CAPA_PED_ABIERTOS], Decimal("500"))
        self.assertNotIn("cheques", res.capas)
        self.assertEqual(res.total, Decimal("1500"))

    def test_credito_cero_doc_actual_no_bloquea_por_capas_base(self):
        cur = FakeExposicionCursor({"cxc": 50000})
        pol = _politica(capa_cxc=True, capa_ped_abiertos=False, capa_doc_actual=True)
        res = calcular_exposicion(cur, 10, pol, doc_actual=Decimal("999999"))
        self.assertEqual(res.capas[CAPA_CXC], Decimal("50000"))
        self.assertEqual(res.capas["doc_actual"], Decimal("999999"))
        self.assertEqual(res.total, Decimal("1049999"))

    def test_sin_capas_activas_total_cero(self):
        cur = FakeExposicionCursor({"cxc": 8000})
        pol = _politica(
            capa_cxc=False,
            capa_ped_abiertos=False,
            capa_doc_actual=False,
        )
        res = calcular_exposicion(cur, 10, pol)
        self.assertEqual(res.capas, {})
        self.assertEqual(res.total, Decimal("0"))
