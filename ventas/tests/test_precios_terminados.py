# -*- coding: utf-8 -*-
"""Tests — precios terminados tabla."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from ventas.services.precios_articulo_legacy import (
    calcular_final_desde_neto,
    calcular_neto_desde_final,
    calcular_util_desde_neto,
)
from ventas.services.precios_terminados import (
    PreciosTerminadosFiltros,
    _aplicar_operacion_valor,
    build_filtros_query_string,
    parse_listas_incluidas,
    parse_precios_terminados_filtros,
    preview_cambio_masivo,
    tipo_art_fab_desde_param,
)


class PreciosArticuloLegacyTests(SimpleTestCase):
    def test_neto_final_ida_vuelta_iva_21(self):
        neto = Decimal("100")
        final = calcular_final_desde_neto(neto, alicuota_iva=Decimal("21"), impuesto_interno_pct=Decimal("0"))
        self.assertEqual(final, Decimal("121.00"))
        back = calcular_neto_desde_final(final, alicuota_iva=Decimal("21"), impuesto_interno_pct=Decimal("0"))
        self.assertEqual(back, Decimal("100.00"))

    def test_util_desde_neto(self):
        util = calcular_util_desde_neto(Decimal("50"), Decimal("75"))
        self.assertEqual(util, Decimal("50.00"))


class PreciosTerminadosFiltrosTests(SimpleTestCase):
    def test_tipo_art_fab(self):
        self.assertEqual(tipo_art_fab_desde_param("terminado"), "Terminado")
        self.assertEqual(tipo_art_fab_desde_param("2da"), "Fabricado 2da")

    def test_parse_listas_default(self):
        self.assertEqual(parse_listas_incluidas([]), [1, 2, 3, 4, 5])

    def test_parse_filtros_get(self):
        req = MagicMock()
        req.GET.get.return_value = "terminado"
        req.GET.getlist.side_effect = lambda k: {
            "marcas_incluidos": ["1", "2"],
            "codigos_incluidos": [],
            "proveedores_incluidos": [],
            "rubros_incluidos": [],
            "subrubros_incluidos": [],
            "listas_incluidas": ["1", "3"],
        }.get(k, [])
        f = parse_precios_terminados_filtros(req.GET)
        self.assertEqual(f.tipo_producto, "terminado")
        self.assertEqual(f.marcas_incluidos, [1, 2])
        self.assertEqual(f.listas_incluidas, [1, 3])

    def test_build_qs_reset_secundarios(self):
        f = PreciosTerminadosFiltros(
            tipo_producto="2da",
            marcas_incluidos=[5],
            listas_incluidas=[1, 2],
        )
        qs = build_filtros_query_string(f, reset_secundarios=True)
        self.assertIn("tipo_producto=2da", qs)
        self.assertNotIn("marcas_incluidos", qs)
        self.assertIn("listas_incluidas=1", qs)

    def test_operacion_porcentaje(self):
        v = _aplicar_operacion_valor(Decimal("100"), "porcentaje_mas", Decimal("10"))
        self.assertEqual(v, Decimal("110.00"))

    def test_preview_masivo_ids_visibles(self):
        p = preview_cambio_masivo(
            "test",
            PreciosTerminadosFiltros(),
            {"ambito": "precio_neto", "tipo_operacion": "establecer", "valor": 10, "listas": [1]},
            ids_articulos=[10, 20, 30],
        )
        self.assertTrue(p.get("ok"))
        self.assertEqual(p["total_articulos"], 3)
        self.assertEqual(p["alcance"], "tabla_visible")

    def test_preview_masivo_sin_listas(self):
        p = preview_cambio_masivo(
            "test",
            PreciosTerminadosFiltros(),
            {"ambito": "precio_neto", "tipo_operacion": "establecer", "valor": 10, "listas": []},
            ids_articulos=[1],
        )
        self.assertFalse(p.get("ok"))
        self.assertEqual(p.get("error"), "listas_requeridas")


class PreciosTerminadosUrlTests(TestCase):
    def test_urls_resolve(self):
        self.assertEqual(reverse("ventas:precios_terminados"), "/ventas/precios-terminados/")
        self.assertEqual(
            reverse("ventas:api_precios_terminados_articulos_buscar"),
            "/ventas/precios-terminados/api/articulos-buscar/",
        )
