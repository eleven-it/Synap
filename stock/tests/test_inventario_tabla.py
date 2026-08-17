# -*- coding: utf-8 -*-
"""Tests servicio inventario tabla MPR."""
from django.test import SimpleTestCase
from unittest.mock import MagicMock, patch

from stock.services.inventario_tabla import (
    AMBITO_FABRICADOS,
    AMBITO_TERMINADOS,
    ETAPAS_FABRICADOS,
    ETAPAS_TERMINADOS,
    FILTRO_STOCK_CON,
    FILTRO_STOCK_SIN,
    FILTRO_STOCK_TODOS,
    InventarioTablaFiltros,
    _build_articulo_where,
    _sql_consolidado_expr,
    _sql_sin_stock_positivo_expr,
    _sql_tiene_stock_positivo_expr,
    _sql_where_filtro_stock,
    build_inventario_query_string,
    buscar_articulos_inventario,
    ce_texto,
    codigo_barras_ean_desde_row,
    codigo_compuesto_articulo,
    consultar_inventario_tabla,
    etapas_para_ambito,
    parse_ambito,
    parse_filtro_stock,
    parse_inventario_filtros,
    parse_presentacion,
    preparar_filas_inventario_presentacion,
    sql_expr_codigo_barras_ean,
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
    def test_default_todos(self):
        f = parse_inventario_filtros({})
        self.assertEqual(f.filtro_stock, FILTRO_STOCK_TODOS)
        self.assertTrue(f.incluir_ceros)
        self.assertEqual(f.presentacion, "unidades")
        self.assertEqual(f.ambito, AMBITO_TERMINADOS)
        self.assertEqual(f.page, 1)

    def test_ambito_terminados(self):
        f = parse_inventario_filtros({"ambito": "terminados"})
        self.assertEqual(f.ambito, AMBITO_TERMINADOS)

    def test_ambito_fabricados(self):
        f = parse_inventario_filtros({"ambito": "fabricados"})
        self.assertEqual(f.ambito, AMBITO_FABRICADOS)

    def test_ambito_invalido(self):
        f = parse_inventario_filtros({"ambito": "otro"})
        self.assertEqual(f.ambito, AMBITO_TERMINADOS)

    def test_marcas_multi(self):
        class Q:
            def get(self, k, d=None):
                return d

            def getlist(self, k):
                return ["3", "7"]

            def __contains__(self, k):
                return False

        f = parse_inventario_filtros(Q(), marcas_getlist=["3", "7"])
        self.assertEqual(f.marcas_incluidos, [3, 7])

    def test_filtro_stock_con(self):
        f = parse_inventario_filtros({"filtro_stock": "con_stock"})
        self.assertEqual(f.filtro_stock, FILTRO_STOCK_CON)
        self.assertFalse(f.incluir_ceros)

    def test_filtro_stock_sin(self):
        f = parse_inventario_filtros({"filtro_stock": "sin_stock"})
        self.assertEqual(f.filtro_stock, FILTRO_STOCK_SIN)
        self.assertTrue(f.incluir_ceros)

    def test_legacy_incluir_ceros_1(self):
        f = parse_inventario_filtros({"incluir_ceros": "1"})
        self.assertEqual(f.filtro_stock, FILTRO_STOCK_TODOS)

    def test_legacy_incluir_ceros_0(self):
        f = parse_inventario_filtros({"incluir_ceros": "0"})
        self.assertEqual(f.filtro_stock, FILTRO_STOCK_CON)


class QueryStringTest(SimpleTestCase):
    def test_paginacion_y_marcas(self):
        f = InventarioTablaFiltros(marcas_incluidos=[3], filtro_stock=FILTRO_STOCK_CON, page=2)
        qs = build_inventario_query_string(f, page=3)
        self.assertIn("marcas_incluidos=3", qs)
        self.assertIn("filtro_stock=con_stock", qs)
        self.assertIn("page=3", qs)
        self.assertNotIn("ambito=", qs)
        self.assertNotIn("incluir_ceros", qs)

    def test_default_todos_no_en_qs(self):
        f = InventarioTablaFiltros()
        qs = build_inventario_query_string(f)
        self.assertNotIn("filtro_stock", qs)
        self.assertNotIn("ambito=", qs)

    def test_persiste_ambito_fabricados(self):
        f = InventarioTablaFiltros(ambito=AMBITO_FABRICADOS)
        qs = build_inventario_query_string(f)
        self.assertIn("ambito=fabricados", qs)


class ParsePresentacionTest(SimpleTestCase):
    def test_docenas(self):
        self.assertEqual(parse_presentacion("docenas"), "docenas")

    def test_invalido(self):
        self.assertEqual(parse_presentacion("x"), "unidades")


class ParseFiltroStockTest(SimpleTestCase):
    def test_aliases(self):
        self.assertEqual(parse_filtro_stock("sin"), FILTRO_STOCK_SIN)
        self.assertEqual(parse_filtro_stock("con"), FILTRO_STOCK_CON)
        self.assertEqual(parse_filtro_stock(None), FILTRO_STOCK_TODOS)


class AmbitoEtapasTest(SimpleTestCase):
    def test_parse_ambito(self):
        self.assertEqual(parse_ambito(None), AMBITO_TERMINADOS)
        self.assertEqual(parse_ambito("fabricados"), AMBITO_FABRICADOS)
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
        self.assertIn("a.tipo_art <> 'Gasto'", where)
        self.assertEqual(params, ["Fabricado", "Fabricado 2da"])

    def test_terminados_incluye_terminado_y_tercero(self):
        where, params = _build_articulo_where(
            InventarioTablaFiltros(ambito=AMBITO_TERMINADOS)
        )
        self.assertIn("tipo_art_fab", where)
        self.assertIn("IN", where)
        self.assertIn("a.tipo_art <> 'Gasto'", where)
        self.assertEqual(params, ["Terminado", "Tercero"])

    def test_busqueda_incluye_talle_y_color_ce(self):
        where, params = _build_articulo_where(
            InventarioTablaFiltros(ambito=AMBITO_TERMINADOS, busqueda="Negro"),
            alias_ce="avce",
        )
        self.assertIn("avce.valor1", where)
        self.assertIn("avce.valor2", where)
        self.assertIn("NombreArticulo", where)
        self.assertEqual(params[:2], ["Terminado", "Tercero"])
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

    def test_sin_stock_es_negacion(self):
        pos = _sql_tiene_stock_positivo_expr(etapas=ETAPAS_TERMINADOS)
        sin = _sql_sin_stock_positivo_expr(etapas=ETAPAS_TERMINADOS)
        self.assertEqual(sin, f"(NOT {pos})")

    def test_where_filtro_stock(self):
        self.assertEqual(_sql_where_filtro_stock(FILTRO_STOCK_TODOS, etapas=ETAPAS_TERMINADOS), "")
        self.assertIn("> 0", _sql_where_filtro_stock(FILTRO_STOCK_CON, etapas=ETAPAS_TERMINADOS))
        self.assertIn("NOT", _sql_where_filtro_stock(FILTRO_STOCK_SIN, etapas=ETAPAS_TERMINADOS))

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
            InventarioTablaFiltros(ambito=AMBITO_TERMINADOS, filtro_stock=FILTRO_STOCK_CON),
        )

        sqls = [llamada.args[0] for llamada in cursor.execute.call_args_list]
        sql_count = next(sql for sql in sqls if "FROM (SELECT a.IDArt" in sql)
        sql_filas = next(sql for sql in sqls if "SELECT a.IDArt AS id_articulo" in sql)
        condicion = "COALESCE(agg.`Terminado`, 0) > 0"
        prefijo = (
            "WHERE (a.IDArt IS NULL OR a.tipo_art IS NULL OR a.tipo_art <> 'Gasto') "
            "AND COALESCE(TRIM(a.tipo_art_fab), '') IN (%s,%s) AND ({condicion})"
        )
        self.assertIn(prefijo.format(condicion=condicion), sql_count)
        self.assertIn(prefijo.format(condicion=condicion), sql_filas)
        self.assertNotIn("HAVING", sql_count)
        self.assertNotIn("HAVING", sql_filas)
        self.assertEqual(resultado["total_registros"], 1)
        self.assertEqual(resultado["filas"][0]["id_articulo"], 7)

    @patch("stock.services.inventario_tabla._nombre_tabla")
    @patch("stock.services.inventario_tabla.mysql_cursor")
    def test_tabla_default_todos_sin_filtro_saldo(self, mock_mysql_cursor, mock_nombre_tabla):
        cursor, contexto = self._cursor_contexto(filas=[{
            "id_articulo": 7,
            "id_manual": "T-7",
            "cod_art_prov": "",
            "nombre_articulo": "Terminado",
            "Terminado": -5,
            "consolidado": -5,
        }])
        mock_mysql_cursor.return_value = contexto
        mock_nombre_tabla.side_effect = [
            "stock_deposito", "deposito", "articulo", "articulo_valor_ce",
        ]

        consultar_inventario_tabla(
            "empresa",
            InventarioTablaFiltros(ambito=AMBITO_TERMINADOS),
        )
        sql_count = next(
            llamada.args[0]
            for llamada in cursor.execute.call_args_list
            if "FROM (SELECT a.IDArt" in llamada.args[0]
        )
        self.assertNotIn("> 0", sql_count.split("WHERE", 1)[-1])

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
            filtro_stock=FILTRO_STOCK_CON,
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

    @patch("stock.services.inventario_tabla._nombre_tabla")
    @patch("stock.services.inventario_tabla.mysql_cursor")
    def test_busqueda_sin_stock(self, mock_mysql_cursor, mock_nombre_tabla):
        cursor, contexto = self._cursor_contexto(filas=[])
        mock_mysql_cursor.return_value = contexto
        mock_nombre_tabla.side_effect = [
            "stock_deposito", "deposito", "articulo", "articulo_valor_ce",
        ]

        buscar_articulos_inventario(
            "empresa",
            "te",
            ambito=AMBITO_TERMINADOS,
            filtro_stock=FILTRO_STOCK_SIN,
        )
        sql = cursor.execute.call_args.args[0]
        self.assertIn("AND (NOT (COALESCE(agg.`Terminado`, 0) > 0))", sql)


class CodigoBarrasEanInventarioTest(SimpleTestCase):
    def test_sql_expr_prioriza_nrocodbarraf(self):
        expr = sql_expr_codigo_barras_ean("a")
        self.assertIn("NroCodBarraF", expr)
        self.assertIn("NroCodBarra", expr)
        self.assertTrue(expr.index("NroCodBarraF") < expr.index("NroCodBarra,"))

    def test_desde_row_prioriza_f(self):
        self.assertEqual(
            codigo_barras_ean_desde_row({"codigo_barras": "779123"}),
            "779123",
        )
        self.assertEqual(
            codigo_barras_ean_desde_row({"ean2": "AAA", "ean1": "BBB"}),
            "AAA",
        )
        self.assertEqual(codigo_barras_ean_desde_row({}), "")

    def test_preparar_propaga_codigo_barras(self):
        filas = preparar_filas_inventario_presentacion(
            [{
                "id_articulo": 1,
                "codigo_barras": "7799999000123",
                "codigo_compuesto": "X",
                "nombre_articulo": "Pack",
                "talle": "T5",
                "color": "Blanco",
                "etapas_saldos": {"Terminado": 0},
                "consolidado": 0,
            }],
            "unidades",
            ambito=AMBITO_TERMINADOS,
        )
        self.assertEqual(filas[0]["codigo_barras"], "7799999000123")

    @patch("stock.services.inventario_tabla._nombre_tabla")
    @patch("stock.services.inventario_tabla.mysql_cursor")
    def test_consultar_incluye_ean_en_select(self, mock_mysql_cursor, mock_nombre_tabla):
        cursor = MagicMock()
        contexto = MagicMock()
        contexto.__enter__.return_value = cursor
        contexto.__exit__.return_value = None
        cursor.fetchone.side_effect = [{"n": 1}, {"n": 1}]
        cursor.fetchall.return_value = [{
            "id_articulo": 7,
            "id_manual": "T-7",
            "cod_art_prov": "",
            "nombre_articulo": "Terminado",
            "codigo_barras": "7790001112223",
            "talle": "",
            "color": "",
            "Terminado": 0,
            "consolidado": 0,
        }]
        mock_mysql_cursor.return_value = contexto
        mock_nombre_tabla.side_effect = [
            "stock_deposito", "deposito", "articulo", "articulo_valor_ce",
        ]

        resultado = consultar_inventario_tabla(
            "empresa",
            InventarioTablaFiltros(ambito=AMBITO_TERMINADOS),
        )
        sql_filas = next(
            llamada.args[0]
            for llamada in cursor.execute.call_args_list
            if "SELECT a.IDArt AS id_articulo" in llamada.args[0]
        )
        self.assertIn("NroCodBarraF", sql_filas)
        self.assertIn("AS codigo_barras", sql_filas)
        self.assertEqual(resultado["filas"][0]["codigo_barras"], "7790001112223")
