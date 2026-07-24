# -*- coding: utf-8 -*-
"""Tests servicio inventario tabla MPR."""
from django.test import SimpleTestCase
from unittest.mock import MagicMock, patch

from stock.services.inventario_tabla import (
    AMBITO_FABRICADOS,
    AMBITO_TERMINADOS,
    ETAPAS_FABRICADOS,
    ETAPAS_TERMINADOS,
    InventarioTablaFiltros,
    _build_articulo_where,
    _sql_consolidado_expr,
    _sql_tiene_stock_positivo_expr,
    buscar_articulos_inventario,
    build_inventario_query_string,
    ce_texto,
    codigo_compuesto_articulo,
    consultar_inventario_tabla,
    etapas_para_ambito,
    parse_ambito,
    parse_inventario_filtros,
    parse_presentacion,
)


class CodigoCompuestoTest(SimpleTestCase):
    def test_manual_y_prov(self):
        self.assertEqual(codigo_compuesto_articulo("12A", "PRV-88"), "12A - PRV-88")

    def test_solo_manual(self):
        self.assertEqual(codigo_compuesto_articulo("12A", ""), "12A")
        self.assertEqual(codigo_compuesto_articulo("12A", None), "12A")


class CeTextoTest(SimpleTestCase):
    def test_vacio_y_guion(self):
        self.assertEqual(ce_texto(""), "")
        self.assertEqual(ce_texto("-"), "")
        self.assertEqual(ce_texto(None), "")

    def test_valor(self):
        self.assertEqual(ce_texto("T4"), "T4")
        self.assertEqual(ce_texto(" Negro "), "Negro")


class ParseFiltrosTest(SimpleTestCase):
    def test_default(self):
        f = parse_inventario_filtros({})
        self.assertFalse(f.incluir_ceros)
        self.assertEqual(f.presentacion, "unidades")
        self.assertEqual(f.ambito, AMBITO_FABRICADOS)
        self.assertEqual(f.page, 1)

    def test_ambito_terminados(self):
        f = parse_inventario_filtros({"ambito": "terminados"})
        self.assertEqual(f.ambito, AMBITO_TERMINADOS)

    def test_ambito_invalido(self):
        f = parse_inventario_filtros({"ambito": "otro"})
        self.assertEqual(f.ambito, AMBITO_FABRICADOS)

    def test_marcas_multi(self):
        class Q:
            def get(self, k, d=None):
                return d

            def getlist(self, k):
                return ["3", "7"]

        f = parse_inventario_filtros(Q(), marcas_getlist=["3", "7"])
        self.assertEqual(f.marcas_incluidos, [3, 7])

    def test_incluir_ceros(self):
        f = parse_inventario_filtros({"incluir_ceros": "1"})
        self.assertTrue(f.incluir_ceros)


class QueryStringTest(SimpleTestCase):
    def test_paginacion_y_marcas(self):
        f = InventarioTablaFiltros(marcas_incluidos=[3], incluir_ceros=True, page=2)
        qs = build_inventario_query_string(f, page=3)
        self.assertIn("marcas_incluidos=3", qs)
        self.assertIn("incluir_ceros=1", qs)
        self.assertIn("page=3", qs)
        self.assertNotIn("ambito=", qs)

    def test_persiste_ambito_terminados(self):
        f = InventarioTablaFiltros(ambito=AMBITO_TERMINADOS)
        qs = build_inventario_query_string(f)
        self.assertIn("ambito=terminados", qs)


class ParsePresentacionTest(SimpleTestCase):
    def test_docenas(self):
        self.assertEqual(parse_presentacion("docenas"), "docenas")

    def test_invalido(self):
        self.assertEqual(parse_presentacion("x"), "unidades")


class AmbitoEtapasTest(SimpleTestCase):
    def test_parse_ambito(self):
        self.assertEqual(parse_ambito(None), AMBITO_FABRICADOS)
        self.assertEqual(parse_ambito("terminados"), AMBITO_TERMINADOS)

    def test_etapas_fabricados(self):
        etapas = etapas_para_ambito(AMBITO_FABRICADOS)
        self.assertEqual(etapas, ETAPAS_FABRICADOS)
        tipos = [t for t, _ in etapas]
        self.assertEqual(tipos, ["Produccion", "SemiElaborado", "2daSeleccion"])
        self.assertNotIn("Terminado", tipos)

    def test_etapas_terminados(self):
        etapas = etapas_para_ambito(AMBITO_TERMINADOS)
        self.assertEqual(etapas, ETAPAS_TERMINADOS)
        self.assertEqual([t for t, _ in etapas], ["Terminado"])


class ArticuloWhereAmbitoTest(SimpleTestCase):
    def test_fabricados_incluye_fabricado_y_2da(self):
        where, params = _build_articulo_where(
            InventarioTablaFiltros(ambito=AMBITO_FABRICADOS)
        )
        self.assertIn("tipo_art_fab", where)
        self.assertIn("IN", where)
        self.assertEqual(params, ["Fabricado", "Fabricado 2da"])

    def test_terminados_solo_terminado(self):
        where, params = _build_articulo_where(
            InventarioTablaFiltros(ambito=AMBITO_TERMINADOS)
        )
        self.assertIn("tipo_art_fab", where)
        self.assertIn("=", where)
        self.assertEqual(params, ["Terminado"])

    def test_busqueda_incluye_talle_y_color_ce(self):
        where, params = _build_articulo_where(
            InventarioTablaFiltros(ambito=AMBITO_TERMINADOS, busqueda="Negro"),
            alias_ce="avce",
        )
        self.assertIn("avce.valor1", where)
        self.assertIn("avce.valor2", where)
        self.assertIn("NombreArticulo", where)
        self.assertEqual(params[0], "Terminado")
        self.assertEqual(params.count("%Negro%"), 7)

class StockPositivoExprTest(SimpleTestCase):
    def test_exige_saldo_positivo_en_alguna_etapa_todas(self):
        expresion = _sql_tiene_stock_positivo_expr()

        self.assertIn(" OR ", expresion)
        self.assertIn("COALESCE(agg.`Produccion`, 0) > 0", expresion)
        self.assertIn("COALESCE(agg.`SemiElaborado`, 0) > 0", expresion)
        self.assertIn("COALESCE(agg.`2daSeleccion`, 0) > 0", expresion)
        self.assertIn("COALESCE(agg.`Terminado`, 0) > 0", expresion)

    def test_solo_etapas_fabricados(self):
        expresion = _sql_tiene_stock_positivo_expr(etapas=ETAPAS_FABRICADOS)
        self.assertIn("COALESCE(agg.`Produccion`, 0) > 0", expresion)
        self.assertIn("COALESCE(agg.`2daSeleccion`, 0) > 0", expresion)
        self.assertNotIn("Terminado", expresion)

    def test_solo_etapas_terminados(self):
        expresion = _sql_tiene_stock_positivo_expr(etapas=ETAPAS_TERMINADOS)
        self.assertEqual(expresion, "(COALESCE(agg.`Terminado`, 0) > 0)")

    def test_consolidado_fabricados(self):
        expr = _sql_consolidado_expr(etapas=ETAPAS_FABRICADOS)
        self.assertIn("Produccion", expr)
        self.assertIn("SemiElaborado", expr)
        self.assertIn("2daSeleccion", expr)
        self.assertNotIn("Terminado", expr)

    def test_consolidado_terminados(self):
        expr = _sql_consolidado_expr(etapas=ETAPAS_TERMINADOS)
        self.assertEqual(expr, "(COALESCE(agg.`Terminado`, 0))")


class FiltroStockPositivoSqlTest(SimpleTestCase):
    def _cursor_contexto(self, *, filas):
        cursor = MagicMock()
        contexto = MagicMock()
        contexto.__enter__.return_value = cursor
        contexto.__exit__.return_value = None
        cursor.fetchone.side_effect = [{"n": 1}, {"n": 1}]
        cursor.fetchall.return_value = filas
        return cursor, contexto

    @patch("stock.services.inventario_tabla._nombre_tabla")
    @patch("stock.services.inventario_tabla.mysql_cursor")
    def test_tabla_usa_where_para_stock_positivo(self, mock_mysql_cursor, mock_nombre_tabla):
        cursor, contexto = self._cursor_contexto(filas=[{
            "id_articulo": 7,
            "id_manual": "T-7",
            "cod_art_prov": "",
            "nombre_articulo": "Terminado",
            "Terminado": 3,
            "consolidado": 3,
        }])
        mock_mysql_cursor.return_value = contexto
        mock_nombre_tabla.side_effect = [
            "stock_deposito", "deposito", "articulo", "articulo_valor_ce",
        ]

        resultado = consultar_inventario_tabla(
            "empresa",
            InventarioTablaFiltros(ambito=AMBITO_TERMINADOS),
        )

        sqls = [llamada.args[0] for llamada in cursor.execute.call_args_list]
        sql_count = next(sql for sql in sqls if "FROM (SELECT a.IDArt" in sql)
        sql_filas = next(sql for sql in sqls if "SELECT a.IDArt AS id_articulo" in sql)
        condicion = "COALESCE(agg.`Terminado`, 0) > 0"
        self.assertIn(f"WHERE COALESCE(TRIM(a.tipo_art_fab), '') = %s AND ({condicion})", sql_count)
        self.assertIn(f"WHERE COALESCE(TRIM(a.tipo_art_fab), '') = %s AND ({condicion})", sql_filas)
        self.assertNotIn("HAVING", sql_count)
        self.assertNotIn("HAVING", sql_filas)
        self.assertEqual(resultado["total_registros"], 1)
        self.assertEqual(resultado["filas"][0]["id_articulo"], 7)

    @patch("stock.services.inventario_tabla._nombre_tabla")
    @patch("stock.services.inventario_tabla.mysql_cursor")
    def test_busqueda_usa_where_para_stock_positivo(self, mock_mysql_cursor, mock_nombre_tabla):
        cursor, contexto = self._cursor_contexto(filas=[{
            "id_articulo": 7,
            "id_manual": "T-7",
            "cod_art_prov": "",
            "nombre_articulo": "Terminado",
            "consolidado": 3,
        }])
        mock_mysql_cursor.return_value = contexto
        mock_nombre_tabla.side_effect = [
            "stock_deposito", "deposito", "articulo", "articulo_valor_ce",
        ]

        resultado = buscar_articulos_inventario(
            "empresa",
            "te",
            ambito=AMBITO_TERMINADOS,
        )

        sql = cursor.execute.call_args.args[0]
        self.assertIn(
            "AND (COALESCE(agg.`Terminado`, 0) > 0) ORDER BY",
            sql,
        )
        self.assertIn("avce.valor1", sql)
        self.assertIn("avce.valor2", sql)
        self.assertNotIn("HAVING", sql)
        self.assertEqual(resultado[0]["id_articulo"], 7)
