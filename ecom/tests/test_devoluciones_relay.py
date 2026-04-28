import unittest
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.devoluciones_relay_views import (
    DevolucionesRelayAPIView,
    DevolucionesSugerenciasNroRelayAPIView,
)

pytestmark = pytest.mark.django_db


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


class TestDevolucionesRelayView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.devoluciones_relay_views.listado_filtros_estadisticas")
    def test_post_seleccion_ok(self, mock_fn):
        mock_fn.return_value = [{"label": "C1", "value": "1|C1"}]
        req = _req_post(
            "/ecom/api/mayoristapp/estadisticas/devoluciones/?ajax=1",
            {"queAccion": "seleccion", "tabla": "cliente"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = DevolucionesRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["total"], 1)

    @patch("ecom.devoluciones_relay_views.listar_devoluciones_relay")
    def test_post_listar_ok(self, mock_fn):
        mock_fn.return_value = [{"CodigoMovimiento": 10}]
        req = _req_post(
            "/ecom/api/mayoristapp/estadisticas/devoluciones/?ajax=1",
            {"queAccion": "listar", "campoBusca": "1"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = DevolucionesRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["total"], 1)

    def test_post_procesar_bloqueado(self):
        req = _req_post(
            "/ecom/api/mayoristapp/estadisticas/devoluciones/?ajax=1",
            {"queAccion": "procesar"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = DevolucionesRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 409)


class TestDevolucionesSugerenciasRelayView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.devoluciones_relay_views.sugerencias_nro_devoluciones_relay")
    def test_get_ok(self, mock_fn):
        mock_fn.return_value = ["DEV0001"]
        req = _req_get(
            "/ecom/api/mayoristapp/estadisticas/devoluciones/sugerencias-nro/",
            {"ajax": "1", "q": "DEV"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = DevolucionesSugerenciasNroRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["total"], 1)

