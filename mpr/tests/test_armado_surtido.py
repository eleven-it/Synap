"""Tests armado surtido: validaciones previas y selector de packs."""
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from decimal import Decimal

from django.test import SimpleTestCase

from mpr.services import (
    TIPO_ART_FAB_PACK_ARMADO_SURTIDO,
    _mpr_costo_stock_desde_articulo,
    articulo_habilitado_armado_surtido,
    listar_packs_armado_surtido,
    opt_puede_armado_surtido,
    validar_datos_armado_surtido,
)


class ValidarDatosArmadoSurtidoTest(SimpleTestCase):
    def test_rechaza_sin_componentes(self):
        ok, err = validar_datos_armado_surtido(
            1, 10, 20, [], id_operario=5, id_articulo_pack=100
        )
        self.assertFalse(ok)
        self.assertIn("componente", (err or "").lower())

    def test_rechaza_origen_igual_destino(self):
        ok, err = validar_datos_armado_surtido(
            2,
            10,
            10,
            [{"id_articulo": 1, "cantidad_por_pack": 1}],
            id_operario=5,
            id_articulo_pack=100,
        )
        self.assertFalse(ok)
        self.assertIn("distintos", (err or "").lower())

    def test_acepta_sin_operario(self):
        ok, err = validar_datos_armado_surtido(
            1,
            10,
            20,
            [{"id_articulo": 1, "cantidad_por_pack": 2}],
            id_operario=None,
            id_articulo_pack=100,
        )
        self.assertTrue(ok)
        self.assertIsNone(err)

    def test_rechaza_articulo_duplicado(self):
        ok, err = validar_datos_armado_surtido(
            1,
            10,
            20,
            [
                {"id_articulo": 1, "cantidad_por_pack": 1},
                {"id_articulo": 1, "cantidad_por_pack": 2},
            ],
            id_operario=5,
            id_articulo_pack=100,
        )
        self.assertFalse(ok)
        self.assertIn("repetido", (err or "").lower())

    def test_acepta_datos_validos(self):
        ok, err = validar_datos_armado_surtido(
            3,
            10,
            20,
            [
                {"id_articulo": 1, "cantidad_por_pack": 2},
                {"id_articulo": 2, "cantidad_por_pack": 1},
            ],
            id_operario=5,
            id_articulo_pack=100,
        )
        self.assertTrue(ok)
        self.assertIsNone(err)


class MprCostoStockDesdeArticuloTest(SimpleTestCase):
    def test_calcula_precio_costoxr(self):
        pc_u, pc_r = _mpr_costo_stock_desde_articulo(Decimal("10.5"), Decimal("3"))
        self.assertEqual(pc_u, Decimal("10.5"))
        self.assertEqual(pc_r, Decimal("31.5"))


def _fake_mysql_cursor(rows):
    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    cursor.fetchone.return_value = rows[0] if rows else None

    @contextmanager
    def _ctx(*_args, **_kwargs):
        yield cursor

    return _ctx, cursor


class ArticuloHabilitadoArmadoSurtidoTest(SimpleTestCase):
    @patch("mpr.services.columna_existe", return_value=True)
    @patch("mpr.services._nombre_tabla", return_value="articulo")
    def test_habilitado_si_tipo_art_fab_fabricado_2da(self, *_mocks):
        ctx, _cursor = _fake_mysql_cursor([{"IDArt": 999}])
        with patch("mpr.services.mysql_cursor", side_effect=ctx):
            self.assertTrue(articulo_habilitado_armado_surtido("emp", 999))

    @patch("mpr.services.columna_existe", return_value=True)
    @patch("mpr.services._nombre_tabla", return_value="articulo")
    def test_no_habilitado_si_no_existe(self, *_mocks):
        ctx, _cursor = _fake_mysql_cursor([])
        with patch("mpr.services.mysql_cursor", side_effect=ctx):
            self.assertFalse(articulo_habilitado_armado_surtido("emp", 1))


class ListarPacksArmadoSurtidoTest(SimpleTestCase):
    @patch("mpr.services.columna_existe", return_value=True)
    @patch("mpr.services._nombre_tabla", return_value="articulo")
    def test_lista_articulos_fabricado_2da(self, *_mocks):
        rows = [
            {
                "id_articulo": 10,
                "codigo_articulo": "PK01",
                "descripcion_articulo": "Pack surtido A",
            }
        ]
        ctx, cursor = _fake_mysql_cursor(rows)
        with patch("mpr.services.mysql_cursor", side_effect=ctx):
            packs = listar_packs_armado_surtido("emp")
        self.assertEqual(len(packs), 1)
        self.assertEqual(packs[0]["id_articulo"], 10)
        self.assertEqual(packs[0]["codigo_articulo"], "PK01")
        sql = cursor.execute.call_args[0][0]
        params = cursor.execute.call_args[0][1]
        self.assertIn("tipo_art_fab", sql)
        self.assertEqual(params, [TIPO_ART_FAB_PACK_ARMADO_SURTIDO])


class OptPuedeArmadoSurtidoTest(SimpleTestCase):
    def test_sin_id_lista_no_bloquea(self):
        ok, msg = opt_puede_armado_surtido("emp", None)
        self.assertTrue(ok)
        self.assertEqual(msg, "")

    @patch("mpr.services.get_cantidad_opp_2da_seleccion_opt", return_value={10: 5})
    @patch("mpr.services.get_deposito_2da_seleccion_mpr", return_value=3)
    @patch("mpr.services.listar_opp_por_opt", return_value=[{"codigo_movimiento": 1}])
    def test_con_opp_y_2da_seleccion_ok(self, *_mocks):
        ok, msg = opt_puede_armado_surtido("emp", 22)
        self.assertTrue(ok)
        self.assertEqual(msg, "")

    @patch("mpr.services.listar_opp_por_opt", return_value=[])
    def test_sin_opp_bloquea(self, *_mocks):
        ok, msg = opt_puede_armado_surtido("emp", 22)
        self.assertFalse(ok)
        self.assertIn("OPP", msg)

    @patch("mpr.services.get_cantidad_opp_2da_seleccion_opt", return_value={})
    @patch("mpr.services.get_deposito_2da_seleccion_mpr", return_value=3)
    @patch("mpr.services.listar_opp_por_opt", return_value=[{"codigo_movimiento": 1}])
    def test_sin_envio_2da_seleccion_bloquea(self, *_mocks):
        ok, msg = opt_puede_armado_surtido("emp", 22)
        self.assertFalse(ok)
        self.assertIn("2", msg)


class EjecutarArmadoSurtidoWrapperTest(SimpleTestCase):
    @patch("mpr.services.guardar_composicion_armado_surtido")
    @patch("mpr.services.get_connection")
    @patch("mpr.services.articulo_habilitado_armado_surtido", return_value=True)
    @patch("mpr.services._ejecutar_armado_surtido_tx")
    def test_wrapper_delega_y_confirma(self, mock_tx, *_mocks):
        from mpr.services import ejecutar_armado_surtido

        mock_tx.return_value = (
            True,
            17,
            "0001-00000017",
            None,
            [{"id_articulo": 813, "cantidad_por_pack": 2}],
            None,
        )
        conn = MagicMock()
        _mocks[1].return_value.__enter__.return_value = conn
        lineas = [{"id_articulo": 813, "cantidad_por_pack": 2}]
        ok, cod, nro, err = ejecutar_armado_surtido(
            "emp",
            5,
            100,
            2,
            3,
            5,
            lineas,
            id_operario=10,
        )
        self.assertTrue(ok)
        self.assertEqual(cod, 17)
        self.assertEqual(nro, "0001-00000017")
        self.assertIsNone(err)
        conn.commit.assert_called_once()
        _mocks[0].assert_called_once()
        mock_tx.assert_called_once()


class ListarMovimientosArmadoPorFechaTest(SimpleTestCase):
    """Historial por fecha: columnas MSTOCK case-insensitive (administranet1)."""

    @patch("mpr.repositories.armado_surtido.columna_existe", return_value=True)
    @patch("mpr.repositories.armado_surtido.mysql_cursor")
    def test_usa_columnas_snake_case_movimiento_stock(self, mock_cursor_ctx, _mock_col):
        from datetime import date

        from mpr.repositories.armado_surtido import listar_movimientos_armado_por_fecha

        cursor = MagicMock()
        mock_cursor_ctx.return_value.__enter__.return_value = cursor
        mock_cursor_ctx.return_value.__exit__.return_value = False

        mov_row = {
            "id_mpr_armado_surtido_movimiento": 20,
            "codigo_movimiento": 2670,
            "id_articulo_pack": 618,
            "cantidad_packs": 1,
            "modo": "1ra",
            "creado_en": None,
            "id_mpr_armado_lote": 20,
            "fecha_realizado": date(2026, 7, 30),
        }

        def execute_side_effect(sql, params=None):
            cursor._last_sql = sql
            return None

        def fetchone_side_effect():
            sql = (cursor._last_sql or "").lower()
            if "show tables like" in sql:
                return {"Tables_in_x": "x"}
            return None

        fetchall_calls = {"n": 0}

        def fetchall_side_effect():
            sql = (cursor._last_sql or "").lower()
            fetchall_calls["n"] += 1
            if "from mpr_armado_surtido_movimiento" in sql:
                return [mov_row]
            if "show columns from" in sql and "movimiento_stock" in sql:
                return [
                    {"Field": "codigo_movimiento"},
                    {"Field": "nro_comprobante"},
                ]
            if "from movimiento_stock" in sql:
                self.assertIn("`codigo_movimiento`", cursor._last_sql)
                self.assertIn("`nro_comprobante`", cursor._last_sql)
                self.assertNotIn("CodigoMovimiento", cursor._last_sql)
                return [{"codigo": 2670, "nro": "0001-00001229"}]
            if "from articulo" in sql:
                return [{
                    "id_articulo": 618,
                    "codigo": "7944-01",
                    "descripcion": "Crew Heritage",
                }]
            return []

        cursor.execute.side_effect = execute_side_effect
        cursor.fetchone.side_effect = fetchone_side_effect
        cursor.fetchall.side_effect = fetchall_side_effect

        out = listar_movimientos_armado_por_fecha(
            "administranet1",
            fecha_realizado=date(2026, 7, 30),
            modo="1ra",
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["id_articulo_pack"], 618)
        self.assertEqual(out[0]["nro_comprobante"], "0001-00001229")


class ConsolidarArmadosPorArticuloPackTest(SimpleTestCase):
    def test_suma_packs_mismo_id_articulo_pack(self):
        from mpr.services import consolidar_armados_por_articulo_pack

        movs = [
            {
                "id_articulo_pack": 508,
                "codigo_articulo": "508-01",
                "descripcion_articulo": "Pack demo",
                "cantidad_packs": 5,
            },
            {
                "id_articulo_pack": 508,
                "codigo_articulo": "508-01",
                "descripcion_articulo": "Pack demo",
                "cantidad_packs": 5,
            },
            {
                "id_articulo_pack": 200,
                "codigo_articulo": "200-01",
                "descripcion_articulo": "Otro pack",
                "cantidad_packs": 2,
            },
        ]
        out = consolidar_armados_por_articulo_pack(movs)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["id_articulo_pack"], 508)
        self.assertEqual(out[0]["cantidad_packs"], 10)
        self.assertEqual(out[1]["cantidad_packs"], 2)

    @patch("mpr.repositories.armado_surtido.listar_movimientos_armado_por_fecha")
    def test_listar_armados_consolida_por_defecto(self, mock_listar):
        from datetime import date

        from mpr.services import listar_armados_realizados_por_fecha

        mock_listar.return_value = [
            {"id_articulo_pack": 1, "codigo_articulo": "A", "descripcion_articulo": "A", "cantidad_packs": 3},
            {"id_articulo_pack": 1, "codigo_articulo": "A", "descripcion_articulo": "A", "cantidad_packs": 2},
        ]
        out = listar_armados_realizados_por_fecha(
            "empresa_test",
            fecha_realizado=date(2026, 7, 31),
            modo="1ra",
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["cantidad_packs"], 5)
