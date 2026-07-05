# Tests APIs facturas imputar mayoristapp.

import unittest
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.facturas_imputar_relay_views import (
    FacturasImputarAccionRelayAPIView,
    FacturasImputarListadoRelayAPIView,
    FacturasImputarSugerenciasNroRelayAPIView,
)

pytestmark = pytest.mark.django_db


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


class TestFacturasImputarListadoView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.facturas_imputar_relay_views.listar_facturas_imputar_relay")
    def test_post_ok(self, mock_listar):
        mock_listar.return_value = [{"CodigoMovimiento": 1}]
        req = _req_post(
            "/ecom/api/mayoristapp/fe/facturas-imputar/listado/?ajax=1",
            {"campoBusca": ""},
            {"base_empresa": "emp1"},
            session_extra={"mayoristapp": {"idcliente": 5}},
        )
        force_authenticate(req, user=self._user())
        resp = FacturasImputarListadoRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["total"], 1)

    def test_post_sin_idcliente_400(self):
        req = _req_post(
            "/ecom/api/mayoristapp/fe/facturas-imputar/listado/?ajax=1",
            {},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = FacturasImputarListadoRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 400)


class TestFacturasImputarSugerenciasView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.facturas_imputar_relay_views.sugerencias_nro_facturas_imputar_relay")
    def test_get_ok(self, mock_s):
        mock_s.return_value = ["100", "1001"]
        req = _req_get(
            "/ecom/api/mayoristapp/fe/facturas-imputar/sugerencias-nro/",
            {"ajax": "1", "q": "10"},
            {"base_empresa": "emp1"},
            session_extra={"mayoristapp": {"idcliente": 5}},
        )
        force_authenticate(req, user=self._user())
        resp = FacturasImputarSugerenciasNroRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["sugerencias"]), 2)


class TestFacturasImputarAccionView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.facturas_imputar_relay_views.ecom_imputacion_write_enabled", return_value=False)
    def test_accion_bloqueada_por_plan(self, _mock):
        req = _req_post(
            "/ecom/api/mayoristapp/fe/facturas-imputar/accion/?ajax=1",
            {
                "imputarFactura": 1,
                "idrecibofactura": 10,
                "codmodfact": 222,
                "fecha": "2026-03-31",
                "nrofactura": "0001-00001234",
                "importe": "1000.00",
                "cancelado": "100.00",
                "saldo": "900.00",
                "aimputar": "200.00",
                "tipocomprobante": "FA",
            },
            {"base_empresa": "emp1"},
            session_extra={"mayoristapp": {"idcliente": 5}},
        )
        force_authenticate(req, user=self._user())
        resp = FacturasImputarAccionRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 409)
