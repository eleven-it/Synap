# Tests APIs cuenta corriente mayoristapp.

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.django_db

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.ctacte_relay_views import (
    ConsumosResumenRelayAPIView,
    CuentaCorrientePedidosRelayAPIView,
    CuentaCorrientePedidosSugerenciasNroRelayAPIView,
    CtacteMovimientosRelayAPIView,
    CtacteSugerenciasNroRelayAPIView,
)


def _req_post(path: str, body: dict, session_user: dict, session_extra: dict | None = None):
    factory = APIRequestFactory()
    req = factory.post(path, body, format="json")
    middleware = SessionMiddleware(lambda r: HttpResponse())
    middleware.process_request(req)
    req.session["user"] = session_user
    if session_extra:
        for k, v in session_extra.items():
            req.session[k] = v
    req.session.save()
    return req


def _req_get(path: str, query: dict, session_user: dict, session_extra: dict | None = None):
    factory = RequestFactory()
    req = factory.get(path, query)
    middleware = SessionMiddleware(lambda r: HttpResponse())
    middleware.process_request(req)
    req.session["user"] = session_user
    if session_extra:
        for k, v in session_extra.items():
            req.session[k] = v
    req.session.save()
    return req


class TestCtacteMovimientosView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.ctacte_relay_views.cliente_accesible_por_sesion", return_value=True)
    @patch("ecom.ctacte_relay_views.listar_movimientos_ctacte_relay")
    def test_post_ok(self, mock_listar, _acc):
        mock_listar.return_value = [{"Debito": 100.0}]
        req = _req_post(
            "/ecom/api/mayoristapp/ctacte/movimientos/?ajax=1",
            {"campoBusca": "-"},
            {"base_empresa": "emp1", "todos_clientes": "Si"},
            session_extra={"mayoristapp": {"idcliente": 5}},
        )
        force_authenticate(req, user=self._user())
        resp = CtacteMovimientosRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["total"], 1)

    def test_sin_idcliente_400(self):
        req = _req_post(
            "/ecom/api/mayoristapp/ctacte/movimientos/?ajax=1",
            {},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = CtacteMovimientosRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 400)


class TestCtacteSugerenciasView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.ctacte_relay_views.cliente_accesible_por_sesion", return_value=True)
    @patch("ecom.ctacte_relay_views.sugerencias_nro_ctacte_relay")
    def test_get_ok(self, mock_s, _acc):
        mock_s.return_value = ["1", "12"]
        req = _req_get(
            "/ecom/api/mayoristapp/ctacte/sugerencias-nro/",
            {"ajax": "1", "q": "1"},
            {"base_empresa": "emp1", "todos_clientes": "Si"},
            session_extra={"mayoristapp": {"idcliente": 5}},
        )
        force_authenticate(req, user=self._user())
        resp = CtacteSugerenciasNroRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["total"], 2)


class TestCuentaCorrientePedidosView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.ctacte_relay_views.cliente_accesible_por_sesion", return_value=True)
    @patch("ecom.ctacte_relay_views.listar_pedidos_cuenta_corriente_relay")
    def test_post_pedidos_ok(self, mock_listar, _acc):
        mock_listar.return_value = [{"NroComprobante": "P-1"}]
        req = _req_post(
            "/ecom/api/mayoristapp/ctacte/pedidos/?ajax=1",
            {"campoBusca": "-"},
            {"base_empresa": "emp1", "todos_clientes": "Si"},
            session_extra={"mayoristapp": {"idcliente": 5}},
        )
        force_authenticate(req, user=self._user())
        resp = CuentaCorrientePedidosRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["total"], 1)


class TestCuentaCorrientePedidosSugerenciasView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.ctacte_relay_views.cliente_accesible_por_sesion", return_value=True)
    @patch("ecom.ctacte_relay_views.sugerencias_nro_pedido_cuenta_corriente_relay")
    def test_get_sugerencias_ok(self, mock_s, _acc):
        mock_s.return_value = ["10"]
        req = _req_get(
            "/ecom/api/mayoristapp/ctacte/pedidos/sugerencias-nro/",
            {"ajax": "1", "q": "1"},
            {"base_empresa": "emp1", "todos_clientes": "Si"},
            session_extra={"mayoristapp": {"idcliente": 5}},
        )
        force_authenticate(req, user=self._user())
        resp = CuentaCorrientePedidosSugerenciasNroRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["total"], 1)


class TestConsumosResumenView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.ctacte_relay_views.cliente_accesible_por_sesion", return_value=True)
    @patch("ecom.ctacte_relay_views.listar_consumos_resumen_relay")
    def test_post_consumos_ok(self, mock_listar, _acc):
        mock_listar.return_value = ([{"IDArt": 1, "Cuantos": 3.0}], "advertencia")
        req = _req_post(
            "/ecom/api/mayoristapp/ctacte/consumos-resumen/?ajax=1",
            {},
            {"base_empresa": "emp1", "todos_clientes": "Si"},
            session_extra={"mayoristapp": {"idcliente": 5}},
        )
        force_authenticate(req, user=self._user())
        resp = ConsumosResumenRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["total"], 1)
        self.assertEqual(resp.data["advertencia_precios"], "advertencia")
