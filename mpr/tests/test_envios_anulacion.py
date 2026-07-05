"""Tests anulación envíos tablero (FIFO vs partes, Opción A)."""
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from mpr.repositories.envio_produccion import (
    agrupar_filas_en_lotes,
    calcular_saldo_anulable_fifo,
    crear_envios_lote,
    motivo_no_anulable,
    sumar_envios_por_componente,
)
from mpr.services import anular_envios_produccion_seleccionados

MYSQL_EMPRESA = "administranet93"
ART_TEST = 999002


class TestCalcularSaldoAnulableFifo(SimpleTestCase):
    def test_sin_partes_todo_anulable(self):
        envios = [
            {"id_mpr_envio_produccion": 1, "cantidad": Decimal("10")},
            {"id_mpr_envio_produccion": 2, "cantidad": Decimal("5")},
        ]
        saldos = calcular_saldo_anulable_fifo(envios, Decimal("0"))
        self.assertEqual(saldos[1], Decimal("10"))
        self.assertEqual(saldos[2], Decimal("5"))

    def test_parte_consume_mas_antiguo_primero(self):
        envios = [
            {"id_mpr_envio_produccion": 1, "cantidad": Decimal("10")},
            {"id_mpr_envio_produccion": 2, "cantidad": Decimal("5")},
        ]
        saldos = calcular_saldo_anulable_fifo(envios, Decimal("12"))
        self.assertEqual(saldos[1], Decimal("0"))
        self.assertEqual(saldos[2], Decimal("3"))

    def test_parte_supera_envios_saldo_cero(self):
        envios = [{"id_mpr_envio_produccion": 1, "cantidad": Decimal("3")}]
        saldos = calcular_saldo_anulable_fifo(envios, Decimal("10"))
        self.assertEqual(saldos[1], Decimal("0"))


class TestMotivoNoAnulable(SimpleTestCase):
    def test_ya_anulado(self):
        self.assertEqual(
            motivo_no_anulable({"anulado": 1, "cantidad": Decimal("1")}, Decimal("1")),
            "Ya anulado",
        )

    def test_con_mstock(self):
        self.assertEqual(
            motivo_no_anulable(
                {"anulado": 0, "codigo_movimiento_mstock": 99, "cantidad": Decimal("1")},
                Decimal("1"),
            ),
            "Vinculado a movimiento de stock",
        )


class TestAnularEnviosProduccionServicio(SimpleTestCase):
    @patch("mpr.repositories.envio_produccion.anular_envios_por_ids")
    @patch("mpr.repositories.parte.opp_acumulado_por_pack")
    @patch("mpr.repositories.envio_produccion.listar_envios_activos_por_articulos")
    @patch("mpr.repositories.envio_produccion.obtener_envios_por_ids")
    def test_anula_fila_completa_sin_parte(
        self, mock_obtener, mock_envios_art, mock_parte, mock_anular
    ):
        mock_obtener.return_value = [
            {
                "id_mpr_envio_produccion": 7,
                "id_articulo": 100,
                "cantidad": Decimal("2"),
                "anulado": 0,
                "codigo_movimiento_mstock": None,
                "creado_en": datetime(2026, 7, 5, 10, 0, 0),
            }
        ]
        mock_envios_art.return_value = {100: mock_obtener.return_value}
        mock_parte.return_value = {100: Decimal("0")}
        mock_anular.return_value = 1

        ok, n, errs, err = anular_envios_produccion_seleccionados("empresa", [7], 1)
        self.assertTrue(ok)
        self.assertEqual(n, 1)
        self.assertIsNone(err)
        mock_anular.assert_called_once_with("empresa", [7], 1)

    @patch("mpr.repositories.envio_produccion.anular_envios_por_ids")
    @patch("mpr.repositories.parte.opp_acumulado_por_pack")
    @patch("mpr.repositories.envio_produccion.listar_envios_activos_por_articulos")
    @patch("mpr.repositories.envio_produccion.obtener_envios_por_ids")
    def test_rechaza_envio_consumido_por_parte(
        self, mock_obtener, mock_envios_art, mock_parte, mock_anular
    ):
        envio_row = {
            "id_mpr_envio_produccion": 8,
            "id_articulo": 100,
            "cantidad": Decimal("5"),
            "anulado": 0,
            "codigo_movimiento_mstock": None,
            "creado_en": datetime(2026, 7, 5, 10, 0, 0),
        }
        mock_obtener.return_value = [envio_row]
        mock_envios_art.return_value = {100: [envio_row]}

        def _parte_side_effect(base, ids, *, desde=None):
            if desde is not None:
                return {100: Decimal("5")}
            return {}

        mock_parte.side_effect = _parte_side_effect

        ok, n, errs, err = anular_envios_produccion_seleccionados("empresa", [8], 1)
        self.assertFalse(ok)
        self.assertEqual(n, 0)
        self.assertTrue(any("Consumido" in e for e in errs))


class TestAgruparFilasEnLotes(SimpleTestCase):
    def test_agrupa_por_uuid_lote(self):
        uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        filas = [
            {
                "id_mpr_envio_produccion": 1,
                "uuid_lote": uuid,
                "id_usuario": 5,
                "cantidad": Decimal("2"),
                "anulable": True,
                "anulado": 0,
                "creado_en": datetime(2026, 7, 5, 10, 0, 0),
            },
            {
                "id_mpr_envio_produccion": 2,
                "uuid_lote": uuid,
                "id_usuario": 5,
                "cantidad": Decimal("3"),
                "anulable": False,
                "anulado": 0,
                "creado_en": datetime(2026, 7, 5, 10, 0, 1),
            },
        ]
        lotes = agrupar_filas_en_lotes(filas)
        self.assertEqual(len(lotes), 1)
        self.assertEqual(lotes[0]["n_lineas"], 2)
        self.assertEqual(lotes[0]["n_anulables"], 1)
        self.assertEqual(lotes[0]["total_cantidad"], Decimal("5"))


    def test_partes_anteriores_al_envio_no_bloquean(self):
        """Partes previas al ledger tablero no deben consumir saldo anulable."""
        envios = [
            {
                "id_mpr_envio_produccion": 13,
                "cantidad": Decimal("1"),
                "creado_en": datetime(2026, 7, 5, 0, 46, 29),
            },
            {
                "id_mpr_envio_produccion": 14,
                "cantidad": Decimal("1"),
                "creado_en": datetime(2026, 7, 5, 0, 47, 26),
            },
        ]
        # Sin partes posteriores al primer envío → ambos anulables
        saldos = calcular_saldo_anulable_fifo(envios, Decimal("0"))
        self.assertEqual(saldos[13], Decimal("1"))
        self.assertEqual(saldos[14], Decimal("1"))

        # Una parte posterior consume el más antiguo
        saldos2 = calcular_saldo_anulable_fifo(envios, Decimal("1"))
        self.assertEqual(saldos2[13], Decimal("0"))
        self.assertEqual(saldos2[14], Decimal("1"))


class TestAnularEnviosMySQL(TestCase):
    """Integración MySQL en administranet93."""

    def setUp(self):
        from mpr.db import mysql_cursor

        with mysql_cursor(MYSQL_EMPRESA) as c:
            c.execute(
                "DELETE FROM mpr_envio_produccion WHERE id_articulo = %s",
                [ART_TEST],
            )

    def tearDown(self):
        from mpr.db import mysql_cursor

        with mysql_cursor(MYSQL_EMPRESA) as c:
            c.execute(
                "DELETE FROM mpr_envio_produccion WHERE id_articulo = %s",
                [ART_TEST],
            )

    def test_crear_lote_comparte_uuid(self):
        crear_envios_lote(
            MYSQL_EMPRESA,
            1,
            [(ART_TEST, Decimal("2")), (ART_TEST, Decimal("3"))],
        )
        from mpr.db import mysql_cursor

        with mysql_cursor(MYSQL_EMPRESA, dict_cursor=True) as c:
            c.execute(
                "SELECT uuid_lote FROM mpr_envio_produccion WHERE id_articulo = %s",
                [ART_TEST],
            )
            uuids = {r["uuid_lote"] for r in (c.fetchall() or [])}
        self.assertEqual(len(uuids), 1)
        self.assertTrue(all(uuids))

    def test_crear_anular_y_excluir_de_suma(self):
        crear_envios_lote(MYSQL_EMPRESA, 1, [(ART_TEST, Decimal("4"))])
        tot1 = sumar_envios_por_componente(MYSQL_EMPRESA, [ART_TEST])
        self.assertEqual(tot1.get(ART_TEST), Decimal("4"))

        from mpr.db import mysql_cursor

        with mysql_cursor(MYSQL_EMPRESA, dict_cursor=True) as c:
            c.execute(
                "SELECT id_mpr_envio_produccion FROM mpr_envio_produccion "
                "WHERE id_articulo = %s AND anulado = 0 LIMIT 1",
                [ART_TEST],
            )
            row = c.fetchone()
        env_id = int(row["id_mpr_envio_produccion"])

        ok, n, _, err = anular_envios_produccion_seleccionados(
            MYSQL_EMPRESA, [env_id], 1
        )
        self.assertTrue(ok, err)
        self.assertEqual(n, 1)

        tot2 = sumar_envios_por_componente(MYSQL_EMPRESA, [ART_TEST])
        self.assertEqual(tot2.get(ART_TEST, Decimal("0")), Decimal("0"))
