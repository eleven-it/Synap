# Tests relays clientes mayoristapp.

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.django_db

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.cliente_relay_views import (
    ClienteBuscarRelayAPIView,
    ClienteComprobanteFormularioRelayAPIView,
    ClienteContactoRelayAPIView,
    ClienteDomicilioOpcionesVisitaRelayAPIView,
    ClienteDomicilioRelayAPIView,
    ClienteRapidoRelayAPIView,
    ClienteSeleccionadoRelayAPIView,
    ClienteSeleccionarRelayAPIView,
)


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


def _req_post(path: str, body: dict, session_user: dict):
    factory = APIRequestFactory()
    req = factory.post(path, body, format="json")
    middleware = SessionMiddleware(lambda r: HttpResponse())
    middleware.process_request(req)
    req.session["user"] = session_user
    req.session.save()
    return req


class TestClienteBuscarRelayView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    def test_get_sin_ajax_400(self):
        req = _req_get(
            "/ecom/api/mayoristapp/clientes/buscar/",
            {"modoBus": "texto", "patron": "x"},
            {"base_empresa": "emp1", "id_vendedor_usr": 1, "todos_clientes": "Si"},
        )
        force_authenticate(req, user=self._user())
        resp = ClienteBuscarRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 400)

    @patch("ecom.cliente_relay_views.buscar_clientes_relay")
    def test_get_ok(self, mock_buscar):
        mock_buscar.return_value = ([{"codigo": 2, "nombre_cliente": "Uno"}], None)
        req = _req_get(
            "/ecom/api/mayoristapp/clientes/buscar/",
            {"ajax": "1", "modoBus": "texto", "patron": "pepe"},
            {"base_empresa": "emp1", "id_vendedor_usr": 1, "todos_clientes": "Si"},
        )
        force_authenticate(req, user=self._user())
        resp = ClienteBuscarRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["clientes"]), 1)
        self.assertEqual(len(resp.data["results"]), 1)
        self.assertEqual(resp.data["results"][0]["id"], 2)

    @patch("ecom.cliente_relay_views.buscar_clientes_relay")
    def test_get_q_alias(self, mock_buscar):
        mock_buscar.return_value = ([{"codigo": 9, "nombre_cliente": "Beta"}], None)
        req = _req_get(
            "/ecom/api/mayoristapp/clientes/buscar/",
            {"ajax": "1", "q": "bet"},
            {"base_empresa": "emp1", "id_vendedor_usr": 1, "todos_clientes": "Si"},
        )
        force_authenticate(req, user=self._user())
        resp = ClienteBuscarRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        mock_buscar.assert_called_once()
        self.assertEqual(mock_buscar.call_args.kwargs["patron_texto"], "bet")
        self.assertEqual(mock_buscar.call_args.kwargs["modo_busqueda"], "texto")
        self.assertEqual(resp.data["results"][0]["text"], "Beta")

    @patch("ecom.cliente_relay_views.buscar_clientes_relay")
    def test_post_ok(self, mock_buscar):
        mock_buscar.return_value = ([], None)
        req = _req_post(
            "/ecom/api/mayoristapp/clientes/buscar/",
            {
                "buscarCliente": "1",
                "claseBusqueda": "codigo",
                "codigo": "99",
            },
            {"base_empresa": "emp1", "id_vendedor_usr": 1, "todos_clientes": "Si"},
        )
        force_authenticate(req, user=self._user())
        resp = ClienteBuscarRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)


class TestClienteSeleccionadoRelayView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.cliente_relay_views.leer_cliente_seleccionado")
    def test_ok(self, mock_leer):
        mock_leer.return_value = {"Codigo": 5}
        req = _req_get(
            "/ecom/api/mayoristapp/clientes/seleccionado/",
            {"ajax": "1"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = ClienteSeleccionadoRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("Codigo"), 5)


class TestClienteComprobanteFormularioRelayView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.cliente_relay_views.guardar_formulario_comprobante_mayoristapp")
    def test_ok(self, mock_g):
        req = _req_get(
            "/ecom/api/mayoristapp/clientes/comprobante-formulario/",
            {"ajax": "1", "frm": "0"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = ClienteComprobanteFormularioRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("estado"), "ok")
        mock_g.assert_called_once()


class TestClienteRelayServicio(unittest.TestCase):
    def test_where_viajante_todos(self):
        from ecom.services.cliente_relay import _where_viajante

        sql, p = _where_viajante({"todos_clientes": "Si"})
        self.assertEqual(sql, "")
        self.assertEqual(p, [])


class TestClienteSeleccionarRelayView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.cliente_relay_views.cliente_accesible_por_sesion", return_value=True)
    @patch("ecom.cliente_relay_views.construir_payload_cliente_seleccionado")
    @patch("ecom.cliente_relay_views.guardar_cliente_seleccion_mayoristapp")
    def test_post_ok(self, mock_guardar, mock_payload, _acc):
        mock_payload.return_value = ({"Codigo": 3}, {}, [], "si")
        factory = APIRequestFactory()
        req = factory.post(
            "/ecom/api/mayoristapp/clientes/seleccionar/?ajax=1",
            {"codigo": "3"},
            format="json",
        )
        middleware = SessionMiddleware(lambda r: HttpResponse())
        middleware.process_request(req)
        req.session["user"] = {"base_empresa": "emp1", "id_vendedor_usr": 1}
        req.session.save()
        force_authenticate(req, user=self._user())
        resp = ClienteSeleccionarRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("estado"), "ok")
        mock_guardar.assert_called_once()


class TestClienteDomicilioRelayView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.cliente_relay_views.cliente_accesible_por_sesion", return_value=True)
    @patch("ecom.cliente_relay_views.id_cliente_de_domicilio", return_value=10)
    @patch("ecom.cliente_relay_views.trae_domicilio_completo")
    @patch("ecom.cliente_relay_views.list_provincias")
    @patch("ecom.cliente_relay_views.list_departamentos")
    @patch("ecom.cliente_relay_views.list_distritos")
    @patch("ecom.cliente_relay_views.list_zonas_erp")
    def test_get_traer(
        self, _z, _d, _dep, _p, mock_trae, _id_dom, _acc
    ):
        mock_trae.return_value = ({"id_cliente_domicilio": 1, "CodProvincia": 2, "IDDepartamento": 3}, None)
        req = _req_get(
            "/ecom/api/mayoristapp/clientes/domicilio/",
            {"ajax": "1", "accion": "traer", "idDomicilio": "99"},
            {"base_empresa": "emp1", "todos_clientes": "Si"},
        )
        force_authenticate(req, user=self._user())
        resp = ClienteDomicilioRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("dom", resp.data)


class TestClienteDomicilioVisitaRelayView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    def test_get(self):
        req = _req_get(
            "/ecom/api/mayoristapp/clientes/domicilio-opciones-visita/",
            {"traeVisita": "1", "tipoVisita": "Semanal"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = ClienteDomicilioOpcionesVisitaRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("opc", resp.data)


class TestClienteContactoRelayView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.cliente_relay_views.leer_idcliente_mayoristapp", return_value=5)
    @patch("ecom.cliente_relay_views.lista_contactos_cliente")
    @patch("ecom.cliente_relay_views.cliente_accesible_por_sesion", return_value=True)
    def test_get_lista(self, _mock_acc, mock_lista, _mock_leer):
        mock_lista.return_value = []
        req = _req_get(
            "/ecom/api/mayoristapp/clientes/contacto/",
            {"ajax": "1", "accion": "lista"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = ClienteContactoRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("total"), 0)


class TestClienteRapidoRelayView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.cliente_relay_views.inicio_payload")
    def test_inicio(self, mock_ini):
        mock_ini.return_value = {"tipoCliente": {}, "ivaCliente": {}, "provincia": {}}
        req = _req_get(
            "/ecom/api/mayoristapp/clientes/rapido/",
            {"ajax": "1", "accion": "inicio"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = ClienteRapidoRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)

    @patch("ecom.cliente_relay_views.guardar_cliente_rapido_lista_sesion")
    @patch("ecom.cliente_relay_views.actualizar_cliente_rapido_json", return_value="[]")
    @patch("ecom.cliente_relay_views.guardar_cliente_seleccion_mayoristapp")
    @patch("ecom.cliente_relay_views.construir_payload_cliente_seleccionado")
    @patch("ecom.cliente_relay_views.alta_cliente_rapido", return_value=42)
    def test_post_alta_ok(self, _alta, mock_payload, mock_guard_sel, _json, _lista):
        mock_payload.return_value = ({"Codigo": 42}, {}, [], "si")
        factory = APIRequestFactory()
        req = factory.post(
            "/ecom/api/mayoristapp/clientes/rapido/?ajax=1",
            {"accion": "altaCliente", "nombreCliente": "Nuevo"},
            format="json",
        )
        middleware = SessionMiddleware(lambda r: HttpResponse())
        middleware.process_request(req)
        req.session["user"] = {"base_empresa": "emp1", "id_vendedor_usr": 1}
        req.session.save()
        force_authenticate(req, user=self._user())
        resp = ClienteRapidoRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("codigo"), 42)
        self.assertEqual(resp.data.get("status"), "ok")

    @patch("ecom.cliente_relay_views.guardar_cliente_seleccion_mayoristapp")
    @patch("ecom.cliente_relay_views.construir_payload_cliente_seleccionado")
    @patch("ecom.cliente_relay_views.edita_cliente_rapido", return_value=7)
    @patch("ecom.cliente_relay_views.cliente_accesible_por_sesion", return_value=True)
    def test_post_edita_ok(self, _acc, _edita, mock_payload, mock_guard):
        mock_payload.return_value = ({"Codigo": 7}, {}, [], "si")
        factory = APIRequestFactory()
        req = factory.post(
            "/ecom/api/mayoristapp/clientes/rapido/?ajax=1",
            {"accion": "editaCliente", "codCliente": "7"},
            format="json",
        )
        middleware = SessionMiddleware(lambda r: HttpResponse())
        middleware.process_request(req)
        req.session["user"] = {"base_empresa": "emp1", "id_vendedor_usr": 1}
        req.session.save()
        force_authenticate(req, user=self._user())
        resp = ClienteRapidoRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("codigo"), 7)
