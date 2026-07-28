"""Regresión: listar_unidades_desde_seleccion debe pedir cant. fabricar bruta (sin restar Semi en ese campo)."""
from unittest.mock import patch

from django.test import SimpleTestCase


class ListarUnidadesDesdeSeleccionFlagTest(SimpleTestCase):
    @patch("mpr.services._listar_unidades_por_demanda")
    @patch("mpr.services._explosion_demanda_componentes_pedido_reserva_pack")
    @patch("mpr.services.bulk_bom_detalle")
    @patch("mpr.services.bulk_id_en_abm")
    @patch("mpr.services.obtener_pp_ped_y_stock_pack_por_articulos")
    def test_llama_listar_unidades_sin_restar_saldo_semi_en_cant_fabricar(
        self,
        mock_refresco,
        mock_bulk_abm,
        mock_bulk_bom,
        mock_explosion,
        mock_listar_ud,
    ):
        mock_refresco.return_value = {100: {"cantidad_pedida_pedido": 0.0, "stock_terminado": 0.0}}
        mock_bulk_abm.return_value = {100: 1}
        mock_bulk_bom.return_value = {}
        mock_explosion.return_value = ({}, {}, {})
        mock_listar_ud.return_value = []

        from mpr.services import listar_unidades_desde_seleccion

        filas = [{"id_articulo": 100, "cantidad_a_fabricar": 10}]
        out = listar_unidades_desde_seleccion("base_prueba", filas, limit=50)

        self.assertEqual(out, [])
        mock_listar_ud.assert_called_once()
        self.assertEqual(
            mock_listar_ud.call_args.kwargs.get("restar_saldo_semi_en_cant_fabricar"),
            False,
        )
