# Tests APIs nota de crédito mayoristapp.

import unittest
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.nota_credito_relay_views import (
    NotaCreditoListadoRelayAPIView,
    NotaCreditoSugerenciasNroRelayAPIView,
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


class TestNotaCreditoListadoView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.nota_credito_relay_views.listar_nota_credito_relay")
    def test_post_ok(self, mock_listar):
        mock_listar.return_value = [{"CodigoMovimiento": 1}]
        req = _req_post(
            "/ecom/api/mayoristapp/fe/nota-credito/listado/?ajax=1",
            {"campoBusca": "TipoPedido", "tipoFact": "-"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = NotaCreditoListadoRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["total"], 1)


class TestNotaCreditoSugerenciasView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.nota_credito_relay_views.sugerencias_nro_nota_credito_relay")
    def test_get_ok(self, mock_s):
        mock_s.return_value = ["100", "1001"]
        req = _req_get(
            "/ecom/api/mayoristapp/fe/nota-credito/sugerencias-nro/",
            {"ajax": "1", "q": "10"},
            {"base_empresa": "emp1", "tipousuario": "vendedor", "id_vendedor_usr": 1},
        )
        force_authenticate(req, user=self._user())
        resp = NotaCreditoSugerenciasNroRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["sugerencias"]), 2)
