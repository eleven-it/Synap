"""Tests listado tablero Armado 2da por tipo_art_fab + stock."""
from unittest.mock import patch

from django.test import SimpleTestCase

from mpr.services import listar_tablero_armado


class ListarTableroArmado2daTest(SimpleTestCase):
    @patch("mpr.services._fetch_codigo_marca_articulo", return_value={1371: 13})
    @patch("mpr.services._stock_deposito_por_articulos", return_value={1371: 0.0})
    @patch("mpr.services._max_packs_armado_1ra_bulk", return_value={1371: 0})
    @patch("mpr.services.lineas_bom_pack_1ra", return_value=[])
    @patch("mpr.services._hay_stock_tipo_en_deposito", return_value=True)
    @patch("mpr.services.get_deposito_terminado_mpr", return_value=6)
    @patch("mpr.services.get_deposito_2da_seleccion_mpr", return_value=4)
    @patch(
        "mpr.services.listar_packs_armado_surtido",
        return_value=[{
            "id_articulo": 1371,
            "codigo_articulo": "1.1.1366",
            "descripcion_articulo": "Pack 2da prueba",
        }],
    )
    def test_lista_fabricado_2da_sin_bom_si_hay_stock_fabricado(self, *_mocks):
        filas = listar_tablero_armado("emp", modo="2da", solo_resta=True)
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["id_articulo"], 1371)
        self.assertFalse(filas[0]["tiene_bom"])
        self.assertTrue(filas[0]["armable"])

    @patch("mpr.services._hay_stock_tipo_en_deposito", return_value=False)
    @patch("mpr.services.get_deposito_terminado_mpr", return_value=6)
    @patch("mpr.services.get_deposito_2da_seleccion_mpr", return_value=4)
    @patch(
        "mpr.services.listar_packs_armado_surtido",
        return_value=[{
            "id_articulo": 1371,
            "codigo_articulo": "1.1.1366",
            "descripcion_articulo": "Pack 2da prueba",
        }],
    )
    @patch("mpr.services.lineas_bom_pack_1ra", return_value=[])
    @patch("mpr.services._max_packs_armado_1ra_bulk", return_value={1371: 0})
    @patch("mpr.services._stock_deposito_por_articulos", return_value={1371: 0.0})
    @patch("mpr.services._fetch_codigo_marca_articulo", return_value={})
    def test_oculta_sin_bom_si_no_hay_stock_fabricado(self, *_mocks):
        filas = listar_tablero_armado("emp", modo="2da", solo_resta=True)
        self.assertEqual(filas, [])
