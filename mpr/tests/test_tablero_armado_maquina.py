"""Tests: nro. de máquina en tablero de Armado (pack → BOM → asignación)."""

from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase

from mpr.services_maquina_linea import enriquecer_filas_tablero_armado_maquina


class TestArmadoTableroMaquina(SimpleTestCase):
    @patch("mpr.services_maquina_linea.listar_articulos_vigentes_todas_maquinas")
    @patch("mpr.services_maquina_linea.listar_maquinas")
    @patch("mpr.services.bulk_bom_detalle")
    @patch("mpr.services.bulk_id_en_abm")
    def test_pack_hereda_maquina_de_componente_y_ordena(
        self, mock_abm, mock_bom, mock_maqs, mock_arts
    ):
        mock_abm.return_value = {100: 10, 200: 20, 300: 30}
        mock_bom.return_value = {
            10: {"componentes": [{"id_articulo": 11, "cantidad_articulo": 1}]},
            20: {"componentes": [{"id_articulo": 22, "cantidad_articulo": 2}]},
            30: {"componentes": [{"id_articulo": 33, "cantidad_articulo": 1}]},
        }
        mock_maqs.return_value = [
            {"id": 1, "codigo": "26", "nombre": "Máquina 26"},
            {"id": 2, "codigo": "12", "nombre": "Máquina 12"},
        ]
        mock_arts.return_value = {
            1: [{"id_articulo": 11}],
            2: [{"id_articulo": 22}],
        }
        filas = [
            {"id_articulo": 100, "codigo_manual": "P100", "descripcion_articulo": "Pack A"},
            {"id_articulo": 200, "codigo_manual": "P200", "descripcion_articulo": "Pack B"},
            {"id_articulo": 300, "codigo_manual": "P300", "descripcion_articulo": "Pack C"},
        ]
        out = enriquecer_filas_tablero_armado_maquina("emp", filas, fecha=date(2026, 8, 3))
        self.assertEqual([f["maquina_nombre"] for f in out], ["12", "26", "—"])
        self.assertEqual([f["id_articulo"] for f in out], [200, 100, 300])
        self.assertTrue(out[0]["show_maquina"])
        self.assertTrue(out[1]["show_maquina"])
        self.assertTrue(out[2]["show_maquina"])
        self.assertTrue(out[0]["tiene_maquina"])
        self.assertFalse(out[2]["tiene_maquina"])

    @patch("mpr.services_maquina_linea.listar_articulos_vigentes_todas_maquinas")
    @patch("mpr.services_maquina_linea.listar_maquinas")
    @patch("mpr.services.bulk_bom_detalle")
    @patch("mpr.services.bulk_id_en_abm")
    def test_multi_maquina_elige_menor_codigo(
        self, mock_abm, mock_bom, mock_maqs, mock_arts
    ):
        mock_abm.return_value = {50: 5}
        mock_bom.return_value = {
            5: {
                "componentes": [
                    {"id_articulo": 1, "cantidad_articulo": 1},
                    {"id_articulo": 2, "cantidad_articulo": 1},
                ]
            },
        }
        mock_maqs.return_value = [
            {"id": 9, "codigo": "40", "nombre": "M40"},
            {"id": 8, "codigo": "7", "nombre": "M7"},
        ]
        mock_arts.return_value = {
            9: [{"id_articulo": 1}],
            8: [{"id_articulo": 2}],
        }
        filas = [{"id_articulo": 50, "codigo_manual": "PX", "descripcion_articulo": "Pack"}]
        out = enriquecer_filas_tablero_armado_maquina("emp", filas)
        self.assertEqual(out[0]["maquina_nombre"], "7")
        self.assertEqual(len(out[0]["maquinas_asignadas"]), 2)

    def test_sin_base_marca_sin_maquina(self):
        filas = [{"id_articulo": 1, "codigo_manual": "A"}]
        out = enriquecer_filas_tablero_armado_maquina("", filas)
        self.assertEqual(out[0]["maquina_nombre"], "—")
        self.assertEqual(out[0]["id_mpr_maquina"], 0)
