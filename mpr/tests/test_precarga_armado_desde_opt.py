"""Precarga del carrito Armado 1ra desde listado/detalle OPT."""
from unittest.mock import patch

from django.test import SimpleTestCase

from mpr.services import construir_items_precarga_armado_desde_opt


class PrecargaArmadoDesdeOptTest(SimpleTestCase):
    @patch("mpr.services._bom_lineas_para_precarga_armado")
    @patch("mpr.services.bulk_restante_armar_opt_listado")
    @patch("mpr.services.bulk_id_en_abm")
    @patch("mpr.services.get_opt_detalle")
    def test_usa_misma_logica_que_listado_opt(
        self, mock_opt, mock_abm, mock_restante, mock_bom
    ):
        mock_opt.return_value = [{
            "id_articulo": 489,
            "codigo_articulo": "1.1.486",
            "descripcion_articulo": "Pack test",
        }]
        mock_abm.return_value = {489: 1001}
        mock_restante.return_value = {"11:489": 10}
        mock_bom.return_value = [
            {"id_articulo": 813, "cantidad_por_pack": 3, "codigo_articulo": "C1"},
        ]
        items = construir_items_precarga_armado_desde_opt("empresa_test", 11, 489)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id_articulo_pack"], 489)
        self.assertEqual(items[0]["cantidad_packs"], 10)
        mock_restante.assert_called_once()
        mock_bom.assert_called_once_with("empresa_test", 489, 1001)

    @patch("mpr.services.get_opt_detalle", return_value=[])
    def test_sin_lineas_opt_devuelve_vacio(self, _mock):
        self.assertEqual(
            construir_items_precarga_armado_desde_opt("empresa_test", 11),
            [],
        )
