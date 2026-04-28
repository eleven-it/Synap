"""API Entregas: no expone importes al chofer."""
from __future__ import annotations

from django.test import SimpleTestCase

from logistica.api_entregas import _dict_sin_importes


class TestDictSinImportes(SimpleTestCase):
    def test_quita_claves_conocidas(self):
        d = {
            "nro_remito": "1",
            "total_remito": 1500.0,
            "totalRemito": 99,
            "totalPedido": 1,
            "totalFactura": 2,
        }
        out = _dict_sin_importes(d)
        self.assertEqual(out, {"nro_remito": "1"})

    def test_vacio_o_none(self):
        self.assertEqual(_dict_sin_importes({}), {})
        self.assertEqual(_dict_sin_importes(None), None)
