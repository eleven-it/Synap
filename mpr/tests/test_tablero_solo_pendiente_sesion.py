"""Persistencia en sesión de toggles del tablero de producción."""

from django.test import RequestFactory, TestCase

from mpr.presentacion_operativa import resolver_modo_presentacion_operativa
from mpr.views import (
    _TABLERO_SESSION_MODO,
    _TABLERO_SESSION_SOLO_SIN_RECETA,
    _TABLERO_SESSION_SOLO_URGENTE,
    _redirect_tablero_produccion,
    _resolver_modo_tablero,
    _resolver_solo_sin_receta_tablero,
    _resolver_solo_urgente_tablero,
    _resolver_solo_pendiente_tablero,
)


class TestSoloUrgenteSesion(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _request(self, query=None):
        request = self.factory.get("/mpr/tablero-produccion/", query or {})
        request.session = self.client.session
        return request

    def test_default_true_sin_sesion_ni_query(self):
        self.assertTrue(_resolver_solo_urgente_tablero(self._request()))

    def test_query_false_persiste_en_sesion(self):
        request = self._request({"solo_urgente": "0"})
        self.assertFalse(_resolver_solo_urgente_tablero(request))
        request.session.save()
        self.assertFalse(_resolver_solo_urgente_tablero(self._request()))

    def test_solo_pendiente_legacy_query(self):
        request = self._request({"solo_pendiente": "0"})
        self.assertFalse(_resolver_solo_pendiente_tablero(request))

    def test_query_true_persiste_en_sesion(self):
        request = self._request({"solo_urgente": "1"})
        self.assertTrue(_resolver_solo_urgente_tablero(request))
        request.session.save()
        self.assertTrue(request.session.get(_TABLERO_SESSION_SOLO_URGENTE))

    def test_redirect_incluye_solo_urgente_desde_sesion(self):
        request = self._request({"solo_urgente": "0"})
        _resolver_solo_urgente_tablero(request)
        response = _redirect_tablero_produccion(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn("solo_urgente=0", response.url)


class TestSoloSinRecetaSesion(TestCase):
    """Persistencia en sesión del filtro Sin receta (modo Pack)."""

    def setUp(self):
        self.factory = RequestFactory()

    def _request(self, query=None):
        request = self.factory.get("/mpr/tablero-produccion/", query or {})
        request.session = self.client.session
        return request

    def test_default_false_sin_sesion_ni_query(self):
        self.assertFalse(_resolver_solo_sin_receta_tablero(self._request()))

    def test_query_true_persiste_en_sesion(self):
        request = self._request({"solo_sin_receta": "1"})
        self.assertTrue(_resolver_solo_sin_receta_tablero(request))
        request.session.save()
        self.assertTrue(request.session.get(_TABLERO_SESSION_SOLO_SIN_RECETA))
        self.assertTrue(_resolver_solo_sin_receta_tablero(self._request()))

    def test_query_false_persiste_en_sesion(self):
        request = self._request({"solo_sin_receta": "0"})
        self.assertFalse(_resolver_solo_sin_receta_tablero(request))
        request.session.save()
        self.assertFalse(_resolver_solo_sin_receta_tablero(self._request()))

    def test_redirect_incluye_solo_sin_receta_desde_sesion(self):
        request = self._request({"solo_sin_receta": "1"})
        _resolver_solo_sin_receta_tablero(request)
        response = _redirect_tablero_produccion(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn("solo_sin_receta=1", response.url)


class TestModoTableroSesion(TestCase):
    """Persistencia Pack|Par y reinyección de presentacion en redirect."""

    def setUp(self):
        self.factory = RequestFactory()

    def _request(self, query=None):
        request = self.factory.get("/mpr/tablero-produccion/", query or {})
        request.session = self.client.session
        return request

    def test_default_par_sin_sesion_ni_query(self):
        self.assertEqual(_resolver_modo_tablero(self._request()), "par")

    def test_query_pack_persiste_en_sesion(self):
        request = self._request({"modo": "pack"})
        self.assertEqual(_resolver_modo_tablero(request), "pack")
        request.session.save()
        self.assertEqual(request.session.get(_TABLERO_SESSION_MODO), "pack")
        self.assertEqual(_resolver_modo_tablero(self._request()), "pack")

    def test_query_par_sobrescribe_sesion_pack(self):
        request = self._request({"modo": "pack"})
        _resolver_modo_tablero(request)
        request.session.save()
        request2 = self._request({"modo": "par"})
        request2.session = request.session
        self.assertEqual(_resolver_modo_tablero(request2), "par")
        self.assertEqual(request2.session.get(_TABLERO_SESSION_MODO), "par")

    def test_modo_invalido_usa_sesion_o_default(self):
        request = self._request({"modo": "pack"})
        _resolver_modo_tablero(request)
        request.session.save()
        request2 = self._request({"modo": "xyz"})
        request2.session = request.session
        self.assertEqual(_resolver_modo_tablero(request2), "pack")

    def test_redirect_incluye_modo_y_presentacion_desde_sesion(self):
        request = self._request({"modo": "pack", "presentacion": "unidades"})
        _resolver_modo_tablero(request)
        resolver_modo_presentacion_operativa(request)
        response = _redirect_tablero_produccion(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn("modo=pack", response.url)
        self.assertIn("presentacion=unidades", response.url)
        self.assertIn("solo_urgente=", response.url)
        self.assertIn("solo_sin_receta=", response.url)


class TestBusquedaArticuloRedirect(TestCase):
    """La búsqueda Alpine (?q=) se reinyecta en el redirect post-Actualizar."""

    def setUp(self):
        self.factory = RequestFactory()

    def _request(self, query=None):
        request = self.factory.get("/mpr/tablero-produccion/", query or {})
        request.session = self.client.session
        return request

    def test_redirect_incluye_q_desde_query_string(self):
        request = self._request()
        response = _redirect_tablero_produccion(request, "q=6245+T5+Puma")
        self.assertEqual(response.status_code, 302)
        self.assertIn("q=6245", response.url)
        self.assertIn("T5", response.url)

    def test_redirect_omite_q_vacio(self):
        request = self._request()
        response = _redirect_tablero_produccion(request, "q=")
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("q=", response.url)
