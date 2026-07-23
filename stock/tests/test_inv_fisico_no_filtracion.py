# -*- coding: utf-8 -*-
"""Tests no-filtración saldo/diferencia en APIs contador (Fase 3 — Strict TDD)."""
import json
from decimal import Decimal

from django.test import SimpleTestCase

from stock.services import inventario_fisico as svc


class CamposProhibidosConteoTest(SimpleTestCase):
    PROHIBIDOS = frozenset({"saldo_snapshot", "saldo_sistema", "diferencia", "saldo"})

    def test_serializar_articulo_catalogo_ciego_omite_saldo(self):
        fila = {
            "id_articulo": 10,
            "codigo": "1.1.100",
            "nombre": "Artículo test",
            "ean": ["7790001234567"],
            "saldo_snapshot": Decimal("50"),
            "diferencia": Decimal("5"),
            "saldo": Decimal("50"),
        }
        out = svc.serializar_articulo_catalogo_ciego(fila)
        for campo in self.PROHIBIDOS:
            self.assertNotIn(campo, out)
        self.assertEqual(out["id_articulo"], 10)
        self.assertEqual(out["codigo"], "1.1.100")

    def test_payload_prefetch_sin_claves_prohibidas(self):
        raw = {
            "id_campana": 1,
            "id_deposito": 2,
            "catalogo_version": "v1",
            "articulos": [
                {
                    "id_articulo": 1,
                    "codigo": "A",
                    "nombre": "Uno",
                    "ean": [],
                    "saldo_snapshot": Decimal("99"),
                }
            ],
        }
        payload = svc.serializar_prefetch_ciego(raw)
        texto = json.dumps(payload, default=str)
        for campo in self.PROHIBIDOS:
            self.assertNotIn(f'"{campo}"', texto)

    def test_buscar_claves_prohibidas_en_anidado(self):
        payload = {"articulos": [{"id_articulo": 1, "nested": {"diferencia": 1}}]}
        encontradas = svc.buscar_claves_prohibidas_conteo(payload)
        self.assertIn("diferencia", encontradas)


class SyncRespuestaConteoTest(SimpleTestCase):
    def test_respuesta_sync_aceptados_sin_saldo(self):
        resp = svc.serializar_respuesta_sync(
            aceptados=[{"client_event_id": "abc", "id_articulo": 1, "cantidad": "5"}],
            conflictos=[],
            rechazados=[],
        )
        texto = json.dumps(resp, default=str)
        self.assertNotIn("saldo_snapshot", texto)
        self.assertNotIn("diferencia", texto)
        self.assertIn("aceptados", resp)
