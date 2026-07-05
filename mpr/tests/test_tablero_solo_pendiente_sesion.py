"""Persistencia en sesión del toggle Solo pendientes del tablero consolidado."""

from django.test import RequestFactory, TestCase

from mpr.views import (
    _TABLERO_SESSION_SOLO_PENDIENTE,
    _redirect_tablero_produccion,
    _resolver_solo_pendiente_tablero,
)


class TestSoloPendienteSesion(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _request(self, query=None):
        request = self.factory.get("/mpr/tablero-produccion/", query or {})
        request.session = self.client.session
        return request

    def test_default_true_sin_sesion_ni_query(self):
        self.assertTrue(_resolver_solo_pendiente_tablero(self._request()))

    def test_query_false_persiste_en_sesion(self):
        request = self._request({"solo_pendiente": "0"})
        self.assertFalse(_resolver_solo_pendiente_tablero(request))
        request.session.save()
        self.assertFalse(_resolver_solo_pendiente_tablero(self._request()))

    def test_query_true_persiste_en_sesion(self):
        request = self._request({"solo_pendiente": "1"})
        self.assertTrue(_resolver_solo_pendiente_tablero(request))
        request.session.save()
        self.assertTrue(_resolver_solo_pendiente_tablero(self._request()))

    def test_redirect_incluye_solo_pendiente_desde_sesion(self):
        request = self._request({"solo_pendiente": "0"})
        _resolver_solo_pendiente_tablero(request)
        response = _redirect_tablero_produccion(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn("solo_pendiente=0", response.url)
