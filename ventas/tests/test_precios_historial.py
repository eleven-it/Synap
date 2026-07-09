# -*- coding: utf-8 -*-
"""Tests — analítica precios_historial."""

from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase
from django.urls import reverse

from ventas.services.precios_historial import (
    HistorialPreciosFiltros,
    _delta_pct,
    _enriquecer_filas_con_deltas,
    parse_historial_filtros,
    resumen_evolucion_desde_filas,
)


class PreciosHistorialCalculoTests(SimpleTestCase):
    def test_delta_pct(self):
        self.assertEqual(_delta_pct(Decimal("110"), Decimal("100")), 10.0)
        self.assertIsNone(_delta_pct(Decimal("10"), Decimal("0")))

    def test_enriquecer_deltas(self):
        raw = [
            {
                "id_precios_historial": 1,
                "fecha": date(2026, 1, 1),
                "fecha_control": "2026-01-01 10:00:00",
                "tipo_modificacion": "Synap precios terminados",
                "precio_neto1": Decimal("100"),
                "precio_iva1": Decimal("121"),
                "util1": Decimal("20"),
                "precio_costo": Decimal("80"),
                "alicuota_iva": Decimal("21"),
                "nombre_articulo": "Art A",
            },
            {
                "id_precios_historial": 2,
                "fecha": date(2026, 2, 1),
                "fecha_control": "2026-02-01 10:00:00",
                "tipo_modificacion": "Synap precios terminados",
                "precio_neto1": Decimal("110"),
                "precio_iva1": Decimal("133.1"),
                "util1": Decimal("25"),
                "precio_costo": Decimal("85"),
                "alicuota_iva": Decimal("21"),
                "nombre_articulo": "Art A",
            },
        ]
        filas = _enriquecer_filas_con_deltas(raw, 1)
        self.assertIsNone(filas[0]["delta_pct"])
        self.assertEqual(filas[1]["delta_neto"], 10.0)
        self.assertEqual(filas[1]["delta_pct"], 10.0)
        self.assertEqual(filas[1]["dias_desde_anterior"], 31)

    def test_resumen_evolucion(self):
        filas = [
            {"neto": 100.0, "final": 121.0},
            {"neto": 110.0, "final": 133.1},
        ]
        r = resumen_evolucion_desde_filas(filas, 1)
        self.assertEqual(r["cantidad_cambios"], 2)
        self.assertEqual(r["variacion_pct_acumulada"], 10.0)

    def test_parse_filtros(self):
        class _Params:
            def get(self, k, d=None):
                return {
                    "lista": "2",
                    "fecha_desde": "2026-01-01",
                    "fecha_hasta": "2026-03-31",
                    "solo_synap": "1",
                }.get(k, d)

            def getlist(self, k):
                return {"marcas_incluidos": ["5", "7"]}.get(k, [])

        f = parse_historial_filtros(_Params())
        self.assertEqual(f.lista, 2)
        self.assertEqual(f.marcas_incluidos, [5, 7])
        self.assertTrue(f.solo_synap)


class PreciosHistorialUrlTests(SimpleTestCase):
    def test_urls(self):
        self.assertEqual(
            reverse("ventas:evolucion_precios"),
            "/ventas/evolucion-precios/",
        )
        self.assertEqual(
            reverse("ventas:api_precios_historial_articulo", kwargs={"id_articulo": 42}),
            "/ventas/precios-terminados/api/historial/42/",
        )
