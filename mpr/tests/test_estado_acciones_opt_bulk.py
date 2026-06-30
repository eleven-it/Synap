"""Tests estado_acciones_opt_bulk (tablero / opt_list sin N+1)."""
from unittest.mock import patch

from django.test import SimpleTestCase

from mpr.services import estado_acciones_opt_bulk


class EstadoAccionesOptBulkTest(SimpleTestCase):
    @patch("mpr.services._stock_deposito_por_articulos", return_value={813: 10.0})
    @patch("mpr.services.get_deposito_produccion_mpr", return_value=3)
    @patch("mpr.services.bulk_bom_detalle", return_value={})
    @patch("mpr.services.bulk_id_en_abm", return_value={})
    @patch("mpr.services._lineas_grupo_opt_bulk")
    def test_bulk_puede_cerrar_sin_pendiente(self, mock_lineas, *_mocks):
        mock_lineas.return_value = {
            10: [{"id_articulo": 100, "cantidad_pendiente_prod": 0}],
            20: [{"id_articulo": 101, "cantidad_pendiente_prod": 5}],
        }
        out = estado_acciones_opt_bulk("emp", [10, 20])
        self.assertTrue(out[10]["puede_cerrar"])
        self.assertFalse(out[10]["puede_crear_opp"])
        self.assertFalse(out[20]["puede_cerrar"])
        self.assertEqual(out[20]["total_pendiente_opp"], 5)

    @patch("mpr.services._stock_deposito_por_articulos", return_value={813: 0.0})
    @patch("mpr.services.get_deposito_produccion_mpr", return_value=3)
    @patch("mpr.services.bulk_bom_detalle")
    @patch("mpr.services.bulk_id_en_abm", return_value={100: 50})
    @patch("mpr.services._lineas_grupo_opt_bulk")
    def test_bulk_sin_stock_no_crea_opp(self, mock_lineas, mock_bom, *_mocks):
        mock_lineas.return_value = {
            42: [{"id_articulo": 100, "cantidad_pendiente_prod": 10}],
        }
        mock_bom.return_value = {
            50: {
                "componentes": [
                    {"id_articulo": 813, "cantidad_articulo": 2},
                ],
            },
        }
        out = estado_acciones_opt_bulk("emp", [42])
        self.assertFalse(out[42]["puede_crear_opp"])

    def test_bulk_lista_vacia(self):
        self.assertEqual(estado_acciones_opt_bulk("emp", []), {})
