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

    def test_rechaza_sin_operario(self):
        ok, err = validar_datos_armado_surtido(
            1,
            10,
            20,
            [{"id_articulo": 1, "cantidad_por_pack": 2}],
            id_operario=None,
            id_articulo_pack=100,
        )
        self.assertFalse(ok)
        self.assertIn("operario", (err or "").lower())

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
