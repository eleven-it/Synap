"""Tests columna 1er fecha entrega — tablero Armado (paridad PCP)."""
from datetime import date
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mpr.services import (
    _formatear_fecha_entrega_ui,
    listar_demanda_pack_desde_pedidos,
)


class FormatearFechaEntregaUiTest(SimpleTestCase):
    def test_fecha_dd_mm_yyyy(self):
        self.assertEqual(_formatear_fecha_entrega_ui(date(2026, 2, 27)), "27/02/2026")

    def test_none_muestra_guion(self):
        self.assertEqual(_formatear_fecha_entrega_ui(None), "—")

    def test_string_iso(self):
        self.assertEqual(_formatear_fecha_entrega_ui("2026-02-27"), "27/02/2026")


class DemandaPackPrimeraFechaEntregaTest(SimpleTestCase):
    @patch("mpr.services._ventana_pack_stock_maps")
    @patch("mpr.services.mysql_cursor")
    @patch("mpr.services.columna_existe", return_value=True)
    @patch("mpr.services._nombre_tabla")
    def test_min_fecha_entrega_por_articulo(
        self, mock_nombre, _col_existe, mock_cursor_ctx, mock_stock_maps
    ):
        mock_stock_maps.return_value = ({101: 0.0}, {})

        def nombre_side(cursor, name):
            return {
                "stockp": "stockp",
                "comp_ped": "comp_ped",
                "articulo": "articulo",
                "stock_deposito": "stock_deposito",
                "deposito": "deposito",
            }.get(name)

        mock_nombre.side_effect = nombre_side

        cursor = MagicMock()
        cursor.fetchone.side_effect = [None, None]  # estado_pedido_opt checks
        cursor.fetchall.side_effect = [
            [
                {"id_articulo": 101, "cantidad": 10, "fecha_entrega": date(2026, 3, 15)},
                {"id_articulo": 101, "cantidad": 5, "fecha_entrega": date(2026, 2, 27)},
            ],
            [{"IDArt": 101, "stock_reserva": 0}],
        ]
        mock_cursor_ctx.return_value.__enter__.return_value = cursor

        filas = listar_demanda_pack_desde_pedidos("emp_test", limit=10)
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["id_articulo"], 101)
        self.assertEqual(filas[0]["primera_fecha_entrega"], "2026-02-27")
