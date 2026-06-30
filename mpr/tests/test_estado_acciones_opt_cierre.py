"""Tests cierre OPT sin exigir armado previo."""
from unittest.mock import patch

from django.test import SimpleTestCase

from mpr.services import estado_acciones_opt


class EstadoAccionesOptCierreTest(SimpleTestCase):
    @patch("mpr.services.get_cantidad_opp_por_destino_opt", return_value=({}, {}, {}))
    @patch("mpr.services.get_cantidades_armadas_por_opt", return_value={})
    @patch("mpr.services.get_lineas_armado_opt", return_value=[{"max_packs_armable": 5}])
    @patch("mpr.services.get_opp_componentes_disponibles", return_value=[])
    @patch("mpr.services.get_opt_detalle")
    def test_puede_cerrar_sin_armar_si_opp_cero(self, mock_detalle, *_mocks):
        mock_detalle.return_value = [
            {"id_articulo": 100, "cantidad_pendiente_prod": 0},
        ]
        out = estado_acciones_opt("emp", 42)
        self.assertTrue(out["puede_cerrar"])
        self.assertEqual(out["total_pendiente_opp"], 0)

    @patch("mpr.services.get_cantidad_opp_por_destino_opt", return_value=({}, {}, {}))
    @patch("mpr.services.get_cantidades_armadas_por_opt", return_value={})
    @patch("mpr.services.get_lineas_armado_opt", return_value=[])
    @patch("mpr.services.get_opp_componentes_disponibles", return_value=[])
    @patch("mpr.services.get_opt_detalle")
    def test_no_puede_cerrar_con_opp_pendiente(self, mock_detalle, *_mocks):
        mock_detalle.return_value = [
            {"id_articulo": 100, "cantidad_pendiente_prod": 50},
        ]
        out = estado_acciones_opt("emp", 42)
        self.assertFalse(out["puede_cerrar"])
        self.assertGreater(out["total_pendiente_opp"], 0)
