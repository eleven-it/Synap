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
    DIR_DEFAULT,
    ORDEN_DEFAULT,
    RESERVA_EQ0,
    RESERVA_GT0,
    PreciosTerminadosFiltros,
    _aplicar_operacion_valor,
    _append_filtros_where,
    build_filtros_query_string,
    build_orden_query_string,
    parse_dir,
    parse_listas_incluidas,
    parse_orden,
    parse_precios_terminados_filtros,
    parse_reserva,
    preview_cambio_masivo,
    sql_order_by,
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

    def test_parse_orden_invalido_default(self):
        self.assertEqual(parse_orden("codigo"), "codigo")
        self.assertEqual(parse_orden("neto_3"), "neto_3")
        self.assertEqual(parse_orden("DROP TABLE"), ORDEN_DEFAULT)
        self.assertEqual(parse_orden(None), ORDEN_DEFAULT)

    def test_parse_dir_invalido_default(self):
        self.assertEqual(parse_dir("asc"), "asc")
        self.assertEqual(parse_dir("desc"), "desc")
        self.assertEqual(parse_dir("invalid"), DIR_DEFAULT)

    def test_parse_reserva(self):
        self.assertEqual(parse_reserva(""), "")
        self.assertEqual(parse_reserva("eq0"), RESERVA_EQ0)
        self.assertEqual(parse_reserva("gt0"), RESERVA_GT0)
        self.assertEqual(parse_reserva("otro"), "")

    def test_build_qs_orden_reserva(self):
        f = PreciosTerminadosFiltros(
            orden="nombre",
            dir="desc",
            reserva=RESERVA_GT0,
            marcas_incluidos=[1],
        )
        qs = build_filtros_query_string(f)
        self.assertIn("orden=nombre", qs)
        self.assertIn("dir=desc", qs)
        self.assertIn("reserva=gt0", qs)
        self.assertIn("marcas_incluidos=1", qs)

    def test_build_qs_orden_default_omitido(self):
        f = PreciosTerminadosFiltros()
        qs = build_filtros_query_string(f)
        self.assertNotIn("orden=", qs)
        self.assertNotIn("dir=", qs)

    def test_sql_order_by_whitelist(self):
        f = PreciosTerminadosFiltros(orden="final_2", dir="desc")
        sql = sql_order_by(f)
        self.assertIn("a.Precio2VI DESC", sql)
        self.assertIn("a.IDArt ASC", sql)

    def test_sql_order_by_invalido_usa_default(self):
        f = PreciosTerminadosFiltros(orden="inyeccion", dir="desc")
        sql = sql_order_by(f)
        self.assertIn("a.id_manual", sql)

    def test_append_filtros_reserva_eq0(self):
        f = PreciosTerminadosFiltros(reserva=RESERVA_EQ0)
        where, params = _append_filtros_where(f)
        self.assertIn("COALESCE(a.stock_reserva, 0) = 0", where)
        self.assertEqual(params, [])

    def test_append_filtros_reserva_gt0(self):
        f = PreciosTerminadosFiltros(reserva=RESERVA_GT0)
        where, params = _append_filtros_where(f)
        self.assertIn("COALESCE(a.stock_reserva, 0) > 0", where)
        self.assertEqual(params, [])

    def test_build_orden_query_toggle(self):
        f = PreciosTerminadosFiltros(orden="codigo", dir="asc", marcas_incluidos=[3])
        qs = build_orden_query_string(f, "codigo")
        self.assertIn("dir=desc", qs)
        self.assertIn("orden=codigo", qs)
        self.assertNotIn("page=", qs)

    def test_build_orden_query_nueva_columna_asc(self):
        f = PreciosTerminadosFiltros(orden="codigo", dir="desc")
        qs = build_orden_query_string(f, "nombre")
        self.assertIn("orden=nombre", qs)
        self.assertNotIn("dir=desc", qs)

    def test_parse_filtros_orden_reserva(self):
        req = MagicMock()
        req.GET.get.side_effect = lambda k, default=None: {
            "tipo_producto": "terminado",
            "orden": "reserva",
            "dir": "desc",
            "reserva": "eq0",
        }.get(k, default)
        req.GET.getlist.side_effect = lambda k: {
            "marcas_incluidos": [],
            "codigos_incluidos": [],
            "proveedores_incluidos": [],
            "rubros_incluidos": [],
            "subrubros_incluidos": [],
            "listas_incluidas": [],
        }.get(k, [])
        f = parse_precios_terminados_filtros(req.GET)
        self.assertEqual(f.orden, "reserva")
        self.assertEqual(f.dir, "desc")
        self.assertEqual(f.reserva, RESERVA_EQ0)

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
