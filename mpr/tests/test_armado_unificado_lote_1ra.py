"""Tests Armado 1ra: BOM anti-tamper y validación de composición."""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mpr.services import (
    calcular_max_packs_armado_1ra,
    lineas_bom_pack_1ra,
    validar_composicion_bom_1ra,
)


class ValidarComposicionBom1raTest(SimpleTestCase):
    @patch("mpr.services.lineas_bom_pack_1ra")
    def test_rechaza_composicion_distinta_al_bom(self, mock_lineas):
        mock_lineas.return_value = [
            {"id_articulo": 813, "cantidad_por_pack": 3},
        ]
        ok, err = validar_composicion_bom_1ra(
            "emp",
            100,
            [{"id_articulo": 813, "cantidad_por_pack": 2}],
        )
        self.assertFalse(ok)
        self.assertIn("lista de materiales", (err or "").lower())

    @patch("mpr.services.lineas_bom_pack_1ra")
    def test_acepta_composicion_identica(self, mock_lineas):
        mock_lineas.return_value = [
            {"id_articulo": 813, "cantidad_por_pack": 3},
        ]
        ok, err = validar_composicion_bom_1ra(
            "emp",
            100,
            [{"id_articulo": 813, "cantidad_por_pack": 3}],
        )
        self.assertTrue(ok)
        self.assertIsNone(err)


class CalcularMaxPacksArmado1raTest(SimpleTestCase):
    @patch("mpr.services.mysql_cursor")
    @patch("mpr.services._nombre_tabla", return_value="stock_deposito")
    @patch("mpr.services.lineas_bom_pack_1ra")
    def test_max_packs_limitado_por_componente_escaso(self, mock_lineas, _tbl, mock_cursor_ctx):
        mock_lineas.return_value = [
            {"id_articulo": 813, "cantidad_por_pack": 3},
            {"id_articulo": 900, "cantidad_por_pack": 1},
        ]
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {"id_articulo": 813, "saldo": 5},
            {"id_articulo": 900, "saldo": 10},
        ]
        mock_cursor_ctx.return_value.__enter__.return_value = cursor
        n = calcular_max_packs_armado_1ra("emp", 100, deposito_semi=3)
        self.assertEqual(n, 1)

    @patch("mpr.services.articulo_habilitado_armado_1ra", return_value=False)
    def test_pack_no_habilitado_devuelve_cero(self, _hab):
        self.assertEqual(calcular_max_packs_armado_1ra("emp", 999, deposito_semi=3), 0)


class LineasBomPack1raTest(SimpleTestCase):
    @patch("mpr.services.get_bom_detalle")
    @patch("mpr.services.get_id_en_abm_por_articulo", return_value=50)
    @patch("mpr.services.articulo_habilitado_armado_1ra", return_value=True)
    def test_lineas_desde_bom(self, _hab, _abm, mock_bom):
        mock_bom.return_value = {
            "componentes": [
                {
                    "id_articulo": 813,
                    "cantidad_articulo": 3,
                    "codigo_articulo": "M1",
                    "descripcion_articulo": "Media",
                }
            ]
        }
        lineas = lineas_bom_pack_1ra("emp", 100)
        self.assertEqual(len(lineas), 1)
        self.assertEqual(lineas[0]["cantidad_por_pack"], 3)
