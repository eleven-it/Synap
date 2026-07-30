"""Tests API catálogo lazy Armado y bulk renglones modal."""
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, SimpleTestCase

from mpr.services import listar_packs_armado_catalogo
from mpr.views import ArmadoPacksCatalogAPIView, _build_renglones_modal_map


class MaxPacksArmado1raBulkTest(SimpleTestCase):
    @patch("mpr.services.mysql_cursor")
    @patch("mpr.services._nombre_tabla")
    def test_bulk_limita_por_componente_escaso(self, mock_nombre, mock_cursor_ctx):
        from mpr.services import _max_packs_armado_1ra_bulk

        mock_nombre.side_effect = lambda _c, t: t
        cursor = MagicMock()
        cursor.fetchall.side_effect = [
            [{"id_articulo": 100, "id_en_abm": 50}],
            [
                {"id_en_abm": 50, "id_articulo": 813, "cantidad_articulo": 3},
                {"id_en_abm": 50, "id_articulo": 900, "cantidad_articulo": 1},
            ],
            [
                {"id_articulo": 813, "saldo": 5},
                {"id_articulo": 900, "saldo": 10},
            ],
        ]
        mock_cursor_ctx.return_value.__enter__.return_value = cursor
        out = _max_packs_armado_1ra_bulk("emp", [100], 3)
        self.assertEqual(out[100], 1)

    @patch("mpr.services.mysql_cursor")
    @patch("mpr.services._nombre_tabla")
    def test_bulk_respeta_componente_sin_stock(self, mock_nombre, mock_cursor_ctx):
        from mpr.services import _max_packs_armado_1ra_bulk

        mock_nombre.side_effect = lambda _c, t: t
        cursor = MagicMock()
        cursor.fetchall.side_effect = [
            [{"id_articulo": 100, "id_en_abm": 50}],
            [
                {"id_en_abm": 50, "id_articulo": 813, "cantidad_articulo": 1},
                {"id_en_abm": 50, "id_articulo": 900, "cantidad_articulo": 1},
            ],
            [
                {"id_articulo": 813, "saldo": 0},
                {"id_articulo": 900, "saldo": 10},
            ],
        ]
        mock_cursor_ctx.return_value.__enter__.return_value = cursor

        out = _max_packs_armado_1ra_bulk("emp", [100], 3)

        self.assertEqual(out[100], 0)


class ListarPacksArmadoCatalogoTest(SimpleTestCase):
    @patch("mpr.services.get_deposito_semi_elaborado_mpr", return_value=None)
    @patch("mpr.services.mysql_cursor")
    @patch("mpr.services._tablas_armado_1ra")
    @patch("mpr.services._nombre_tabla")
    @patch("mpr.services._fragmento_sql_cantidad_promedio_bulto", return_value=", 12 AS cantidad_promedio_bulto")
    def test_modo_1ra_con_busqueda_aplica_limit(
        self, _bulto, mock_nombre, mock_tablas, mock_cursor_ctx, _dep
    ):
        mock_tablas.return_value = ("articulo", "en_abm", "en_abm_formula")
        mock_nombre.return_value = "articulo"
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {
                "id_articulo": 10,
                "codigo_articulo": "PK1",
                "descripcion_articulo": "Pack uno",
                "cantidad_promedio_bulto": 12,
            }
        ]
        mock_cursor_ctx.return_value.__enter__.return_value = cursor

        out = listar_packs_armado_catalogo("emp", "1ra", busqueda="pk", limit=25)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["id_articulo"], 10)
        sql = cursor.execute.call_args[0][0]
        self.assertIn("LIKE", sql)
        self.assertIn("LIMIT", sql)

    @patch("mpr.services._max_packs_armado_1ra_bulk")
    @patch("mpr.services.get_deposito_semi_elaborado_mpr", return_value=3)
    @patch("mpr.services.mysql_cursor")
    @patch("mpr.services._tablas_armado_1ra")
    @patch("mpr.services._nombre_tabla")
    @patch("mpr.services._fragmento_sql_cantidad_promedio_bulto", return_value=", 12 AS cantidad_promedio_bulto")
    def test_modo_1ra_filtra_packs_sin_stock(
        self, _bulto, mock_nombre, mock_tablas, mock_cursor_ctx, _dep, mock_bulk
    ):
        mock_tablas.return_value = ("articulo", "en_abm", "en_abm_formula")
        mock_nombre.return_value = "articulo"
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {"id_articulo": 10, "codigo_articulo": "PK1", "descripcion_articulo": "A", "cantidad_promedio_bulto": 12},
            {"id_articulo": 11, "codigo_articulo": "PK2", "descripcion_articulo": "B", "cantidad_promedio_bulto": 12},
        ]
        mock_cursor_ctx.return_value.__enter__.return_value = cursor
        mock_bulk.return_value = {10: 2, 11: 0}

        out = listar_packs_armado_catalogo("emp", "1ra", busqueda="pk", limit=25, deposito_semi=3)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["id_articulo"], 10)
        self.assertEqual(out[0]["max_packs"], 2)


class ArmadoPacksCatalogAPIViewTest(SimpleTestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.view = ArmadoPacksCatalogAPIView()

    @patch("mpr.views.listar_packs_armado_catalogo")
    @patch("mpr.views._get_base_empresa", return_value="emp")
    def test_get_devuelve_packs(self, _base, mock_listar):
        mock_listar.return_value = [{"id_articulo": 1, "codigo_articulo": "A"}]
        req = self.rf.get("/api/armado/packs-catalog/?modo=1ra&q=ab")
        resp = self.view.get(req)
        self.assertEqual(resp.status_code, 200)
        import json as _json

        data = _json.loads(resp.content)
        self.assertEqual(len(data["packs"]), 1)
        mock_listar.assert_called_once()


class BuildRenglonesModalMapBulkTest(SimpleTestCase):
    @patch("mpr.views.build_grupos_articulo_renglones_movimiento", return_value=[])
    @patch("mpr.views.obtener_renglones_movimiento_bulk")
    def test_usa_bulk_en_lugar_de_loop(self, mock_bulk, _grupos):
        mock_bulk.return_value = {100: [{"IDArt": 1}]}
        opp = [{"codigo_movimiento": 100}]
        out = _build_renglones_modal_map("emp", opp, [])
        self.assertIn("100", out)
        mock_bulk.assert_called_once_with("emp", [100])
