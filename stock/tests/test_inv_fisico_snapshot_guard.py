# -*- coding: utf-8 -*-
"""Snapshot inmutable, control snapshot vs kardex e idempotencia de autorización."""
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from stock.services import inventario_fisico as svc


def _cursor_ctx(mock_ctx, cursor):
    mock_ctx.return_value.__enter__ = MagicMock(return_value=cursor)
    mock_ctx.return_value.__exit__ = MagicMock(return_value=False)


class SnapshotInmutableTest(SimpleTestCase):
    def test_rechaza_update_de_saldo_snapshot(self):
        with self.assertRaises(svc.SnapshotInmutableError):
            svc.validar_campos_update_linea(["cantidad_contada", "SALDO_SNAPSHOT"])

    def test_permite_otros_campos(self):
        svc.validar_campos_update_linea(["cantidad_contada", "diferencia", "ajuste_sistema"])

    def test_crear_campana_no_pisa_snapshot_existente(self):
        import inspect

        src = inspect.getsource(svc.crear_campana)
        self.assertNotIn("UPDATE saldo_snapshot", src)
        self.assertIn("ON DUPLICATE KEY UPDATE id_linea = id_linea", src)


class CompararSnapshotKardexTest(SimpleTestCase):
    def test_caso_947819_04_detecta_inflado(self):
        lineas = [
            {"id_linea": 8951, "id_articulo": 1748, "id_deposito": 6, "saldo_snapshot": Decimal("1262")},
            {"id_linea": 2, "id_articulo": 10, "id_deposito": 6, "saldo_snapshot": Decimal("5")},
        ]
        kardex = {(1748, 6): Decimal("758"), (10, 6): Decimal("5")}
        diffs = svc.comparar_snapshot_vs_kardex(lineas, kardex)
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0]["id_articulo"], 1748)
        self.assertEqual(diffs[0]["diferencia"], Decimal("504"))

    def test_articulo_sin_movimientos_vale_cero(self):
        lineas = [{"id_linea": 1, "id_articulo": 1, "id_deposito": 6, "saldo_snapshot": Decimal("3")}]
        diffs = svc.comparar_snapshot_vs_kardex(lineas, {})
        self.assertEqual(diffs[0]["kardex_a_snapshot"], Decimal("0"))

    def test_coinciden_sin_diferencias(self):
        lineas = [{"id_linea": 1, "id_articulo": 1, "id_deposito": 6, "saldo_snapshot": Decimal("0")}]
        self.assertEqual(svc.comparar_snapshot_vs_kardex(lineas, {}), [])

    @patch("stock.services.inventario_fisico._filtro_movimiento_efectivo_deposito", return_value=" AND 1=1 ")
    @patch("stock.services.inventario_fisico._nombre_tabla", return_value="stock")
    @patch("stock.services.inventario_fisico.mysql_cursor")
    def test_verificar_usa_filtro_efectivo_y_fecha_snapshot(self, mock_ctx, _tbl, mock_filtro):
        cursor = MagicMock()
        cursor.fetchall.side_effect = [
            [{"id_linea": 1, "id_articulo": 1748, "id_deposito": 6, "saldo_snapshot": Decimal("1262")}],
            [{"id_articulo": 1748, "id_deposito": 6, "saldo": Decimal("758")}],
        ]
        _cursor_ctx(mock_ctx, cursor)
        ok, diffs = svc.verificar_snapshot_vs_kardex("emp", 10, "2026-09-08 12:25:01", [6])
        self.assertFalse(ok)
        self.assertEqual(diffs[0]["diferencia"], Decimal("504"))
        mock_filtro.assert_called_once()
        sql, params = cursor.execute.call_args_list[1].args
        self.assertIn("FechaControl < %s", sql)
        self.assertIn("AND 1=1", sql)
        self.assertEqual(params[-1], "2026-09-08 12:25:01")

    def test_verificar_sin_fecha_snapshot_no_ok(self):
        ok, diffs = svc.verificar_snapshot_vs_kardex("emp", 10, None, [6])
        self.assertFalse(ok)
        self.assertIn("error", diffs[0])


class AutorizarGuardasTest(SimpleTestCase):
    def _campana(self, **extra):
        base = {
            "id_campana": 10,
            "estado": svc.ESTADO_EN_REVISION,
            "fecha": "2026-09-08",
            "depositos": [6],
            "fecha_snapshot": "2026-09-08 12:25:01",
        }
        base.update(extra)
        return base

    @patch("core.services.administranet_stock.alta_movimiento")
    @patch("stock.services.inventario_fisico.recalcular_ajuste_post_snapshot")
    @patch("stock.services.inventario_fisico.obtener_campana")
    def test_idempotente_con_id_movimiento_mstock(self, mock_obt, mock_recalc, mock_alta):
        mock_obt.return_value = self._campana(id_movimiento_mstock=17710)
        ok, res = svc.autorizar_y_aplicar_campana("emp", 10, id_usuario=9, id_puesto=1)
        self.assertFalse(ok)
        self.assertEqual(res["codigo"], "ya_aplicada")
        self.assertEqual(res["codigo_movimiento"], 17710)
        mock_alta.assert_not_called()
        mock_recalc.assert_not_called()

    @patch("core.services.administranet_stock.alta_movimiento")
    @patch("stock.services.inventario_fisico.mstock_existente_campana", return_value=17709)
    @patch("stock.services.inventario_fisico.obtener_campana")
    def test_idempotente_con_mstock_previo_sin_id_guardado(self, mock_obt, _prev, mock_alta):
        mock_obt.return_value = self._campana()
        ok, res = svc.autorizar_y_aplicar_campana("emp", 10, id_usuario=9, id_puesto=1)
        self.assertFalse(ok)
        self.assertEqual(res["codigo"], "ya_aplicada")
        mock_alta.assert_not_called()

    @patch("core.services.administranet_stock.alta_movimiento")
    @patch("stock.services.inventario_fisico.transicionar_campana")
    @patch("stock.services.inventario_fisico.recalcular_ajuste_post_snapshot")
    @patch("stock.services.inventario_fisico.verificar_snapshot_vs_kardex")
    @patch("stock.services.inventario_fisico.contar_conflictos_sync", return_value=0)
    @patch("stock.services.inventario_fisico.mstock_existente_campana", return_value=None)
    @patch("stock.services.inventario_fisico.obtener_campana")
    def test_bloquea_si_snapshot_no_coincide(
        self, mock_obt, _prev, _conf, mock_verif, mock_recalc, mock_trans, mock_alta
    ):
        mock_obt.return_value = self._campana()
        diff = {"id_articulo": 1748, "id_deposito": 6, "saldo_snapshot": Decimal("1262"),
                "kardex_a_snapshot": Decimal("758"), "diferencia": Decimal("504")}
        mock_verif.return_value = (False, [diff])
        ok, res = svc.autorizar_y_aplicar_campana("emp", 10, id_usuario=9, id_puesto=1)
        self.assertFalse(ok)
        self.assertEqual(res["codigo"], "snapshot_descuadrado")
        self.assertEqual(res["diferencias_snapshot"], [diff])
        mock_recalc.assert_not_called()
        mock_trans.assert_not_called()
        mock_alta.assert_not_called()
