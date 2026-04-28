# Tests APIs recibos mayoristapp.

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.django_db

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.recibos_relay_views import RecibosListadoRelayAPIView


def _req_post(path: str, body: dict, session_user: dict):
    factory = APIRequestFactory()
    req = factory.post(path, body, format="json")
    middleware = SessionMiddleware(lambda r: HttpResponse())
    middleware.process_request(req)
    req.session["user"] = session_user
    req.session.save()
    return req


class TestRecibosListadoView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.recibos_relay_views.listar_recibos_relay")
    def test_post_ok(self, mock_listar):
        mock_listar.return_value = ([{"NroComprobante": "1"}], None)
        req = _req_post(
            "/ecom/api/mayoristapp/recibos/listado/?ajax=1&consulta=1",
            {"campoBusca": "-"},
            {"base_empresa": "emp1", "id_usuario": 5},
        )
        force_authenticate(req, user=self._user())
        resp = RecibosListadoRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["total"], 1)

    def test_sin_consulta_400(self):
        req = _req_post(
            "/ecom/api/mayoristapp/recibos/listado/?ajax=1",
            {},
            {"base_empresa": "emp1", "id_usuario": 5},
        )
        force_authenticate(req, user=self._user())
        resp = RecibosListadoRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 400)

    @patch("ecom.recibos_relay_views.listar_recibos_relay")
    def test_sin_id_usuario_400(self, mock_listar):
        mock_listar.return_value = (None, "Se requiere id_usuario en la sesión para el listado de recibos.")
        req = _req_post(
            "/ecom/api/mayoristapp/recibos/listado/?ajax=1&consulta=1",
            {},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = RecibosListadoRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 400)
