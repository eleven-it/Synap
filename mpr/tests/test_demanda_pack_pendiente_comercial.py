"""Tests saldo comercial PED (cantidad_pendiente) en demanda pack — sin MySQL real."""
from datetime import date
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mpr.services import (
    _sql_filtros_ped_demanda_comercial,
    _sql_qty_pendiente_comercial_stockp,
    listar_demanda_pack_desde_pedidos,
)

COALESCE_LEGADO = "COALESCE(sp.cantidad, sp.cantidad_pendiente, sp.Cantidad, 0)"


class SqlQtyPendienteComercialStockpTest(SimpleTestCase):
    """Expresión SQL de saldo comercial por renglón stockp."""

    def test_con_pendiente_y_entregada_usa_greatest(self):
        cursor = MagicMock()

        def col_existe(_cur, tabla, columna):
            return tabla == "stockp" and columna in (
                "cantidad_pendiente",
                "cantidad_entregada",
            )

        with patch("mpr.services.columna_existe", side_effect=col_existe):
            sql = _sql_qty_pendiente_comercial_stockp(cursor, "stockp")

        self.assertIn("GREATEST", sql)
        self.assertIn("cantidad_pendiente", sql)
        self.assertIn("cantidad_entregada", sql)
        self.assertNotIn(COALESCE_LEGADO, sql)

    def test_solo_pendiente_sin_resta_entregada(self):
        cursor = MagicMock()

        def col_existe(_cur, tabla, columna):
            if tabla != "stockp":
                return False
            return columna == "cantidad_pendiente"

        with patch("mpr.services.columna_existe", side_effect=col_existe):
            sql = _sql_qty_pendiente_comercial_stockp(cursor, "stockp")

        self.assertIn("GREATEST", sql)
        self.assertIn("cantidad_pendiente", sql)
        self.assertNotIn("cantidad_entregada", sql)
        self.assertNotIn(COALESCE_LEGADO, sql)

    def test_sin_columnas_cae_a_coalesce_legado(self):
        cursor = MagicMock()

        with patch("mpr.services.columna_existe", return_value=False):
            sql = _sql_qty_pendiente_comercial_stockp(cursor, "stockp")

        self.assertEqual(sql, COALESCE_LEGADO)
        self.assertNotIn("GREATEST", sql)


class SqlFiltrosPedDemandaComercialTest(SimpleTestCase):
    """Filtros comerciales de PED (Estado cerrado y remitido_facturado)."""

    def test_con_estado_y_remitido_facturado(self):
        cursor = MagicMock()

        def col_existe(_cur, tabla, columna):
            if tabla == "comp_ped" and columna == "Estado":
                return True
            if tabla == "stockp" and columna == "remitido_facturado":
                return True
            return False

        with patch("mpr.services.columna_existe", side_effect=col_existe):
            sql = _sql_filtros_ped_demanda_comercial(cursor, "comp_ped", "stockp")

        self.assertIn("Facturado", sql)
        self.assertIn("Cerrado", sql)
        self.assertIn("remitido_facturado", sql)
        self.assertIn("<> 'Si'", sql)
        self.assertNotIn("En remito", sql)

    def test_sin_columnas_devuelve_vacio(self):
        cursor = MagicMock()

        with patch("mpr.services.columna_existe", return_value=False):
            sql = _sql_filtros_ped_demanda_comercial(cursor, "comp_ped", "stockp")

        self.assertEqual(sql, "")


class ListarDemandaPackSaldoComercialTest(SimpleTestCase):
    """listar_demanda_pack_desde_pedidos usa saldo comercial en el SQL principal."""

    @patch("mpr.services._ventana_pack_stock_maps")
    @patch("mpr.services.mysql_cursor")
    @patch("mpr.services.columna_existe", return_value=True)
    @patch("mpr.services._nombre_tabla")
    def test_sql_demanda_usa_pendiente_comercial(
        self, mock_nombre, _col_existe, mock_cursor_ctx, mock_stock_maps
    ):
        mock_stock_maps.return_value = ({101: 0.0}, {})

        def nombre_side(_cursor, name):
            return {
                "stockp": "stockp",
                "comp_ped": "comp_ped",
                "articulo": "articulo",
                "stock_deposito": "stock_deposito",
                "deposito": "deposito",
            }.get(name)

        mock_nombre.side_effect = nombre_side

        cursor = MagicMock()
        cursor.fetchone.side_effect = [None, None]
        cursor.fetchall.side_effect = [
            [
                {"id_articulo": 101, "cantidad": 10, "fecha_entrega": date(2026, 3, 15)},
                {"id_articulo": 101, "cantidad": 5, "fecha_entrega": date(2026, 2, 27)},
            ],
            [],
            [{"IDArt": 101, "stock_reserva": 0}],
        ]
        mock_cursor_ctx.return_value.__enter__.return_value = cursor

        listar_demanda_pack_desde_pedidos("emp_test", limit=10)

        sql_ped = None
        for call in cursor.execute.call_args_list:
            sql = call[0][0] if call[0] else ""
            if "FROM stockp" in sql and "AS cantidad" in sql:
                sql_ped = sql
                break

        self.assertIsNotNone(sql_ped, "No se encontró el SQL principal de demanda PED")
        self.assertIn("cantidad_pendiente", sql_ped)
        self.assertIn("Facturado", sql_ped)
        self.assertIn("Cerrado", sql_ped)
        self.assertIn("remitido_facturado", sql_ped)
        self.assertIn("> 0", sql_ped)
        self.assertNotIn(COALESCE_LEGADO, sql_ped)
