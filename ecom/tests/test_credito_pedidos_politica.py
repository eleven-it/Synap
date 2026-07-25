# -*- coding: utf-8 -*-
"""Tests resolver_politica (Fase A — TDD)."""
from django.test import SimpleTestCase

from ecom.services.credito_pedidos.politica import (
    CANAL_PRE,
    PoliticaCredito,
    politica_default_empresa,
    resolver_politica,
)


class FakePoliticaCursor:
    def __init__(self, rows_by_key):
        self.rows_by_key = rows_by_key
        self.calls = []

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        key = (int(params[0]), str(params[1]).upper())
        self._last = self.rows_by_key.get(key)

    def fetchone(self):
        return getattr(self, "_last", None)


class CreditoPoliticaTests(SimpleTestCase):
    def test_politica_especifica_cliente_canal(self):
        cur = FakePoliticaCursor(
            {
                (100, "PED"): {
                    "id": 5,
                    "id_cliente": 100,
                    "canal": "PED",
                    "limite_dias": 45,
                    "capa_cxc": "Si",
                    "capa_ped_abiertos": "No",
                    "capa_remitos_nf": "No",
                    "capa_cheques": "Si",
                    "capa_doc_actual": "Si",
                    "incluir_mora": "Si",
                },
            }
        )
        pol = resolver_politica(cur, 100, "PED")
        self.assertEqual(pol.id, 5)
        self.assertEqual(pol.id_cliente, 100)
        self.assertEqual(pol.limite_dias, 45)
        self.assertTrue(pol.capa_cxc)
        self.assertFalse(pol.capa_ped_abiertos)
        self.assertTrue(pol.capa_cheques)

    def test_fallback_default_empresa_si_no_hay_cliente(self):
        cur = FakePoliticaCursor(
            {
                (200, "PRE"): None,
                (0, "PRE"): {
                    "id": 1,
                    "id_cliente": 0,
                    "canal": "PRE",
                    "limite_dias": 15,
                    "capa_cxc": "Si",
                    "capa_ped_abiertos": "Si",
                    "capa_remitos_nf": "No",
                    "capa_cheques": "No",
                    "capa_doc_actual": "No",
                    "incluir_mora": "Si",
                },
            }
        )
        pol = resolver_politica(cur, 200, CANAL_PRE)
        self.assertEqual(pol.id, 1)
        self.assertEqual(pol.id_cliente, 0)
        self.assertEqual(pol.limite_dias, 15)
        self.assertFalse(pol.capa_doc_actual)
        self.assertEqual(len(cur.calls), 2)

    def test_politica_hardcoded_si_no_hay_filas(self):
        cur = FakePoliticaCursor({})
        pol = resolver_politica(cur, 300, "PED")
        esperada = politica_default_empresa("PED")
        self.assertEqual(pol, esperada)
        self.assertIsInstance(pol, PoliticaCredito)
