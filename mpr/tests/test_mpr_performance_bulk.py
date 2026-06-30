"""Tests bulk performance helpers (equivalentes pack, detalle OPT, unidades selección)."""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mpr.services import (
    bulk_componentes_a_equivalentes_pack,
    componentes_a_equivalentes_pack,
    get_depositos_con_suma_stock,
    get_op_detalle_bulk,
    listar_unidades_desde_seleccion,
)
from mpr.request_scope_cache import reset_mpr_request_caches


class BulkComponentesEquivalentesPackTest(SimpleTestCase):
    @patch("mpr.services.bulk_bom_detalle")
    @patch("mpr.services.bulk_id_en_abm")
    def test_bulk_una_query_bom_para_varios_packs(self, mock_abm, mock_bom):
        mock_abm.return_value = {10: 100, 20: 200}
        mock_bom.return_value = {
            100: {
                "componentes": [
                    {"id_articulo": 501, "cantidad_articulo": 3},
                ],
            },
            200: {
                "componentes": [
                    {"id_articulo": 502, "cantidad_articulo": 2},
                ],
            },
        }
        opp = {501: 9, 502: 4}
        out = bulk_componentes_a_equivalentes_pack("emp", [10, 20, 10], opp)
        self.assertEqual(out[10], 3)
        self.assertEqual(out[20], 2)
        mock_abm.assert_called_once()
        mock_bom.assert_called_once()

    @patch("mpr.services.bulk_componentes_a_equivalentes_pack")
    def test_singular_delega_en_bulk(self, mock_bulk):
        mock_bulk.return_value = {5: 7}
        self.assertEqual(
            componentes_a_equivalentes_pack("emp", 5, {5: 7}),
            7,
        )
        mock_bulk.assert_called_once_with("emp", [5], {5: 7})


class GetOpDetalleBulkTest(SimpleTestCase):
    @patch("mpr.services.get_op_detalle")
    def test_un_solo_id_delega_en_get_op_detalle(self, mock_single):
        mock_single.return_value = [{"id_lista_produccion": 1}]
        out = get_op_detalle_bulk("emp", [1])
        self.assertEqual(len(out), 1)
        mock_single.assert_called_once_with("emp", 1)

    @patch("mpr.services.mysql_cursor")
    @patch("mpr.services._nombre_tabla")
    def test_varios_ids_una_sola_query(self, mock_nombre, mock_cursor_ctx):
        mock_nombre.side_effect = lambda _c, n: n
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {
                "id_lista_produccion": 1,
                "id_articulo": 100,
                "codigo_articulo": "P1",
                "descripcion_articulo": "Pack 1",
                "cantidad_pedida": 10,
                "cantidad_pendiente_prod": 5,
                "cantidad_asignada_opt": 10,
                "en_proceso_produccion": "Si",
                "id_operario_opt": None,
            },
            {
                "id_lista_produccion": 2,
                "id_articulo": 101,
                "codigo_articulo": "P2",
                "descripcion_articulo": "Pack 2",
                "cantidad_pedida": 8,
                "cantidad_pendiente_prod": 0,
                "cantidad_asignada_opt": 8,
                "en_proceso_produccion": "Si",
                "id_operario_opt": None,
            },
        ]
        mock_cursor_ctx.return_value.__enter__.return_value = cursor

        out = get_op_detalle_bulk("emp", [1, 2])
        self.assertEqual(len(out), 2)
        sql = cursor.execute.call_args_list[0][0][0]
        self.assertIn("id_lista_produccion IN", sql)


class ListarUnidadesDesdeSeleccionRefrescoTest(SimpleTestCase):
    @patch("mpr.services._listar_unidades_por_demanda", return_value=[])
    @patch("mpr.services._explosion_demanda_componentes_pedido_reserva_pack", return_value=({}, {}))
    @patch("mpr.services.bulk_bom_detalle", return_value={})
    @patch("mpr.services.bulk_id_en_abm", return_value={100: 1})
    @patch("mpr.services.listar_ventana_pack")
    @patch("mpr.services.obtener_pp_ped_y_stock_pack_por_articulos")
    def test_siempre_refresca_pp_ped_y_stock_liviano(
        self, mock_refresco, mock_vp, mock_abm, mock_bom, mock_explosion, mock_listar_ud
    ):
        mock_refresco.return_value = {
            100: {"cantidad_pedida_pedido": 25.0, "stock_terminado": 3.0},
        }
        filas = [{
            "id_articulo": 100,
            "cantidad_a_fabricar": 10,
            "cantidad_pedida_pedido": 1.0,
            "stock_terminado": 99.0,
        }]
        listar_unidades_desde_seleccion("emp", filas, limit=50)
        mock_refresco.assert_called_once_with("emp", [100])
        mock_vp.assert_not_called()
        filas_enriq = mock_explosion.call_args[0][0]
        self.assertEqual(filas_enriq[0]["cantidad_pedida_pedido"], 25.0)
        self.assertEqual(filas_enriq[0]["stock_terminado"], 3.0)

    @patch("mpr.services._listar_unidades_por_demanda", return_value=[])
    @patch("mpr.services._explosion_demanda_componentes_pedido_reserva_pack", return_value=({}, {}))
    @patch("mpr.services.bulk_bom_detalle", return_value={})
    @patch("mpr.services.bulk_id_en_abm", return_value={100: 1})
    @patch("mpr.services.obtener_pp_ped_y_stock_pack_por_articulos")
    def test_reutiliza_refresco_precalculado(self, mock_refresco, *_mocks):
        precalc = {100: {"cantidad_pedida_pedido": 10.0, "stock_terminado": 2.0}}
        filas = [{"id_articulo": 100, "cantidad_a_fabricar": 5}]
        listar_unidades_desde_seleccion("emp", filas, limit=50, refresco_pack=precalc)
        mock_refresco.assert_not_called()


class GetDepositosConSumaStockCacheTest(SimpleTestCase):
    def tearDown(self):
        reset_mpr_request_caches()
        super().tearDown()

    @patch("mpr.services._get_depositos_core")
    @patch("mpr.services.mysql_cursor")
    @patch("mpr.services._nombre_tabla")
    def test_sin_middleware_no_cachea(self, mock_nombre, mock_cursor_ctx, mock_core):
        mock_core.return_value = [{"CodDeposito": 1, "NombreDeposito": "Central"}]
        mock_nombre.return_value = "deposito"
        cursor = MagicMock()
        cursor.fetchall.return_value = [{"CodDeposito": 1, "suma_stock": "Si"}]
        mock_cursor_ctx.return_value.__enter__.return_value = cursor

        get_depositos_con_suma_stock("emp", 5)
        get_depositos_con_suma_stock("emp", 5)
        self.assertEqual(mock_core.call_count, 2)

    @patch("core.mysql_pool.request_mysql_conn_var")
    @patch("mpr.services._get_depositos_core")
    @patch("mpr.services.mysql_cursor")
    @patch("mpr.services._nombre_tabla")
    def test_con_request_mysql_cachea_por_base_y_puesto(
        self, mock_nombre, mock_cursor_ctx, mock_core, mock_conn_var
    ):
        mock_conn_var.get.return_value = ("emp", MagicMock())
        mock_core.return_value = [{"CodDeposito": 1, "NombreDeposito": "Central"}]
        mock_nombre.return_value = "deposito"
        cursor = MagicMock()
        cursor.fetchall.return_value = [{"CodDeposito": 1, "suma_stock": "Si"}]
        mock_cursor_ctx.return_value.__enter__.return_value = cursor

        out1 = get_depositos_con_suma_stock("emp", 5)
        out2 = get_depositos_con_suma_stock("emp", 5)
        self.assertEqual(mock_core.call_count, 1)
        self.assertEqual(out1, out2)
        out1[0]["suma_stock"] = "No"
        self.assertEqual(out2[0]["suma_stock"], "Si")
