"""Tests listado tablero Armado 1ra por stock Semi (max_armable)."""
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mpr.services import listar_tablero_armado


def _fake_mysql_cursor(rows):
    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    cursor.fetchone.return_value = rows[0] if rows else None

    @contextmanager
    def _ctx(*_args, **_kwargs):
        yield cursor

    return _ctx


PACK_33 = {
    "id_articulo": 33,
    "codigo_articulo": "1.1.0033",
    "descripcion_articulo": "Pack terminado prueba",
}


class ListarTableroArmado1raSemiTest(SimpleTestCase):
    @patch("mpr.services._fetch_codigo_marca_articulo", return_value={})
    @patch("mpr.services._nombre_tabla", return_value="articulo")
    @patch(
        "mpr.services.mysql_cursor",
        side_effect=_fake_mysql_cursor([
            {"id_articulo": 33, "stock_reserva": 0},
        ]),
    )
    @patch(
        "mpr.services.obtener_pp_ped_y_stock_pack_por_articulos",
        return_value={
            33: {
                "stock_terminado": 3143,
                "cantidad_pedida_pedido": 0,
            },
        },
    )
    @patch("mpr.services._max_packs_armado_1ra_bulk", return_value={33: 915})
    @patch("mpr.services.get_deposito_semi_elaborado_mpr", return_value=3)
    @patch("mpr.services.listar_packs_armado_1ra", return_value=[PACK_33])
    @patch("mpr.services.listar_demanda_pack_desde_pedidos", return_value=[])
    def test_incluye_pack_sin_demanda_si_max_armable_positivo(self, *_mocks):
        filas = listar_tablero_armado("emp", modo="1ra")
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["id_articulo"], 33)
        self.assertEqual(filas[0]["max_armable"], 915)
        self.assertEqual(filas[0]["resta_armar"], 0)
        self.assertEqual(filas[0]["stock_terminado"], 3143)
        self.assertTrue(filas[0]["tiene_bom"])

    @patch("mpr.services._fetch_codigo_marca_articulo", return_value={})
    @patch("mpr.services._max_packs_armado_1ra_bulk", return_value={33: 0})
    @patch("mpr.services.get_deposito_semi_elaborado_mpr", return_value=3)
    @patch("mpr.services.listar_packs_armado_1ra", return_value=[PACK_33])
    @patch("mpr.services.listar_demanda_pack_desde_pedidos", return_value=[])
    def test_excluye_pack_si_max_armable_cero(self, *_mocks):
        filas = listar_tablero_armado("emp", modo="1ra")
        self.assertEqual(filas, [])
