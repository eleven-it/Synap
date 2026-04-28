import unittest
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory
from rest_framework.test import force_authenticate

from ecom.filtros_estadisticas_relay_views import FiltrosEstadisticasRelayAPIView

pytestmark = pytest.mark.django_db


def _req_get(path: str, query: dict, session_user: dict):
    factory = RequestFactory()
    req = factory.get(path, query)
    middleware = SessionMiddleware(lambda r: HttpResponse())
    middleware.process_request(req)
    req.session["user"] = session_user
    req.session.save()
    return req


class TestFiltrosEstadisticasRelayView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.filtros_estadisticas_relay_views.listado_filtros_estadisticas")
    def test_get_ok(self, mock_fn):
        mock_fn.return_value = [{"label": "Cliente A", "value": "1|Cliente A"}]
        req = _req_get(
            "/ecom/api/mayoristapp/estadisticas/filtros/",
            {"ajax": "1", "tabla": "cliente"},
            {"base_empresa": "emp1"},
        )
        req.session["usa_id_manual"] = "Si"
        req.session["vendedor_a_cargo"] = [1, 2]
        req.session.save()
        force_authenticate(req, user=self._user())
        resp = FiltrosEstadisticasRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["total"], 1)

    def test_get_sin_tabla_400(self):
        req = _req_get(
            "/ecom/api/mayoristapp/estadisticas/filtros/",
            {"ajax": "1"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = FiltrosEstadisticasRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 400)

