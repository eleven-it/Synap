# Tests APIs comprobantes mayoristapp.

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.django_db

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.comprobantes_relay_views import (
    ComprobantesAnularPedidoRelayAPIView,
    ComprobanteAMailEnqueueRelayAPIView,
    ComprobanteAMailQueueStatusRelayAPIView,
    ComprobanteAMailRelayAPIView,
    ComprobantesNoCanceladosRelayAPIView,
    ComprobantesNoCanceladosResumenRelayAPIView,
    ComprobantesPedidosRelayAPIView,
    ComprobantesPresupuestosRelayAPIView,
    ComprobantesRemitosRelayAPIView,
    ComprobantesSugerenciasNroRelayAPIView,
)


def _req_post(path: str, body: dict, session_user: dict):
    factory = APIRequestFactory()
    req = factory.post(path, body, format="json")
    middleware = SessionMiddleware(lambda r: HttpResponse())
    middleware.process_request(req)
    req.session["user"] = session_user
    req.session.save()
    return req


def _req_get(path: str, query: dict, session_user: dict):
    factory = RequestFactory()
    req = factory.get(path, query)
    middleware = SessionMiddleware(lambda r: HttpResponse())
    middleware.process_request(req)
    req.session["user"] = session_user
    req.session.save()
    return req


class TestComprobantesPedidosView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.comprobantes_relay_views.listar_pedidos_relay")
    def test_post_ok(self, mock_listar):
        mock_listar.return_value = [{"CodigoMovimiento": 1}]
        req = _req_post(
            "/ecom/api/mayoristapp/comprobantes/pedidos/?ajax=1",
            {"vendedor": "true", "campoBusca": "-"},
            {"base_empresa": "emp1", "id_vendedor_usr": 1},
        )
        force_authenticate(req, user=self._user())
        resp = ComprobantesPedidosRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["total"], 1)


class TestComprobantesSugerenciasView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.comprobantes_relay_views.sugerencias_nro_comp_relay")
    def test_get_ok(self, mock_s):
        mock_s.return_value = ["100", "1001"]
        req = _req_get(
            "/ecom/api/mayoristapp/comprobantes/sugerencias-nro/",
            {"ajax": "1", "q": "10", "tipo": "PED"},
            {"base_empresa": "emp1", "tipousuario": "vendedor", "id_vendedor_usr": 1},
        )
        force_authenticate(req, user=self._user())
        resp = ComprobantesSugerenciasNroRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["sugerencias"]), 2)


class TestComprobantesPresupuestosView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.comprobantes_relay_views.listar_presupuestos_relay", return_value=[])
    def test_post(self, _m):
        req = _req_post(
            "/ecom/api/mayoristapp/comprobantes/presupuestos/?ajax=1",
            {},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = ComprobantesPresupuestosRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)


class TestComprobantesRemitosView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.comprobantes_relay_views.listar_remitos_relay", return_value=[])
    def test_post(self, _m):
        req = _req_post(
            "/ecom/api/mayoristapp/comprobantes/remitos/?ajax=1",
            {},
            {"base_empresa": "emp1", "id_usuario": 5},
        )
        force_authenticate(req, user=self._user())
        resp = ComprobantesRemitosRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)


class TestComprobanteAMailView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.comprobantes_relay_views.obtener_comprobante_para_mail")
    def test_get_ok(self, mock_fn):
        mock_fn.return_value = {
            "comprobante": {"codigomovimiento": 123},
            "token": "abc",
            "redirect_path": "fin-comprobante.php?p=abc",
        }
        req = _req_get(
            "/ecom/api/mayoristapp/comprobantes/comprobante-a-mail/",
            {"codMov": "123", "tipocomprobante": "1"},
            {"base_empresa": "emp1"},
        )
        req.session["mayoristapp"] = {"idcliente": 5}
        req.session.save()
        force_authenticate(req, user=self._user())
        resp = ComprobanteAMailRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["token"], "abc")

    def test_get_parametros_invalidos_400(self):
        req = _req_get(
            "/ecom/api/mayoristapp/comprobantes/comprobante-a-mail/",
            {"codMov": "x"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = ComprobanteAMailRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 400)


class TestComprobanteAMailEnqueueView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.comprobantes_relay_views.encolar_comprobante_mail")
    def test_post_ok(self, mock_fn):
        item = MagicMock()
        item.id = 77
        item.status = "pending"
        mock_fn.return_value = item
        req = _req_post(
            "/ecom/api/mayoristapp/comprobantes/comprobante-a-mail/enqueue/?ajax=1",
            {"codMov": 123, "tipocomprobante": 1, "email": "cliente@test.local"},
            {"base_empresa": "emp1"},
        )
        req.session["mayoristapp"] = {"idcliente": 5}
        req.session.save()
        force_authenticate(req, user=self._user())
        resp = ComprobanteAMailEnqueueRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 202)
        self.assertEqual(resp.data["msg"], "ok")


class TestComprobanteAMailQueueStatusView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.comprobantes_relay_views.EcomMailQueue")
    def test_get_ok(self, mock_model):
        item = MagicMock()
        item.id = 7
        item.status = "pending"
        item.attempts = 1
        item.last_error = ""
        item.to_email = "cliente@test.local"
        item.subject = "Comprobante"
        mock_model.objects.filter.return_value.first.return_value = item
        req = _req_get(
            "/ecom/api/mayoristapp/comprobantes/comprobante-a-mail/queue-status/",
            {"ajax": "1", "queue_id": "7"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = ComprobanteAMailQueueStatusRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["queue_id"], 7)


class TestComprobantesNoCanceladosView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.comprobantes_relay_views.listar_no_cancelados_relay")
    def test_post_ok(self, mock_fn):
        mock_fn.return_value = {"filas": [{"TipoComprobante": "FA"}], "saldo_al_dia": 10}
        req = _req_post(
            "/ecom/api/mayoristapp/comprobantes/no-cancelados/?ajax=1",
            {},
            {"base_empresa": "emp1"},
        )
        req.session["mayoristapp"] = {"idcliente": 5}
        req.session.save()
        force_authenticate(req, user=self._user())
        resp = ComprobantesNoCanceladosRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["total"], 1)

    @patch("ecom.comprobantes_relay_views.listar_no_cancelados_resumen_relay")
    def test_post_resumen_ok(self, mock_fn):
        mock_fn.return_value = {"filas": [{"TipoComprobante": "FA"}], "saldo_al_dia": 10}
        req = _req_post(
            "/ecom/api/mayoristapp/comprobantes/no-cancelados-resumen/?ajax=1",
            {},
            {"base_empresa": "emp1"},
        )
        req.session["mayoristapp"] = {"idcliente": 5}
        req.session.save()
        force_authenticate(req, user=self._user())
        resp = ComprobantesNoCanceladosResumenRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["total"], 1)


class TestComprobantesAnularPedidoView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.comprobantes_relay_views.anular_pedido_relay")
    def test_post_ok(self, mock_fn):
        mock_fn.return_value = {"msg": "ok", "error": ""}
        req = _req_post(
            "/ecom/api/mayoristapp/comprobantes/anular-pedido/?ajax=1",
            {"anularPedido": 1, "codMovPedido": 123},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = ComprobantesAnularPedidoRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["msg"], "ok")

    @patch("ecom.comprobantes_relay_views.anular_pedido_relay")
    def test_post_error(self, mock_fn):
        mock_fn.return_value = {"msg": "error", "error": "fallo"}
        req = _req_post(
            "/ecom/api/mayoristapp/comprobantes/anular-pedido/?ajax=1",
            {"anularPedido": 1, "codMovPedido": "x"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = ComprobantesAnularPedidoRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 400)
