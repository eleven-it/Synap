# -*- coding: utf-8 -*-
"""Tests analizador, autorización y MSTOCK inventario físico (Fase 6 — Strict TDD)."""
import json
import uuid
from decimal import Decimal
from unittest.mock import MagicMock, call, patch

from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import reverse

from stock.services import inventario_fisico as svc


class MotivoMstockPorDiferenciaTest(SimpleTestCase):
    def test_sobrante_diferencia_positiva(self):
        self.assertEqual(svc.motivo_mstock_por_diferencia(Decimal("2")), svc.MOTIVO_SOBRANTE)

    def test_faltante_diferencia_negativa(self):
        self.assertEqual(svc.motivo_mstock_por_diferencia(Decimal("-1")), svc.MOTIVO_FALTANTE)

    def test_sin_movimiento_diferencia_cero(self):
        self.assertIsNone(svc.motivo_mstock_por_diferencia(Decimal("0")))


class ConstruirRenglonMstockTest(SimpleTestCase):
    def test_faltante_genera_salida(self):
        linea = {
            "id_articulo": 10,
            "id_deposito": 3,
            "diferencia": Decimal("-4"),
            "codigo": "ART-10",
            "nombre": "Artículo diez",
        }
        reng = svc.construir_renglon_mstock(linea)
        self.assertEqual(reng["IDArt"], 10)
        self.assertEqual(reng["CodDeposito"], 3)
        self.assertEqual(reng["salida"], Decimal("4"))
        self.assertEqual(reng["entrada"], Decimal("0"))
        self.assertEqual(reng["ES"], "S")

    def test_sobrante_genera_entrada(self):
        linea = {
            "id_articulo": 11,
            "id_deposito": 5,
            "diferencia": Decimal("2.5"),
            "codigo": "ART-11",
            "nombre": "Artículo once",
        }
        reng = svc.construir_renglon_mstock(linea)
        self.assertEqual(reng["entrada"], Decimal("2.5"))
        self.assertEqual(reng["salida"], Decimal("0"))
        self.assertEqual(reng["ES"], "E")

    def test_prioriza_diferencia_real_sobre_legacy(self):
        linea = {
            "id_articulo": 12,
            "id_deposito": 3,
            "diferencia": Decimal("10"),
            "diferencia_real": Decimal("-3"),
            "codigo": "ART-12",
            "nombre": "Artículo doce",
        }
        reng = svc.construir_renglon_mstock(linea)
        self.assertEqual(reng["salida"], Decimal("3"))
        self.assertEqual(reng["entrada"], Decimal("0"))
        self.assertEqual(reng["ES"], "S")

    def test_diferencia_real_cero_sin_movimiento(self):
        linea = {
            "id_articulo": 13,
            "id_deposito": 3,
            "diferencia": Decimal("5"),
            "diferencia_real": Decimal("0"),
            "codigo": "ART-13",
            "nombre": "Artículo trece",
        }
        reng = svc.construir_renglon_mstock(linea)
        self.assertEqual(reng["entrada"], Decimal("0"))
        self.assertEqual(reng["salida"], Decimal("0"))


class BloqueoAutorizacionSyncTest(SimpleTestCase):
    def test_bloqueado_si_pendientes_cliente(self):
        bloqueado, codigo, _msg = svc.evaluar_bloqueo_autorizacion(
            svc.ESTADO_EN_REVISION,
            pendientes_cliente=3,
            conflictos_sync=0,
        )
        self.assertTrue(bloqueado)
        self.assertEqual(codigo, "sync_pendiente")

    def test_bloqueado_si_conflictos_sync(self):
        bloqueado, codigo, _msg = svc.evaluar_bloqueo_autorizacion(
            svc.ESTADO_EN_REVISION,
            pendientes_cliente=0,
            conflictos_sync=2,
        )
        self.assertTrue(bloqueado)
        self.assertEqual(codigo, "sync_pendiente")

    def test_no_bloqueado_en_revision_sin_pendientes(self):
        bloqueado, codigo, _msg = svc.evaluar_bloqueo_autorizacion(
            svc.ESTADO_EN_REVISION,
            pendientes_cliente=0,
            conflictos_sync=0,
        )
        self.assertFalse(bloqueado)
        self.assertEqual(codigo, "")

    def test_bloqueado_estado_incorrecto(self):
        bloqueado, codigo, _msg = svc.evaluar_bloqueo_autorizacion(
            svc.ESTADO_EN_CONTEO,
            pendientes_cliente=0,
            conflictos_sync=0,
        )
        self.assertTrue(bloqueado)
        self.assertEqual(codigo, "estado_invalido")


class AutorizarCampanaServiceTest(SimpleTestCase):
    def _campana_revision(self):
        return {
            "id_campana": 7,
            "estado": svc.ESTADO_EN_REVISION,
            "fecha": "2026-07-23",
            "depositos": [3],
        }

    @patch("core.services.administranet_stock.alta_movimiento")
    @patch("stock.services.inventario_fisico.contar_conflictos_sync")
    @patch("stock.services.inventario_fisico.obtener_campana")
    @patch("stock.services.inventario_fisico.mysql_cursor")
    def test_rechaza_si_pendientes_cliente(
        self, mock_cursor_ctx, mock_obtener, mock_conflictos, mock_alta
    ):
        mock_obtener.return_value = self._campana_revision()
        mock_conflictos.return_value = 0

        ok, result = svc.autorizar_y_aplicar_campana(
            "emp",
            7,
            id_usuario=1,
            id_puesto=1,
            pendientes_cliente=5,
        )
        self.assertFalse(ok)
        self.assertTrue(result.get("bloqueado"))
        self.assertEqual(result.get("codigo"), "sync_pendiente")
        mock_alta.assert_not_called()

    @patch("stock.services.inventario_fisico.transicionar_campana")
    @patch("core.services.administranet_stock.alta_movimiento")
    @patch("stock.services.inventario_fisico.recalcular_ajuste_post_snapshot")
    @patch("stock.services.inventario_fisico.contar_conflictos_sync")
    @patch("stock.services.inventario_fisico.obtener_campana")
    @patch("stock.services.inventario_fisico._query_lineas_analizador")
    @patch("stock.services.inventario_fisico.mysql_cursor")
    def test_autoriza_aplica_mstock_y_transiciona(
        self,
        mock_cursor_ctx,
        mock_lineas,
        mock_obtener,
        mock_conflictos,
        mock_recalc,
        mock_alta,
        mock_transicion,
    ):
        mock_obtener.return_value = self._campana_revision()
        mock_conflictos.return_value = 0
        mock_recalc.return_value = (True, {"lineas_actualizadas": 3})
        mock_alta.return_value = (True, Decimal("9001"), "00012345", None, None)
        mock_transicion.return_value = (True, {"estado": svc.ESTADO_APLICADO})
        cursor = MagicMock()
        mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)
        mock_lineas.return_value = [
            {
                "id_linea": 1,
                "id_articulo": 100,
                "id_deposito": 3,
                "saldo_snapshot": Decimal("10"),
                "cantidad_contada": Decimal("12"),
                "diferencia": Decimal("2"),
                "diferencia_real": Decimal("2"),
                "codigo": "A100",
                "nombre": "Art 100",
            },
            {
                "id_linea": 2,
                "id_articulo": 101,
                "id_deposito": 3,
                "saldo_snapshot": Decimal("5"),
                "cantidad_contada": Decimal("4"),
                "diferencia": Decimal("-1"),
                "diferencia_real": Decimal("-1"),
                "codigo": "A101",
                "nombre": "Art 101",
            },
            {
                "id_linea": 3,
                "id_articulo": 102,
                "id_deposito": 3,
                "saldo_snapshot": Decimal("7"),
                "cantidad_contada": Decimal("7"),
                "diferencia": Decimal("0"),
                "diferencia_real": Decimal("0"),
                "codigo": "A102",
                "nombre": "Art 102",
            },
            {
                "id_linea": 4,
                "id_articulo": 103,
                "id_deposito": 3,
                "saldo_snapshot": Decimal("20"),
                "cantidad_contada": Decimal("25"),
                "diferencia": Decimal("5"),
                "diferencia_real": Decimal("0"),
                "codigo": "A103",
                "nombre": "Art 103",
            },
        ]

        ok, result = svc.autorizar_y_aplicar_campana(
            "emp",
            7,
            id_usuario=9,
            id_puesto=2,
            pendientes_cliente=0,
            id_punto_venta=1,
        )
        self.assertTrue(ok, result)
        self.assertEqual(result["estado"], svc.ESTADO_APLICADO)
        self.assertEqual(result["movimientos_mstock"], 2)
        self.assertEqual(mock_alta.call_count, 2)
        self.assertGreaterEqual(mock_transicion.call_count, 2)
        mock_recalc.assert_called_once_with(
            "emp", 7, id_usuario=9, pisar_overrides=False
        )

    @patch("core.services.administranet_stock.alta_movimiento")
    @patch("stock.services.inventario_fisico.obtener_campana")
    def test_sin_autorizacion_no_llama_alta_movimiento(self, mock_obtener, mock_alta):
        mock_obtener.return_value = {
            "id_campana": 8,
            "estado": svc.ESTADO_EN_CONTEO,
            "fecha": "2026-07-23",
            "depositos": [3],
        }
        ok, result = svc.autorizar_y_aplicar_campana(
            "emp", 8, id_usuario=1, id_puesto=1, pendientes_cliente=0
        )
        self.assertFalse(ok)
        mock_alta.assert_not_called()
        self.assertEqual(result.get("codigo"), "estado_invalido")


class AnularCampanaServiceTest(SimpleTestCase):
    @patch("stock.services.inventario_fisico.obtener_campana")
    @patch("stock.services.inventario_fisico.mysql_cursor")
    def test_anular_en_conteo_sin_mstock(self, mock_cursor_ctx, mock_obtener):
        mock_obtener.return_value = {"id_campana": 5, "estado": svc.ESTADO_EN_CONTEO}
        cursor = MagicMock()
        mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)

        ok, result = svc.anular_campana("emp", 5)
        self.assertTrue(ok)
        self.assertEqual(result["estado"], svc.ESTADO_ANULADO)
        update_sql = cursor.execute.call_args_list[0].args[0]
        self.assertIn("UPDATE inv_fisico_campana", update_sql)

    @patch("stock.services.inventario_fisico.obtener_campana")
    def test_no_anular_aplicada(self, mock_obtener):
        mock_obtener.return_value = {"id_campana": 5, "estado": svc.ESTADO_APLICADO}
        ok, result = svc.anular_campana("emp", 5)
        self.assertFalse(ok)
        self.assertIn("Aplicada", result.get("error", ""))


class ListarLineasAnalizadorTest(SimpleTestCase):
    @patch("stock.services.inventario_fisico.listar_contadores_candidatos")
    @patch("stock.services.inventario_fisico._query_lineas_analizador")
    @patch("stock.services.inventario_fisico.mysql_cursor")
    def test_filtro_faltante_solo_negativas(self, mock_cursor_ctx, mock_query, mock_candidatos):
        mock_candidatos.return_value = []
        cursor = MagicMock()
        mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)
        mock_query.return_value = [
            {
                "id_linea": 1,
                "id_articulo": 1,
                "id_deposito": 3,
                "saldo_snapshot": Decimal("10"),
                "cantidad_contada": Decimal("8"),
                "diferencia": Decimal("-2"),
                "diferencia_real": Decimal("-2"),
                "codigo": "X1",
                "nombre": "Uno",
                "id_contador": 10,
                "estado_linea": "Contado",
            },
            {
                "id_linea": 2,
                "id_articulo": 2,
                "id_deposito": 3,
                "saldo_snapshot": Decimal("5"),
                "cantidad_contada": Decimal("7"),
                "diferencia": Decimal("2"),
                "diferencia_real": Decimal("2"),
                "codigo": "X2",
                "nombre": "Dos",
                "id_contador": 10,
                "estado_linea": "Contado",
            },
        ]

        lineas = svc.listar_lineas_analizador("emp", 1, filtro="faltante")
        self.assertEqual(len(lineas), 1)
        self.assertEqual(lineas[0]["diferencia_real"], Decimal("-2"))

    @patch("stock.services.inventario_fisico.listar_contadores_candidatos")
    @patch("stock.services.inventario_fisico._query_lineas_analizador")
    @patch("stock.services.inventario_fisico.mysql_cursor")
    def test_filtro_no_contados(self, mock_cursor_ctx, mock_query, mock_candidatos):
        mock_candidatos.return_value = []
        cursor = MagicMock()
        mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)
        mock_query.return_value = [
            {
                "id_linea": 1,
                "id_articulo": 1,
                "id_deposito": 3,
                "saldo_snapshot": Decimal("10"),
                "cantidad_contada": Decimal("8"),
                "diferencia_real": Decimal("-2"),
                "codigo": "X1",
                "nombre": "Contado",
                "id_contador": 10,
                "estado_linea": "Contado",
            },
            {
                "id_linea": 2,
                "id_articulo": 2,
                "id_deposito": 3,
                "saldo_snapshot": Decimal("5"),
                "cantidad_contada": None,
                "diferencia_real": None,
                "codigo": "X2",
                "nombre": "Sin contar",
                "id_contador": None,
                "estado_linea": "Pendiente",
            },
            {
                "id_linea": 3,
                "id_articulo": 3,
                "id_deposito": 3,
                "saldo_snapshot": Decimal("1"),
                "cantidad_contada": Decimal("0"),
                "diferencia_real": Decimal("-1"),
                "codigo": "X3",
                "nombre": "Contado cero",
                "id_contador": 10,
                "estado_linea": "Contado",
            },
        ]
        lineas = svc.listar_lineas_analizador("emp", 1, filtro="no_contados")
        self.assertEqual(len(lineas), 1)
        self.assertEqual(lineas[0]["id_linea"], 2)
        self.assertIsNone(lineas[0]["cantidad_contada"])

    @patch("stock.services.inventario_fisico.listar_contadores_candidatos")
    @patch("stock.services.inventario_fisico._query_lineas_analizador")
    @patch("stock.services.inventario_fisico.mysql_cursor")
    def test_filtro_marcas_solo_seleccionadas(self, mock_cursor_ctx, mock_query, mock_candidatos):
        mock_candidatos.return_value = []
        cursor = MagicMock()
        mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)
        mock_query.return_value = [
            {
                "id_linea": 1,
                "id_articulo": 1,
                "id_deposito": 3,
                "saldo_snapshot": Decimal("10"),
                "cantidad_contada": Decimal("8"),
                "diferencia": Decimal("-2"),
                "codigo": "X1",
                "nombre": "Uno",
                "id_marca": 5,
                "nombre_marca": "Marca A",
            },
            {
                "id_linea": 2,
                "id_articulo": 2,
                "id_deposito": 3,
                "saldo_snapshot": Decimal("5"),
                "cantidad_contada": Decimal("7"),
                "diferencia": Decimal("2"),
                "codigo": "X2",
                "nombre": "Dos",
                "id_marca": 9,
                "nombre_marca": "Marca B",
            },
        ]

        lineas = svc.listar_lineas_analizador("emp", 1, marcas_incluidos=[5])
        self.assertEqual(len(lineas), 1)
        self.assertEqual(lineas[0]["id_marca"], 5)


class ParseMarcasIncluidosTest(SimpleTestCase):
    def test_normaliza_ids(self):
        self.assertEqual(svc.parse_marcas_incluidos(["1", "2", "x", "3"]), [1, 2, 3])

    def test_vacio(self):
        self.assertEqual(svc.parse_marcas_incluidos([]), [])


class BuildAnalizadorQueryStringTest(SimpleTestCase):
    def test_preserva_filtro_y_marcas(self):
        qs = svc.build_analizador_query_string(filtro="faltante", marcas_incluidos=[3, 7])
        self.assertIn("filtro=faltante", qs)
        self.assertIn("marcas_incluidos=3", qs)
        self.assertIn("marcas_incluidos=7", qs)


@override_settings(
    SESSION_ENGINE="django.contrib.sessions.backends.cache",
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "inv-fisico-ajuste-tests",
        }
    },
)
class ApiCampanaAutorizarTest(SimpleTestCase):
    def _request_post(self, id_campana=7, body=None):
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.http import HttpResponse
        from django.test import RequestFactory

        rf = RequestFactory()
        data = body if body is not None else {}
        request = rf.post(
            reverse("stock:api_campana_autorizar", kwargs={"id_campana": id_campana}),
            data=json.dumps(data),
            content_type="application/json",
        )
        SessionMiddleware(lambda req: HttpResponse()).process_request(request)
        request.session["user"] = {
            "base_empresa": "emp",
            "id_usuario": 1,
            "id_puesto": 1,
            "cod_usuario": "supervisor",
        }
        request.session.save()
        user = MagicMock()
        user.is_authenticated = True
        user.is_admin = MagicMock(return_value=True)
        request.user = user
        return request

    @patch("stock.services.inventario_fisico.autorizar_y_aplicar_campana")
    def test_api_bloqueo_sync_modal_json(self, mock_autorizar):
        from stock.api_views import api_campana_autorizar

        mock_autorizar.return_value = (
            False,
            {
                "bloqueado": True,
                "codigo": "sync_pendiente",
                "error": "Hay 3 conteos sin sincronizar.",
                "pendientes_cliente": 3,
            },
        )

        resp = api_campana_autorizar(self._request_post(body={"pendientes_cliente": 3}), id_campana=7)
        self.assertEqual(resp.status_code, 409)
        data = json.loads(resp.content)
        self.assertTrue(data["bloqueado"])
        self.assertEqual(data["codigo"], "sync_pendiente")
        self.assertIn("sincronizar", data["error"].lower())

    @patch("stock.services.inventario_fisico.autorizar_y_aplicar_campana")
    def test_api_exito_transicion_aplicado(self, mock_autorizar):
        from stock.api_views import api_campana_autorizar

        mock_autorizar.return_value = (
            True,
            {
                "estado": svc.ESTADO_APLICADO,
                "movimientos_mstock": 2,
                "lineas_ajustadas": 2,
                "codigo_movimiento": 9001,
            },
        )

        resp = api_campana_autorizar(self._request_post(), id_campana=7)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["ok"])
        self.assertEqual(data["estado"], svc.ESTADO_APLICADO)


@override_settings(
    SESSION_ENGINE="django.contrib.sessions.backends.cache",
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "inv-fisico-ajuste-vista-tests",
        }
    },
)
class AnalizadorVistaTest(SimpleTestCase):
    @patch("stock.services.inventario_fisico.recalcular_ajuste_post_snapshot")
    @patch("stock.services.inventario_fisico.listar_lineas_analizador")
    @patch("stock.services.inventario_fisico.obtener_resumen_monitor")
    @patch("stock.services.inventario_fisico.obtener_campana")
    @patch("stock.services.inventario_tabla.listar_marcas_catalogo")
    def test_vista_muestra_diferencias(
        self, mock_marcas, mock_campana, mock_resumen, mock_lineas, mock_recalc
    ):
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.http import HttpResponse
        from django.test import RequestFactory

        from stock.views import inventario_fisico_analizador_view

        mock_marcas.return_value = [{"value": 1, "label": "Marca Uno"}]
        mock_recalc.return_value = (True, {"lineas_actualizadas": 1})
        mock_campana.return_value = {
            "id_campana": 3,
            "estado": svc.ESTADO_EN_REVISION,
            "fecha": "2026-07-23",
            "depositos": [3],
        }
        mock_resumen.return_value = {
            "conflictos_sync": 1,
            "pendientes_conteo": 5,
            "bloqueo_autorizar": True,
            "mensaje_bloqueo": "Hay conteos sin sincronizar.",
            "total": 10,
            "contados": 5,
            "pendientes": 5,
            "porcentaje": 50,
        }
        mock_lineas.return_value = [
            {
                "id_linea": 1,
                "diferencia": Decimal("-2"),
                "diferencia_real": Decimal("-2"),
                "saldo_snapshot": Decimal("10"),
                "cantidad_contada": Decimal("8"),
                "codigo": "A1",
                "nombre": "Art",
            }
        ]

        rf = RequestFactory()
        request = rf.get(
            reverse("stock:inventario_fisico_analizador", kwargs={"id_campana": 3})
        )
        SessionMiddleware(lambda req: HttpResponse()).process_request(request)
        request.session["user"] = {
            "base_empresa": "emp",
            "id_usuario": 1,
            "cod_usuario": "supervisor",
            "nombre_empresa": "Empresa Test",
            "nombre_usuario": "Super",
            "apellido_usuario": "Visor",
        }
        request.session.save()
        user = MagicMock()
        user.is_authenticated = True
        user.is_admin = MagicMock(return_value=True)
        request.user = user

        resp = inventario_fisico_analizador_view(request, id_campana=3)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn("Analizador", content)
        self.assertIn("Disponible", content)
        self.assertIn("Diferencia real", content)
        self.assertIn("Buscar en tabla", content)
        self.assertIn("-2", content)
        self.assertIn("sincronizar", content.lower())


class MarcarNoContadosCeroServicioTest(SimpleTestCase):
    """Contado cero masivo — servicio (change contado-cero-masivo-analizador)."""

    def _campana(self, estado=svc.ESTADO_EN_REVISION):
        return {"id_campana": 7, "estado": estado, "depositos": [3]}

    def _lineas_sin_contar(self, cantidad=1, *, saldo=Decimal("0"), id_base=1):
        return [
            {
                "id_linea": id_base + i,
                "id_articulo": 100 + i,
                "id_deposito": 3,
                "saldo_snapshot": saldo,
                "cantidad_contada": None,
            }
            for i in range(cantidad)
        ]

    def _mock_cursor_con_lineas(self, mock_cursor_ctx, lineas):
        cursor = MagicMock()
        cursor.fetchall.return_value = lineas
        cursor.fetchone.side_effect = [
            {"cantidad_contada": l.get("cantidad_contada")} for l in lineas
        ]
        cursor.rowcount = 1
        mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)
        return cursor

    @patch("stock.services.inventario_fisico.recalcular_ajuste_post_snapshot")
    @patch("stock.services.inventario_fisico.obtener_campana")
    def test_servicio_existe_y_falla_sin_implementacion_minima(
        self, mock_obtener, mock_recalc
    ):
        mock_obtener.return_value = self._campana()
        mock_recalc.return_value = (True, {"lineas_actualizadas": 0})
        ok, _result = svc.marcar_no_contados_como_cero("emp", 7, id_usuario=1)
        self.assertIsInstance(ok, bool)

    @patch("stock.services.inventario_fisico.contar_desglose_no_contados")
    @patch("stock.services.inventario_fisico.recalcular_ajuste_post_snapshot")
    @patch("stock.services.inventario_fisico._insert_auditoria_ajuste")
    @patch("stock.services.inventario_fisico._proyectar_linea")
    @patch("stock.services.inventario_fisico.mysql_cursor")
    @patch("stock.services.inventario_fisico.obtener_campana")
    def test_uuid_36_chars_y_motivo_supervisor_es(
        self,
        mock_obtener,
        mock_cursor_ctx,
        mock_proyectar,
        mock_auditoria,
        mock_recalc,
        mock_desglose,
    ):
        mock_obtener.return_value = self._campana()
        mock_recalc.return_value = (True, {"lineas_actualizadas": 1})
        mock_desglose.return_value = {
            "lineas_no_contadas": 1,
            "lineas_con_snap_ne0": 1,
            "lineas_con_mov_post": 0,
        }
        mock_proyectar.return_value = 1
        cursor = self._mock_cursor_con_lineas(
            mock_cursor_ctx, self._lineas_sin_contar(1, saldo=Decimal("3"))
        )

        ok, result = svc.marcar_no_contados_como_cero("emp", 7, id_usuario=99)
        self.assertTrue(ok)
        self.assertEqual(result["lineas_marcadas"], 1)

        insert_sql = cursor.execute.call_args_list[2].args[0]
        insert_params = cursor.execute.call_args_list[2].args[1]
        self.assertIn("INSERT INTO inv_fisico_evento", insert_sql)
        client_event_id = insert_params[0]
        self.assertEqual(len(client_event_id), 36)
        uuid.UUID(client_event_id)
        self.assertEqual(insert_params[8], svc.MOTIVO_CONTADO_CERO_SUPERVISOR)
        self.assertTrue(str(insert_params[8]).strip())

    @patch("stock.services.inventario_fisico.contar_desglose_no_contados")
    @patch("stock.services.inventario_fisico.recalcular_ajuste_post_snapshot")
    @patch("stock.services.inventario_fisico._insert_auditoria_ajuste")
    @patch("stock.services.inventario_fisico._proyectar_linea")
    @patch("stock.services.inventario_fisico.mysql_cursor")
    @patch("stock.services.inventario_fisico.obtener_campana")
    def test_cinco_null_tres_contadas_proyecta_cinco(
        self,
        mock_obtener,
        mock_cursor_ctx,
        mock_proyectar,
        mock_auditoria,
        mock_recalc,
        mock_desglose,
    ):
        mock_obtener.return_value = self._campana()
        mock_recalc.return_value = (True, {"lineas_actualizadas": 5})
        mock_desglose.return_value = {
            "lineas_no_contadas": 5,
            "lineas_con_snap_ne0": 2,
            "lineas_con_mov_post": 1,
        }
        mock_proyectar.return_value = 1
        lineas = self._lineas_sin_contar(5)
        self._mock_cursor_con_lineas(mock_cursor_ctx, lineas)

        ok, result = svc.marcar_no_contados_como_cero("emp", 7, id_usuario=1)
        self.assertTrue(ok)
        self.assertEqual(result["lineas_marcadas"], 5)
        self.assertEqual(mock_proyectar.call_count, 5)
        for call_args in mock_proyectar.call_args_list:
            self.assertEqual(call_args.args[5], Decimal("0"))
            self.assertTrue(call_args.kwargs.get("solo_si_sin_contar"))

    @patch("stock.services.inventario_fisico.contar_desglose_no_contados")
    @patch("stock.services.inventario_fisico.recalcular_ajuste_post_snapshot")
    @patch("stock.services.inventario_fisico._insert_auditoria_ajuste")
    @patch("stock.services.inventario_fisico._proyectar_linea")
    @patch("stock.services.inventario_fisico.mysql_cursor")
    @patch("stock.services.inventario_fisico.obtener_campana")
    def test_sync_concurrente_gana_no_marca_linea(
        self,
        mock_obtener,
        mock_cursor_ctx,
        mock_proyectar,
        mock_auditoria,
        mock_recalc,
        mock_desglose,
    ):
        mock_obtener.return_value = self._campana()
        mock_recalc.return_value = (True, {"lineas_actualizadas": 1})
        mock_desglose.return_value = {
            "lineas_no_contadas": 2,
            "lineas_con_snap_ne0": 0,
            "lineas_con_mov_post": 0,
        }
        mock_proyectar.side_effect = [1, 0]
        lineas = self._lineas_sin_contar(2)
        cursor = MagicMock()
        cursor.fetchall.return_value = lineas
        cursor.fetchone.side_effect = [
            {"cantidad_contada": None},
            {"cantidad_contada": Decimal("4")},
        ]
        cursor.rowcount = 1
        mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)

        ok, result = svc.marcar_no_contados_como_cero("emp", 7, id_usuario=1)
        self.assertTrue(ok)
        self.assertEqual(result["lineas_marcadas"], 1)
        self.assertEqual(mock_auditoria.call_count, 1)

    @patch("stock.services.inventario_fisico.contar_desglose_no_contados")
    @patch("stock.services.inventario_fisico.recalcular_ajuste_post_snapshot")
    @patch("stock.services.inventario_fisico._insert_auditoria_ajuste")
    @patch("stock.services.inventario_fisico._proyectar_linea")
    @patch("stock.services.inventario_fisico.mysql_cursor")
    @patch("stock.services.inventario_fisico.obtener_campana")
    def test_un_evento_y_una_auditoria_por_linea(
        self,
        mock_obtener,
        mock_cursor_ctx,
        mock_proyectar,
        mock_auditoria,
        mock_recalc,
        mock_desglose,
    ):
        mock_obtener.return_value = self._campana()
        mock_recalc.return_value = (True, {"lineas_actualizadas": 2})
        mock_desglose.return_value = {
            "lineas_no_contadas": 2,
            "lineas_con_snap_ne0": 0,
            "lineas_con_mov_post": 0,
        }
        mock_proyectar.return_value = 1
        cursor = self._mock_cursor_con_lineas(
            mock_cursor_ctx, self._lineas_sin_contar(2)
        )

        ok, result = svc.marcar_no_contados_como_cero("emp", 7, id_usuario=5)
        self.assertTrue(ok)
        self.assertEqual(result["lineas_marcadas"], 2)

        evento_inserts = [
            c
            for c in cursor.execute.call_args_list
            if c.args and "INSERT INTO inv_fisico_evento" in c.args[0]
        ]
        self.assertEqual(len(evento_inserts), 2)
        self.assertEqual(mock_auditoria.call_count, 2)
        for aud_call in mock_auditoria.call_args_list:
            self.assertEqual(
                aud_call.kwargs.get("accion"), svc.ACCION_AUDIT_CONTADO_CERO_MASIVO
            )

    @patch("stock.services.inventario_fisico.recalcular_ajuste_post_snapshot")
    @patch("stock.services.inventario_fisico.obtener_campana")
    def test_estados_en_conteo_y_en_revision_ok_aplicada_400(
        self, mock_obtener, mock_recalc
    ):
        mock_recalc.return_value = (True, {"lineas_actualizadas": 0})

        for estado_ok in (svc.ESTADO_EN_CONTEO, svc.ESTADO_EN_REVISION):
            with self.subTest(estado=estado_ok):
                with patch(
                    "stock.services.inventario_fisico.contar_desglose_no_contados",
                    return_value={
                        "lineas_no_contadas": 0,
                        "lineas_con_snap_ne0": 0,
                        "lineas_con_mov_post": 0,
                    },
                ), patch("stock.services.inventario_fisico.mysql_cursor") as mock_cursor_ctx:
                    mock_obtener.return_value = self._campana(estado=estado_ok)
                    cursor = MagicMock()
                    cursor.fetchall.return_value = []
                    mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=cursor)
                    mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)
                    ok, result = svc.marcar_no_contados_como_cero("emp", 7, id_usuario=1)
                    self.assertTrue(ok, result)
                    self.assertEqual(result["lineas_marcadas"], 0)

        mock_obtener.return_value = self._campana(estado=svc.ESTADO_APLICADO)
        ok, result = svc.marcar_no_contados_como_cero("emp", 7, id_usuario=1)
        self.assertFalse(ok)
        self.assertIn("error", result)

    @patch("stock.services.inventario_fisico.contar_desglose_no_contados")
    @patch("stock.services.inventario_fisico.recalcular_ajuste_post_snapshot")
    @patch("stock.services.inventario_fisico.mysql_cursor")
    @patch("stock.services.inventario_fisico.obtener_campana")
    def test_idempotencia_sin_null_restantes(
        self, mock_obtener, mock_cursor_ctx, mock_recalc, mock_desglose
    ):
        mock_obtener.return_value = self._campana()
        mock_recalc.return_value = (True, {"lineas_actualizadas": 0})
        mock_desglose.return_value = {
            "lineas_no_contadas": 0,
            "lineas_con_snap_ne0": 0,
            "lineas_con_mov_post": 0,
        }
        cursor = MagicMock()
        cursor.fetchall.return_value = []
        cursor.fetchone.return_value = None
        mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)

        ok, result = svc.marcar_no_contados_como_cero("emp", 7, id_usuario=1)
        self.assertTrue(ok)
        self.assertEqual(result["lineas_marcadas"], 0)

    @patch("core.services.administranet_stock.alta_movimiento")
    @patch("stock.services.inventario_fisico.contar_desglose_no_contados")
    @patch("stock.services.inventario_fisico.recalcular_ajuste_post_snapshot")
    @patch("stock.services.inventario_fisico._insert_auditoria_ajuste")
    @patch("stock.services.inventario_fisico._proyectar_linea")
    @patch("stock.services.inventario_fisico.mysql_cursor")
    @patch("stock.services.inventario_fisico.obtener_campana")
    def test_no_invoca_mstock(
        self,
        mock_obtener,
        mock_cursor_ctx,
        mock_proyectar,
        mock_auditoria,
        mock_recalc,
        mock_desglose,
        mock_alta,
    ):
        mock_obtener.return_value = self._campana()
        mock_recalc.return_value = (True, {"lineas_actualizadas": 1})
        mock_desglose.return_value = {
            "lineas_no_contadas": 1,
            "lineas_con_snap_ne0": 1,
            "lineas_con_mov_post": 0,
        }
        mock_proyectar.return_value = 1
        self._mock_cursor_con_lineas(mock_cursor_ctx, self._lineas_sin_contar(1))

        ok, _result = svc.marcar_no_contados_como_cero("emp", 7, id_usuario=1)
        self.assertTrue(ok)
        mock_alta.assert_not_called()

    @patch("stock.services.inventario_fisico.contar_desglose_no_contados")
    @patch("stock.services.inventario_fisico.recalcular_ajuste_post_snapshot")
    @patch("stock.services.inventario_fisico._proyectar_linea")
    @patch("stock.services.inventario_fisico.mysql_cursor")
    @patch("stock.services.inventario_fisico.obtener_campana")
    def test_recalc_pisar_overrides_false(
        self,
        mock_obtener,
        mock_cursor_ctx,
        mock_proyectar,
        mock_recalc,
        mock_desglose,
    ):
        mock_obtener.return_value = self._campana()
        mock_desglose.return_value = {
            "lineas_no_contadas": 1,
            "lineas_con_snap_ne0": 0,
            "lineas_con_mov_post": 0,
        }
        mock_proyectar.return_value = 1
        mock_recalc.return_value = (True, {"lineas_actualizadas": 1})
        self._mock_cursor_con_lineas(mock_cursor_ctx, self._lineas_sin_contar(1))

        svc.marcar_no_contados_como_cero("emp", 7, id_usuario=42)
        mock_recalc.assert_called_once_with(
            "emp", 7, id_usuario=42, pisar_overrides=False
        )

    @patch("stock.services.inventario_fisico.contar_desglose_no_contados")
    @patch("stock.services.inventario_fisico.recalcular_ajuste_post_snapshot")
    @patch("stock.services.inventario_fisico._insert_auditoria_ajuste")
    @patch("stock.services.inventario_fisico._proyectar_linea")
    @patch("stock.services.inventario_fisico.mysql_cursor")
    @patch("stock.services.inventario_fisico.obtener_campana")
    def test_recalc_falla_ok_con_advertencia_sin_rollback(
        self,
        mock_obtener,
        mock_cursor_ctx,
        mock_proyectar,
        mock_auditoria,
        mock_recalc,
        mock_desglose,
    ):
        mock_obtener.return_value = self._campana()
        mock_desglose.return_value = {
            "lineas_no_contadas": 1,
            "lineas_con_snap_ne0": 0,
            "lineas_con_mov_post": 0,
        }
        mock_proyectar.return_value = 1
        mock_recalc.return_value = (
            False,
            {"error": "No se pudo recalcular el ajuste post-snapshot."},
        )
        self._mock_cursor_con_lineas(mock_cursor_ctx, self._lineas_sin_contar(1))

        ok, result = svc.marcar_no_contados_como_cero("emp", 7, id_usuario=1)
        self.assertTrue(ok)
        self.assertEqual(result["lineas_marcadas"], 1)
        self.assertIsNotNone(result.get("advertencia"))
        self.assertEqual(mock_auditoria.call_count, 1)

    @patch("stock.services.inventario_fisico.calcular_ajuste_post_snapshot")
    @patch("stock.services.inventario_fisico.mysql_cursor")
    def test_desglose_snap_ne0_y_mov_post_coherentes(
        self, mock_cursor_ctx, mock_netos
    ):
        mock_netos.return_value = {(100, 3): Decimal("2"), (101, 3): Decimal("0")}
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {"id_articulo": 100, "id_deposito": 3, "saldo_snapshot": Decimal("5")},
            {"id_articulo": 101, "id_deposito": 3, "saldo_snapshot": Decimal("0")},
            {"id_articulo": 102, "id_deposito": 3, "saldo_snapshot": Decimal("0")},
        ]
        mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)

        desglose = svc.contar_desglose_no_contados("emp", 7)
        self.assertEqual(desglose["lineas_no_contadas"], 3)
        self.assertEqual(desglose["lineas_con_snap_ne0"], 1)
        self.assertEqual(desglose["lineas_con_mov_post"], 1)


@override_settings(
    SESSION_ENGINE="django.contrib.sessions.backends.cache",
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "inv-fisico-marcar-cero-api-tests",
        }
    },
)
class ApiCampanaMarcarNoContadosCeroTest(SimpleTestCase):
    def _request_post(self, id_campana=7, *, is_admin=True, tiene_permiso=True):
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.http import HttpResponse
        from django.test import RequestFactory

        rf = RequestFactory()
        request = rf.post(
            reverse(
                "stock:api_campana_marcar_no_contados_cero",
                kwargs={"id_campana": id_campana},
            ),
            data=json.dumps({}),
            content_type="application/json",
        )
        SessionMiddleware(lambda req: HttpResponse()).process_request(request)
        request.session["user"] = {
            "base_empresa": "emp",
            "id_usuario": 1,
            "id_puesto": 1,
            "cod_usuario": "operador",
        }
        request.session.save()
        user = MagicMock()
        user.is_authenticated = True
        user.is_admin = MagicMock(return_value=is_admin)
        user.tiene_permiso = MagicMock(return_value=tiene_permiso)
        user.cod_usuario = "operador"
        user.roles = MagicMock()
        user.roles.all.return_value = []
        request.user = user
        return request

    @patch("stock.services.inventario_fisico.marcar_no_contados_como_cero")
    def test_api_exito_200_con_desglose(self, mock_marcar):
        from stock.api_views import api_campana_marcar_no_contados_cero

        mock_marcar.return_value = (
            True,
            {
                "lineas_marcadas": 10,
                "lineas_con_snap_ne0": 3,
                "lineas_con_mov_post": 1,
                "advertencia": None,
                "mensaje": "10 líneas marcadas con Contado = 0.",
            },
        )
        resp = api_campana_marcar_no_contados_cero(self._request_post(), id_campana=7)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["ok"])
        self.assertEqual(data["lineas_marcadas"], 10)
        self.assertEqual(data["lineas_con_snap_ne0"], 3)
        self.assertEqual(data["lineas_con_mov_post"], 1)
        self.assertIsNone(data["advertencia"])

    @patch("stock.services.inventario_fisico.marcar_no_contados_como_cero")
    def test_api_estado_invalido_400(self, mock_marcar):
        from stock.api_views import api_campana_marcar_no_contados_cero

        mock_marcar.return_value = (False, {"error": "No se puede marcar contado cero."})
        resp = api_campana_marcar_no_contados_cero(self._request_post(), id_campana=7)
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.content)
        self.assertIn("error", data)

    @patch("stock.services.inventario_fisico.marcar_no_contados_como_cero")
    def test_api_advertencia_recalc_en_respuesta(self, mock_marcar):
        from stock.api_views import api_campana_marcar_no_contados_cero

        mock_marcar.return_value = (
            True,
            {
                "lineas_marcadas": 2,
                "lineas_con_snap_ne0": 0,
                "lineas_con_mov_post": 0,
                "advertencia": "No se pudo recalcular el ajuste post-snapshot.",
                "mensaje": "2 líneas marcadas con Contado = 0.",
            },
        )
        resp = api_campana_marcar_no_contados_cero(self._request_post(), id_campana=7)
        data = json.loads(resp.content)
        self.assertTrue(data["ok"])
        self.assertEqual(data["lineas_marcadas"], 2)
        self.assertIn("recalcular", data["advertencia"].lower())

    def test_api_sin_permiso_403(self):
        from django.core.exceptions import PermissionDenied
        from stock.api_views import api_campana_marcar_no_contados_cero

        with self.assertRaises(PermissionDenied):
            api_campana_marcar_no_contados_cero(
                self._request_post(is_admin=False, tiene_permiso=False),
                id_campana=7,
            )


@override_settings(
    SESSION_ENGINE="django.contrib.sessions.backends.cache",
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "inv-fisico-marcar-cero-vista-tests",
        }
    },
)
class AnalizadorMarcarCeroContextoTest(SimpleTestCase):
    @patch("stock.views.render")
    @patch("stock.services.inventario_fisico.contar_desglose_no_contados")
    @patch("stock.services.inventario_fisico.recalcular_ajuste_post_snapshot")
    @patch("stock.services.inventario_fisico.listar_lineas_analizador")
    @patch("stock.services.inventario_fisico.obtener_resumen_monitor")
    @patch("stock.services.inventario_fisico.obtener_campana")
    @patch("stock.services.inventario_tabla.listar_marcas_catalogo")
    def test_contexto_counts_globales_ignoran_filtro_marcas(
        self,
        mock_marcas,
        mock_campana,
        mock_resumen,
        mock_lineas,
        mock_recalc,
        mock_desglose,
        mock_render,
    ):
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.http import HttpResponse
        from django.test import RequestFactory

        from stock.views import inventario_fisico_analizador_view

        mock_marcas.return_value = [{"value": 5, "label": "Marca A"}]
        mock_recalc.return_value = (True, {"lineas_actualizadas": 0})
        mock_campana.return_value = {
            "id_campana": 3,
            "estado": svc.ESTADO_EN_REVISION,
            "fecha": "2026-07-23",
            "depositos": [3],
        }
        mock_resumen.return_value = {
            "conflictos_sync": 0,
            "bloqueo_autorizar": False,
            "bloqueo_estado": False,
            "total": 20,
            "contados": 8,
            "pendientes": 12,
        }
        mock_desglose.return_value = {
            "lineas_no_contadas": 12,
            "lineas_con_snap_ne0": 3,
            "lineas_con_mov_post": 1,
        }
        mock_lineas.side_effect = lambda *args, **kwargs: (
            [{"id_linea": 1, "id_marca": 5}]
            if kwargs.get("marcas_incluidos")
            else [{"id_linea": i} for i in range(1, 6)]
        )
        mock_render.return_value = HttpResponse("ok")

        rf = RequestFactory()
        request = rf.get(
            reverse("stock:inventario_fisico_analizador", kwargs={"id_campana": 3}),
            {"marcas_incluidos": "5"},
        )
        SessionMiddleware(lambda req: HttpResponse()).process_request(request)
        request.session["user"] = {
            "base_empresa": "emp",
            "id_usuario": 1,
            "cod_usuario": "supervisor",
        }
        request.session.save()
        user = MagicMock()
        user.is_authenticated = True
        user.is_admin = MagicMock(return_value=True)
        request.user = user

        inventario_fisico_analizador_view(request, id_campana=3)
        context = mock_render.call_args.args[2]
        self.assertEqual(context["lineas_no_contadas"], 12)
        self.assertEqual(context["lineas_no_contadas_snap_ne0"], 3)
        self.assertEqual(context["lineas_no_contadas_mov_post"], 1)
        self.assertTrue(context["puede_marcar_cero"])
        mock_desglose.assert_called_once_with("emp", 3)
