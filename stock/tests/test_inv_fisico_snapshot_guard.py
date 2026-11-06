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
        self.assertEqual(res["diferencias_snapshot"], svc._serializar_diffs([diff]))
        mock_recalc.assert_not_called()
        mock_trans.assert_not_called()
        mock_alta.assert_not_called()


# --- Aceptar descuadre, base kardex actual y auditoría ---
from datetime import datetime


def _mov(fc, entrada=0, salida=0):
    return {"FechaControl": fc, "Entrada": Decimal(entrada), "Salida": Decimal(salida)}


class DiferenciaRealSaldoActualTest(SimpleTestCase):
    def test_formula_contado_mas_b_menos_saldo(self):
        self.assertEqual(
            svc.calcular_diferencia_real_saldo_actual(Decimal("289"), Decimal("-528"), Decimal("230")),
            Decimal("-469"),
        )

    def test_sin_conteo_o_sin_saldo_none(self):
        self.assertIsNone(svc.calcular_diferencia_real_saldo_actual(None, 0, Decimal("1")))
        self.assertIsNone(svc.calcular_diferencia_real_saldo_actual(Decimal("1"), 0, None))


class RecalcularBaseKardexTest(SimpleTestCase):
    """Caso 947819-04: snapshot inflado 1262, kardex real; tras aplicar el kardex cuadra."""

    def _run(self, *, saldo_sd, kardex_rows):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {"id_linea": 8951, "id_articulo": 1748, "id_deposito": 6,
             "saldo_snapshot": Decimal("1262"), "cantidad_contada": Decimal("289"),
             "ajuste_manual": None}
        ]
        snap = datetime(2026, 9, 8, 12, 25, 1)
        post = [m for m in kardex_rows if m["FechaControl"] >= snap]
        saldo_kardex = sum((m["Entrada"] - m["Salida"] for m in kardex_rows), Decimal("0"))
        eventos = {(1748, 6): [{"id_evento": 1, "cantidad": Decimal("289"),
                                "server_ts": datetime(2026, 9, 9, 11, 8, 39), "resultado": "aceptado"}]}
        with patch.object(svc, "obtener_campana", return_value={
                "estado": svc.ESTADO_EN_REVISION, "fecha_snapshot": snap, "depositos": [6]}), \
             patch.object(svc, "mysql_cursor") as ctx, \
             patch.object(svc, "_cargar_eventos_campana", return_value=eventos), \
             patch.object(svc, "_cargar_movimientos_post_snapshot_campana", return_value={(1748, 6): post}), \
             patch.object(svc, "_fetch_saldos_deposito", return_value={6: saldo_sd}), \
             patch.object(svc, "_fetch_saldo_kardex", return_value=saldo_kardex):
            _cursor_ctx(ctx, cursor)
            ok, info = svc.recalcular_ajuste_post_snapshot("emp", 10, id_usuario=9, base_saldo_actual=True)
        self.assertTrue(ok, info)
        upd = [c for c in cursor.execute.call_args_list if "UPDATE inv_fisico_linea" in c.args[0]][0]
        self.assertNotIn("saldo_snapshot", upd.args[0])
        diff_real = upd.args[1][2]
        return diff_real, saldo_kardex, info

    def _kardex(self):
        return [
            _mov(datetime(2026, 8, 31, 11, 45), entrada=758),           # pre-snapshot
            _mov(datetime(2026, 9, 10, 10, 46), salida=528),            # remitos post-conteo
        ]

    def test_kardex_final_igual_contado_mas_b(self):
        diff_real, saldo_kardex, _info = self._run(saldo_sd=Decimal("230"), kardex_rows=self._kardex())
        self.assertEqual(diff_real, Decimal("-469"))
        kardex_final = saldo_kardex + diff_real            # aplicar el MSTOCK al kardex
        self.assertEqual(kardex_final, Decimal("289") + Decimal("-528"))

    def test_usa_kardex_si_stock_deposito_difiere_y_lo_informa(self):
        diff_real, saldo_kardex, info = self._run(saldo_sd=Decimal("734"), kardex_rows=self._kardex())
        self.assertEqual(saldo_kardex + diff_real, Decimal("-239"))
        self.assertEqual(info["lineas_sd_distinto_kardex"][0]["stock_deposito"], "734")
        self.assertEqual(info["lineas_sd_distinto_kardex"][0]["kardex"], "230")


class AceptarDescuadreTest(SimpleTestCase):
    DIFF = {"id_linea": 8951, "id_articulo": 1748, "id_deposito": 6,
            "saldo_snapshot": Decimal("1262"), "kardex_a_snapshot": Decimal("758"),
            "diferencia": Decimal("504")}

    def _campana(self):
        return {"id_campana": 10, "estado": svc.ESTADO_EN_REVISION, "fecha": "2026-09-08",
                "depositos": [6], "fecha_snapshot": "2026-09-08 12:25:01"}

    def _patches(self, verif):
        return [
            patch.object(svc, "obtener_campana", return_value=self._campana()),
            patch.object(svc, "mstock_existente_campana", return_value=None),
            patch.object(svc, "contar_conflictos_sync", return_value=0),
            patch.object(svc, "verificar_snapshot_vs_kardex", return_value=verif),
        ]

    def _start(self, verif):
        for p in self._patches(verif):
            p.start()
            self.addCleanup(p.stop)

    @patch("core.services.administranet_stock.alta_movimiento")
    @patch.object(svc, "recalcular_ajuste_post_snapshot")
    @patch.object(svc, "registrar_aceptacion_descuadre")
    def test_no_aceptar_bloquea_con_listado(self, mock_aud, mock_recalc, mock_alta):
        self._start((False, [self.DIFF]))
        ok, res = svc.autorizar_y_aplicar_campana("emp", 10, id_usuario=9, id_puesto=1)
        self.assertFalse(ok)
        self.assertEqual(res["codigo"], "snapshot_descuadrado")
        self.assertTrue(res["puede_aceptar"])
        self.assertEqual(res["diferencias_snapshot"][0]["diferencia"], "504")
        mock_aud.assert_not_called()
        mock_recalc.assert_not_called()
        mock_alta.assert_not_called()

    @patch("core.services.administranet_stock.alta_movimiento")
    @patch.object(svc, "transicionar_campana", return_value=(True, {}))
    @patch.object(svc, "_query_lineas_analizador")
    @patch.object(svc, "mysql_cursor")
    @patch.object(svc, "recalcular_ajuste_post_snapshot", return_value=(True, {}))
    @patch.object(svc, "registrar_aceptacion_descuadre", return_value=True)
    def test_aceptar_continua_audita_y_usa_base_saldo_actual(
        self, mock_aud, mock_recalc, mock_ctx, mock_lineas, _trans, mock_alta
    ):
        self._start((False, [self.DIFF]))
        _cursor_ctx(mock_ctx, MagicMock())
        mock_lineas.return_value = [{
            "id_linea": 8951, "id_articulo": 1748, "id_deposito": 6,
            "saldo_snapshot": Decimal("1262"), "cantidad_contada": Decimal("289"),
            "diferencia": Decimal("-469"), "diferencia_real": Decimal("-469"),
            "codigo": "1.1.1735", "nombre": "947819-04"}]
        mock_alta.return_value = (True, Decimal("30000"), "0001-1", None, None)
        ok, res = svc.autorizar_y_aplicar_campana(
            "emp", 10, id_usuario=9, id_puesto=1, aceptar_descuadre=True)
        self.assertTrue(ok, res)
        self.assertEqual(res["descuadre_aceptado"], 1)
        mock_aud.assert_called_once_with("emp", 10, [self.DIFF], id_usuario=9)
        self.assertTrue(mock_recalc.call_args.kwargs["base_saldo_actual"])
        mock_alta.assert_called_once()

    @patch("core.services.administranet_stock.alta_movimiento")
    @patch.object(svc, "recalcular_ajuste_post_snapshot")
    @patch.object(svc, "registrar_aceptacion_descuadre", return_value=True)
    def test_aceptar_sin_poder_verificar_tambien_continua(self, mock_aud, mock_recalc, mock_alta):
        self._start((False, [{"error": "No se pudo reconstruir el kardex a fecha_snapshot."}]))
        mock_recalc.return_value = (False, {"error": "stop"})
        ok, res = svc.autorizar_y_aplicar_campana(
            "emp", 10, id_usuario=9, id_puesto=1, aceptar_descuadre=True)
        mock_aud.assert_called_once()
        mock_recalc.assert_called_once()
        self.assertEqual(res["error"], "stop")

    @patch("core.services.administranet_stock.alta_movimiento")
    @patch.object(svc, "recalcular_ajuste_post_snapshot")
    @patch.object(svc, "registrar_aceptacion_descuadre", return_value=False)
    def test_falla_auditoria_no_aplica(self, _aud, mock_recalc, mock_alta):
        self._start((False, [self.DIFF]))
        ok, res = svc.autorizar_y_aplicar_campana(
            "emp", 10, id_usuario=9, id_puesto=1, aceptar_descuadre=True)
        self.assertFalse(ok)
        mock_recalc.assert_not_called()
        mock_alta.assert_not_called()

    @patch("core.services.administranet_stock.alta_movimiento")
    @patch.object(svc, "registrar_aceptacion_descuadre")
    def test_idempotencia_se_mantiene_aun_aceptando(self, mock_aud, mock_alta):
        with patch.object(svc, "obtener_campana",
                          return_value=dict(self._campana(), id_movimiento_mstock=17710)):
            ok, res = svc.autorizar_y_aplicar_campana(
                "emp", 10, id_usuario=9, id_puesto=1, aceptar_descuadre=True)
        self.assertFalse(ok)
        self.assertEqual(res["codigo"], "ya_aplicada")
        mock_aud.assert_not_called()
        mock_alta.assert_not_called()


class RegistrarAceptacionDescuadreTest(SimpleTestCase):
    @patch.object(svc, "mysql_cursor")
    def test_inserta_una_fila_por_diferencia_con_usuario(self, mock_ctx):
        cursor = MagicMock()
        _cursor_ctx(mock_ctx, cursor)
        ok = svc.registrar_aceptacion_descuadre("emp", 10, [AceptarDescuadreTest.DIFF], id_usuario=9)
        self.assertTrue(ok)
        sql, params = cursor.execute.call_args.args
        self.assertIn("INSERT INTO inv_fisico_ajuste_auditoria", sql)
        self.assertIn(svc.ACCION_AUDIT_DESCUADRE_ACEPTADO, params)
        self.assertIn(9, params)
        self.assertIn(Decimal("1262"), params)
        self.assertIn(Decimal("758"), params)
        self.assertIn(Decimal("504"), params)

    @patch.object(svc, "mysql_cursor")
    def test_sin_verificacion_registra_fila_generica(self, mock_ctx):
        cursor = MagicMock()
        _cursor_ctx(mock_ctx, cursor)
        self.assertTrue(svc.registrar_aceptacion_descuadre("emp", 10, [{"error": "x"}], id_usuario=3))
        self.assertEqual(cursor.execute.call_count, 1)


class ApiAceptarDescuadreTest(SimpleTestCase):
    def _req(self, body):
        import json as _j
        from django.test import RequestFactory
        rf = RequestFactory()
        req = rf.post("/x", data=_j.dumps(body), content_type="application/json")
        return req

    @patch("stock.api_views._session_context")
    @patch("stock.services.inventario_fisico.autorizar_y_aplicar_campana")
    def test_api_pasa_aceptar_descuadre_solo_si_true(self, mock_aut, mock_ctx):
        from stock import api_views
        mock_ctx.return_value = ({"base_empresa": "emp", "id_usuario": 9}, None)
        mock_aut.return_value = (True, {"estado": svc.ESTADO_APLICADO})
        view = api_views.api_campana_autorizar
        while hasattr(view, "__wrapped__"):
            view = view.__wrapped__
        view(self._req({"aceptar_descuadre": True}), id_campana=10)
        self.assertTrue(mock_aut.call_args.kwargs["aceptar_descuadre"])
        view(self._req({"aceptar_descuadre": "si"}), id_campana=10)
        self.assertFalse(mock_aut.call_args.kwargs["aceptar_descuadre"])
