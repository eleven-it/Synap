"""Tests Phase 5 — batch checkout masivo + compensación."""

import json
from decimal import Decimal
from datetime import date
from unittest.mock import MagicMock, patch

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.checkout_relay_views import _session_pv
from ecom.models import EcomPedidoMasivoDraft, EcomPedidoMasivoDraftCelda
from ecom.pedido_masivo_views import PedidoMasivoConfirmarAPIView
from ecom.services.batch_checkout_masivo import (
    PREVIEW_CELDAS_LIMITE_BLANDO,
    calcular_totales_lote_masivo,
    confirmar_lote_masivo,
    confirmar_lote_masivo_stream,
)
from ecom.services.pedido_cabecera_comercial import PedidoCabeceraComercial
from ecom.services.recibo_catalogos_service import listar_puntos_venta_usuario


class TestConfirmarLoteMasivo(TestCase):
    def _draft_con_dos_sucursales(self):
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_b",
            id_usuario=9,
            id_cliente=100,
            cod_viajante=2,
            estado=EcomPedidoMasivoDraft.ESTADO_BORRADOR,
        )
        EcomPedidoMasivoDraftCelda.objects.create(
            draft=d, id_articulo=1, id_cliente_domicilio=10, cantidad_packs=Decimal("2")
        )
        EcomPedidoMasivoDraftCelda.objects.create(
            draft=d, id_articulo=1, id_cliente_domicilio=20, cantidad_packs=Decimal("3")
        )
        return d

    @patch("ecom.services.batch_checkout_masivo.opciones_presentacion_articulo")
    @patch("ecom.services.batch_checkout_masivo.agregar_item")
    @patch("ecom.services.batch_checkout_masivo.confirmar")
    def test_ok_dos_ped(self, mock_conf, mock_add, mock_opts):
        mock_opts.return_value = {
            "tipo_unidad_defecto": "Unidad",
            "opciones": [{"tipo": "Unidad", "multiplicador": 1}],
        }
        mock_add.return_value = (MagicMock(), None)
        mock_conf.side_effect = [
            (True, None, {"codigo_movimiento": 101, "nro_comprobante": "A-1"}),
            (True, None, {"codigo_movimiento": 102, "nro_comprobante": "A-2"}),
        ]
        d = self._draft_con_dos_sucursales()
        ok, msg, payload = confirmar_lote_masivo(
            d, id_usuario=9, id_punto_venta=1, cod_viajante=2
        )
        self.assertTrue(ok)
        d.refresh_from_db()
        self.assertEqual(d.estado, EcomPedidoMasivoDraft.ESTADO_CONFIRMADO)
        self.assertEqual(d.codigos_movimiento, [101, 102])
        self.assertEqual(mock_conf.call_count, 2)
        # id_cliente_domicilio en cada checkout
        doms = [
            mock_conf.call_args_list[i].args[1].id_cliente_domicilio for i in range(2)
        ]
        self.assertEqual(sorted(doms), [10, 20])

    @patch("ecom.services.batch_checkout_masivo.opciones_presentacion_articulo")
    @patch("ecom.services.batch_checkout_masivo.agregar_item")
    @patch("ecom.services.batch_checkout_masivo.confirmar")
    def test_propaga_cabecera_a_cada_ped(self, mock_conf, mock_add, mock_opts):
        mock_opts.return_value = {
            "tipo_unidad_defecto": "Unidad",
            "opciones": [{"tipo": "Unidad", "multiplicador": 1}],
        }
        mock_add.return_value = (MagicMock(), None)
        mock_conf.side_effect = [
            (True, None, {"codigo_movimiento": 401, "nro_comprobante": "C-1"}),
            (True, None, {"codigo_movimiento": 402, "nro_comprobante": "C-2"}),
        ]
        d = self._draft_con_dos_sucursales()
        cab = PedidoCabeceraComercial(
            fecha_pedido=date(2026, 7, 10),
            fecha_entrega=date(2026, 7, 20),
            vencimiento=date(2026, 7, 25),
            id_condventa=4,
            cond_venta="Contado",
            lista_id=4,
        )
        ok, _, _ = confirmar_lote_masivo(
            d,
            id_usuario=9,
            id_punto_venta=1,
            cod_viajante=2,
            cabecera=cab,
            es_supervisor=True,
        )
        self.assertTrue(ok)
        self.assertEqual(mock_conf.call_count, 2)
        for call in mock_conf.call_args_list:
            datos = call.args[1]
            self.assertEqual(datos.fecha_pedido, cab.fecha_pedido)
            self.assertEqual(datos.lista_id, 4)
            self.assertEqual(datos.vencimiento, cab.vencimiento)

    @patch("ecom.services.batch_checkout_masivo.opciones_presentacion_articulo")
    @patch("ecom.services.batch_checkout_masivo.agregar_item")
    @patch("ecom.services.batch_checkout_masivo.confirmar")
    @patch("ecom.services.batch_checkout_masivo.recalcular_totales")
    def test_confirmar_aplica_descuentos_y_operativo(
        self, mock_recalc, mock_conf, mock_add, mock_opts
    ):
        mock_opts.return_value = {
            "tipo_unidad_defecto": "Unidad",
            "opciones": [{"tipo": "Unidad", "multiplicador": 1}],
        }
        mock_add.return_value = (MagicMock(), None)
        mock_conf.side_effect = [
            (True, None, {"codigo_movimiento": 301, "nro_comprobante": "B-1"}),
            (True, None, {"codigo_movimiento": 302, "nro_comprobante": "B-2"}),
        ]
        d = self._draft_con_dos_sucursales()
        d.descuentos_fila = {"1": 10.0}
        d.descuento_pie_pct = Decimal("5")
        d.save()
        sess = {
            "id_vendedor_usr": 16,
            "cod_viajante_operativo": 21,
            "vendedor_a_cargo": [21, 10],
        }
        ok, _, payload = confirmar_lote_masivo(
            d,
            id_usuario=9,
            id_punto_venta=1,
            desc_pie_pct=5,
            sess_user=sess,
        )
        self.assertTrue(ok)
        self.assertEqual(payload.get("cod_viajante"), 21)
        mock_add.assert_called()
        kwargs_add = mock_add.call_args.kwargs
        self.assertEqual(kwargs_add.get("descuento_cliente"), Decimal("10"))
        mock_conf.assert_called()
        self.assertEqual(mock_conf.call_args.kwargs.get("cod_viajante"), 21)

    @patch("ecom.services.batch_checkout_masivo.anular_pedido_relay")
    @patch("ecom.services.batch_checkout_masivo.opciones_presentacion_articulo")
    @patch("ecom.services.batch_checkout_masivo.agregar_item")
    @patch("ecom.services.batch_checkout_masivo.confirmar")
    def test_fail_segunda_compensa_primera(self, mock_conf, mock_add, mock_opts, mock_anular):
        mock_opts.return_value = {
            "tipo_unidad_defecto": "Unidad",
            "opciones": [{"tipo": "Unidad", "multiplicador": 1}],
        }
        mock_add.return_value = (MagicMock(), None)
        mock_conf.side_effect = [
            (True, None, {"codigo_movimiento": 201}),
            (False, "Stock insuficiente", None),
        ]
        mock_anular.return_value = {"msg": "ok", "error": ""}
        d = self._draft_con_dos_sucursales()
        # celdas count before
        n_celdas = d.celdas.count()
        ok, msg, payload = confirmar_lote_masivo(
            d, id_usuario=9, id_punto_venta=1, cod_viajante=2
        )
        self.assertFalse(ok)
        self.assertIn("Stock", msg)
        mock_anular.assert_called_once()
        self.assertEqual(mock_anular.call_args.args[1], 201)
        d.refresh_from_db()
        self.assertEqual(d.estado, EcomPedidoMasivoDraft.ESTADO_BORRADOR)
        self.assertEqual(d.codigos_movimiento, [])
        self.assertIn("20", d.ultimo_error)
        self.assertEqual(d.celdas.count(), n_celdas)

    def test_sin_cantidades(self):
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_b", id_usuario=1, id_cliente=1
        )
        ok, msg, _ = confirmar_lote_masivo(d, id_usuario=1, id_punto_venta=1)
        self.assertFalse(ok)
        self.assertIn("cantidades", msg.lower())

    @patch("ecom.services.batch_checkout_masivo.validar_multiplos_draft")
    def test_rechaza_confirmar_si_multiplo_invalido(self, mock_val):
        d = self._draft_con_dos_sucursales()
        mock_val.return_value = (
            False,
            "Hay 1 cantidad(es) que no respetan la unidad de empaquetado (6).",
            [{"id_articulo": 1, "codigo": "X", "cantidad": 7, "multiplo_empaque": 6}],
        )
        ok, msg, payload = confirmar_lote_masivo(
            d, id_usuario=9, id_punto_venta=1, cod_viajante=2
        )
        self.assertFalse(ok)
        self.assertIn("empaquetado", msg.lower())
        self.assertEqual(payload.get("code"), "multiplo_empaque")
        self.assertEqual(len(payload.get("infracciones_multiplo") or []), 1)
        d.refresh_from_db()
        self.assertEqual(d.estado, EcomPedidoMasivoDraft.ESTADO_BORRADOR)

    @patch("ecom.services.batch_checkout_masivo.opciones_presentacion_articulo")
    @patch("ecom.services.batch_checkout_masivo.agregar_item")
    @patch("ecom.services.batch_checkout_masivo.confirmar")
    def test_stream_emite_eventos_por_sucursal(self, mock_conf, mock_add, mock_opts):
        mock_opts.return_value = {
            "tipo_unidad_defecto": "Unidad",
            "opciones": [{"tipo": "Unidad", "multiplicador": 1}],
        }
        mock_add.return_value = (MagicMock(), None)
        mock_conf.side_effect = [
            (True, None, {"codigo_movimiento": 501, "nro_comprobante": "S-1"}),
            (True, None, {"codigo_movimiento": 502, "nro_comprobante": "S-2"}),
        ]
        d = self._draft_con_dos_sucursales()
        eventos = list(
            confirmar_lote_masivo_stream(
                d,
                id_usuario=9,
                id_punto_venta=1,
                cod_viajante=2,
                nombres_sucursales={10: "Suc A", 20: "Suc B"},
            )
        )
        tipos = [e.get("event") for e in eventos]
        self.assertEqual(tipos[0], "inicio")
        self.assertEqual(tipos[-1], "fin")
        self.assertEqual(eventos[0]["total"], 2)
        suc = [e for e in eventos if e.get("event") == "sucursal"]
        self.assertEqual(len(suc), 4)
        self.assertEqual(suc[0]["estado"], "procesando")
        self.assertEqual(suc[0]["nombre"], "Suc A")
        self.assertEqual(suc[1]["estado"], "ok")
        self.assertEqual(suc[1]["codigo_movimiento"], 501)
        fin = eventos[-1]
        self.assertTrue(fin["ok"])
        self.assertEqual(fin["codigos_movimiento"], [501, 502])

    @patch("ecom.services.batch_checkout_masivo.anular_pedido_relay")
    @patch("ecom.services.batch_checkout_masivo.opciones_presentacion_articulo")
    @patch("ecom.services.batch_checkout_masivo.agregar_item")
    @patch("ecom.services.batch_checkout_masivo.confirmar")
    def test_stream_fail_compensa(self, mock_conf, mock_add, mock_opts, mock_anular):
        mock_opts.return_value = {
            "tipo_unidad_defecto": "Unidad",
            "opciones": [{"tipo": "Unidad", "multiplicador": 1}],
        }
        mock_add.return_value = (MagicMock(), None)
        mock_conf.side_effect = [
            (True, None, {"codigo_movimiento": 601}),
            (False, "Stock insuficiente", None),
        ]
        mock_anular.return_value = {"msg": "ok", "error": ""}
        d = self._draft_con_dos_sucursales()
        eventos = list(
            confirmar_lote_masivo_stream(
                d, id_usuario=9, id_punto_venta=1, cod_viajante=2
            )
        )
        fin = eventos[-1]
        self.assertFalse(fin["ok"])
        self.assertIn("Stock", fin["message"])
        mock_anular.assert_called_once()
        errores_suc = [e for e in eventos if e.get("estado") == "error"]
        self.assertEqual(len(errores_suc), 1)


class TestConfirmacionMasivaStreamAPI(TestCase):
    @patch("ecom.pedido_masivo_views.serializar_matriz", return_value={"estado": "confirmado"})
    @patch("ecom.pedido_masivo_views.confirmar_lote_masivo_stream")
    @patch("ecom.pedido_masivo_views.es_supervisor_desde_ctx", return_value=False)
    @patch("ecom.pedido_masivo_views.ctx_desde_request", return_value={})
    @patch("ecom.pedido_masivo_views._resolver_cabecera_masivo")
    def test_api_stream_ndjson(
        self,
        mock_cabecera,
        _mock_ctx,
        _mock_supervisor,
        mock_stream,
        _mock_matriz,
    ):
        draft = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_b",
            id_usuario=9,
            id_cliente=100,
            estado=EcomPedidoMasivoDraft.ESTADO_BORRADOR,
        )

        def _gen(*_a, **_k):
            yield {"event": "inicio", "total": 1}
            yield {
                "event": "fin",
                "ok": True,
                "message": "Se crearon 1 pedido(s).",
                "codigos_movimiento": [900],
                "errores": {},
                "compensacion": [],
            }

        mock_cabecera.return_value = (MagicMock(lista_id=1), None)
        mock_stream.side_effect = _gen

        request = APIRequestFactory().post(
            "/ecom/api/mayoristapp/pedido-masivo/confirmar/",
            {"draft_id": draft.pk, "stream": True},
            format="json",
        )
        SessionMiddleware(lambda r: HttpResponse()).process_request(request)
        request.session["user"] = {
            "id_usuario": 9,
            "base_empresa": "emp_b",
            "id_punto_venta": 1,
        }
        request.session.save()
        force_authenticate(
            request,
            user=MagicMock(is_authenticated=True, is_superuser=True),
        )

        response = PedidoMasivoConfirmarAPIView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn("application/x-ndjson", response["Content-Type"])
        body = b"".join(response.streaming_content).decode("utf-8")
        lineas = [json.loads(ln) for ln in body.strip().split("\n") if ln.strip()]
        self.assertEqual(lineas[0]["event"], "inicio")
        self.assertTrue(lineas[-1]["ok"])
        self.assertIn("matriz", lineas[-1])
        mock_stream.assert_called_once()

    @patch("ecom.pedido_masivo_views.serializar_matriz", return_value={"estado": "confirmado"})
    @patch("ecom.pedido_masivo_views.confirmar_lote_masivo_stream")
    @patch("ecom.pedido_masivo_views.es_supervisor_desde_ctx", return_value=False)
    @patch("ecom.pedido_masivo_views.ctx_desde_request", return_value={})
    @patch("ecom.pedido_masivo_views._resolver_cabecera_masivo")
    def test_api_stream_accept_wildcard_y_ndjson_no_406(
        self,
        mock_cabecera,
        _mock_ctx,
        _mock_supervisor,
        mock_stream,
        _mock_matriz,
    ):
        """La vista negocia Accept */* y application/x-ndjson sin responder 406."""
        draft = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_b",
            id_usuario=9,
            id_cliente=100,
            estado=EcomPedidoMasivoDraft.ESTADO_BORRADOR,
        )

        def _gen(*_a, **_k):
            yield {"event": "inicio", "total": 1}
            yield {
                "event": "fin",
                "ok": True,
                "message": "Se crearon 1 pedido(s).",
                "codigos_movimiento": [901],
                "errores": {},
                "compensacion": [],
            }

        mock_cabecera.return_value = (MagicMock(lista_id=1), None)
        mock_stream.side_effect = _gen

        request = APIRequestFactory().post(
            "/ecom/api/mayoristapp/pedido-masivo/confirmar/",
            {"draft_id": draft.pk, "stream": True},
            format="json",
            HTTP_ACCEPT="*/*",
        )
        SessionMiddleware(lambda r: HttpResponse()).process_request(request)
        request.session["user"] = {
            "id_usuario": 9,
            "base_empresa": "emp_b",
            "id_punto_venta": 1,
        }
        request.session.save()
        force_authenticate(
            request,
            user=MagicMock(is_authenticated=True, is_superuser=True),
        )

        response = PedidoMasivoConfirmarAPIView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn("application/x-ndjson", response["Content-Type"])
        # Consumir el stream para ejecutar el generador mockeado.
        _ = b"".join(response.streaming_content)
        mock_stream.assert_called_once()

        request_ndjson = APIRequestFactory().post(
            "/ecom/api/mayoristapp/pedido-masivo/confirmar/",
            {"draft_id": draft.pk, "stream": True},
            format="json",
            HTTP_ACCEPT="application/x-ndjson",
        )
        SessionMiddleware(lambda r: HttpResponse()).process_request(request_ndjson)
        request_ndjson.session["user"] = {
            "id_usuario": 9,
            "base_empresa": "emp_b",
            "id_punto_venta": 1,
        }
        request_ndjson.session.save()
        force_authenticate(
            request_ndjson,
            user=MagicMock(is_authenticated=True, is_superuser=True),
        )
        response_ndjson = PedidoMasivoConfirmarAPIView.as_view()(request_ndjson)
        self.assertEqual(response_ndjson.status_code, 200)
        self.assertIn("application/x-ndjson", response_ndjson["Content-Type"])
        _ = b"".join(response_ndjson.streaming_content)
        self.assertEqual(mock_stream.call_count, 2)


class TestConfirmacionMasivaPuntoVenta(TestCase):
    @patch("ecom.pedido_masivo_views.serializar_matriz", return_value={})
    @patch("ecom.pedido_masivo_views.confirmar_lote_masivo")
    @patch("ecom.pedido_masivo_views.es_supervisor_desde_ctx", return_value=False)
    @patch("ecom.pedido_masivo_views.ctx_desde_request", return_value={})
    @patch("ecom.pedido_masivo_views._resolver_cabecera_masivo")
    def test_usa_pv_del_usuario_si_el_body_lo_omite(
        self,
        mock_cabecera,
        _mock_ctx,
        _mock_supervisor,
        mock_confirmar,
        _mock_matriz,
    ):
        draft = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_b",
            id_usuario=9,
            id_cliente=100,
            estado=EcomPedidoMasivoDraft.ESTADO_BORRADOR,
        )
        mock_cabecera.return_value = (MagicMock(lista_id=1), None)
        mock_confirmar.return_value = (True, "Se crearon 1 pedido(s).", {})

        request = APIRequestFactory().post(
            "/ecom/api/mayoristapp/pedido-masivo/confirmar/",
            {"draft_id": draft.pk},
            format="json",
        )
        SessionMiddleware(lambda r: HttpResponse()).process_request(request)
        request.session["user"] = {
            "id_usuario": 9,
            "base_empresa": "emp_b",
            "id_punto_venta": 7,
        }
        request.session.save()
        force_authenticate(
            request,
            user=MagicMock(is_authenticated=True, is_superuser=True),
        )

        response = PedidoMasivoConfirmarAPIView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_confirmar.call_args.kwargs["id_punto_venta"], 7)

    @patch("ecom.pedido_masivo_views._session_pv", side_effect=RuntimeError("fallo PV"))
    def test_error_al_resolver_pv_responde_400(self, _mock_pv):
        draft = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_b",
            id_usuario=9,
            id_cliente=100,
            estado=EcomPedidoMasivoDraft.ESTADO_BORRADOR,
        )
        request = APIRequestFactory().post(
            "/ecom/api/mayoristapp/pedido-masivo/confirmar/",
            {"draft_id": draft.pk},
            format="json",
        )
        SessionMiddleware(lambda r: HttpResponse()).process_request(request)
        request.session["user"] = {"id_usuario": 9, "base_empresa": "emp_b"}
        request.session.save()
        force_authenticate(
            request,
            user=MagicMock(is_authenticated=True, is_superuser=True),
        )

        response = PedidoMasivoConfirmarAPIView.as_view()(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "error_resolucion_pv")

    @patch(
        "ecom.checkout_relay_views.listar_puntos_venta_usuario",
        side_effect=RuntimeError("fallo catálogo"),
    )
    def test_session_pv_falla_cerrado(self, _mock_catalogo):
        request = APIRequestFactory().get("/")
        SessionMiddleware(lambda r: HttpResponse()).process_request(request)
        request.session["user"] = {"base_empresa": "emp_b"}
        request.session.save()

        self.assertIsNone(_session_pv(request))


class TestCatalogoPuntosVenta(TestCase):
    @patch("ecom.services.recibo_catalogos_service.get_mysql_pool")
    def test_lista_filas_tuple_del_cursor_mysql(self, mock_pool):
        conn = mock_pool.return_value.get_connection.return_value.__enter__.return_value
        cursor = conn.cursor.return_value
        cursor.fetchall.return_value = [(7, 12, "si")]

        puntos = listar_puntos_venta_usuario(
            "emp_b",
            {"id_usuario": 9},
        )

        self.assertEqual(
            puntos,
            [
                {
                    "id_punto_venta": 7,
                    "nro_punto_venta": 12,
                    "cont": "si",
                    "value": "7|12|si",
                    "label": "0012",
                }
            ],
        )

    @patch("ecom.services.recibo_catalogos_service.get_mysql_pool")
    def test_fallback_admite_fila_tuple_del_cursor_mysql(self, mock_pool):
        conn = mock_pool.return_value.get_connection.return_value.__enter__.return_value
        cursor = conn.cursor.return_value
        cursor.fetchall.return_value = []
        cursor.fetchone.return_value = (8, 4, None)

        puntos = listar_puntos_venta_usuario(
            "emp_b",
            {"id_usuario": 9, "id_punto_venta": 8},
        )

        self.assertEqual(puntos[0]["id_punto_venta"], 8)
        self.assertEqual(puntos[0]["nro_punto_venta"], 4)
        self.assertEqual(puntos[0]["cont"], "no")


class TestPreviewLoteMasivo(TestCase):
    @patch("ecom.services.batch_checkout_masivo.recalcular_totales")
    @patch("ecom.services.batch_checkout_masivo.agregar_item")
    @patch("ecom.services.batch_checkout_masivo.opciones_presentacion_articulo")
    @patch("ecom.services.batch_checkout_masivo.leer_contexto_cliente_masivo")
    def test_preview_warning_celdas_limite(self, mock_ctx, mock_opts, mock_add, mock_recalc):
        mock_ctx.return_value = {
            "descRenglon": Decimal("0"),
            "descPie": Decimal("0"),
            "lista_id": 1,
        }
        mock_opts.return_value = {
            "tipo_unidad_defecto": "Unidad",
            "opciones": [{"tipo": "Unidad", "multiplicador": 1}],
        }
        mock_add.return_value = (MagicMock(), None)
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_b",
            id_usuario=1,
            id_cliente=100,
        )
        for i in range(PREVIEW_CELDAS_LIMITE_BLANDO + 1):
            EcomPedidoMasivoDraftCelda.objects.create(
                draft=d,
                id_articulo=1,
                id_cliente_domicilio=1000 + i,
                cantidad_packs=Decimal("1"),
            )
        cart_mock = MagicMock()
        cart_mock.subtotal_neto = Decimal("100")
        cart_mock.iva_21 = Decimal("21")
        cart_mock.iva_105 = Decimal("0")
        cart_mock.total = Decimal("121")
        with patch(
            "ecom.services.batch_checkout_masivo._crear_carrito_efimero",
            return_value=cart_mock,
        ):
            r = calcular_totales_lote_masivo(d, id_usuario=1)
        self.assertTrue(r["ok"])
        self.assertIn("límite recomendado", r["warning"])
        self.assertEqual(r["celdas_con_cantidad"], PREVIEW_CELDAS_LIMITE_BLANDO + 1)

    @patch("ecom.services.batch_checkout_masivo.recalcular_totales")
    @patch("ecom.services.batch_checkout_masivo.agregar_item")
    @patch("ecom.services.batch_checkout_masivo.opciones_presentacion_articulo")
    @patch("ecom.services.batch_checkout_masivo.leer_contexto_cliente_masivo")
    def test_preview_pasa_validar_stock_false(
        self, mock_ctx, mock_opts, mock_add, mock_recalc
    ):
        mock_ctx.return_value = {
            "descRenglon": Decimal("0"),
            "descPie": Decimal("0"),
            "lista_id": 1,
        }
        mock_opts.return_value = {
            "tipo_unidad_defecto": "Unidad",
            "opciones": [{"tipo": "Unidad", "multiplicador": 1}],
        }
        mock_add.return_value = (MagicMock(), None)
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_b",
            id_usuario=1,
            id_cliente=100,
        )
        EcomPedidoMasivoDraftCelda.objects.create(
            draft=d,
            id_articulo=1,
            id_cliente_domicilio=10,
            cantidad_packs=Decimal("5"),
        )
        cart_mock = MagicMock()
        cart_mock.subtotal_neto = Decimal("500")
        cart_mock.iva_21 = Decimal("105")
        cart_mock.iva_105 = Decimal("0")
        cart_mock.total = Decimal("605")
        with patch(
            "ecom.services.batch_checkout_masivo._crear_carrito_efimero",
            return_value=cart_mock,
        ):
            r = calcular_totales_lote_masivo(d, id_usuario=1)
        mock_add.assert_called()
        self.assertFalse(mock_add.call_args.kwargs.get("validar_stock", True))
        self.assertTrue(r["ok"])
        self.assertEqual(len(r["sucursales"]), 1)
        self.assertEqual(r["total_lote"]["total"], 605.0)
