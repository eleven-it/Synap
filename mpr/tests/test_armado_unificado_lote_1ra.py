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
    @patch("mpr.services._max_packs_armado_1ra_bulk")
    def test_max_packs_delega_en_bulk(self, mock_bulk):
        mock_bulk.return_value = {100: 2}
        n = calcular_max_packs_armado_1ra("emp", 100, deposito_semi=3)
        self.assertEqual(n, 2)
        mock_bulk.assert_called_once_with("emp", [100], 3)

    @patch("mpr.services._max_packs_armado_1ra_bulk", return_value={999: 0})
    def test_sin_stock_devuelve_cero(self, _mock_bulk):
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
