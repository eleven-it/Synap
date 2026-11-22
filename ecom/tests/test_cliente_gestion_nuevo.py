"""Gestión de clientes desde el puesto vendedor."""

from unittest.mock import patch

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.cliente_relay_views import ClienteRapidoRelayAPIView
from ecom.services.cliente_rapido_escritura import alta_cliente_rapido, edita_cliente_rapido


class _Vendedor:
    is_authenticated = True
    is_superuser = False

    def __init__(self, permisos):
        self.permisos = permisos

    def tiene_permiso(self, codigo):
        return codigo in self.permisos


def _request(data, permisos, tipo="Vendedor"):
    req = APIRequestFactory().post(
        "/ecom/api/mayoristapp/clientes/rapido/?ajax=1", data, format="json"
    )
    SessionMiddleware(lambda _: HttpResponse()).process_request(req)
    req.session["user"] = {"base_empresa": "bestsox", "tipousuario": tipo, "id_vendedor_usr": 7}
    force_authenticate(req, user=_Vendedor(permisos))
    return req


class ClienteGestionNuevoTests(SimpleTestCase):
    def test_alta_rechaza_usuario_sin_permiso(self):
        with patch("ecom.cliente_relay_views._session_user", return_value={"tipousuario": "Vendedor"}):
            response = ClienteRapidoRelayAPIView.as_view()(
                _request({"accion": "altaCliente", "nombreCliente": "Nuevo"}, set())
            )
        self.assertEqual(response.status_code, 403)

    def test_alta_rechaza_datos_incompletos_antes_de_escribir(self):
        with patch("ecom.cliente_relay_views._session_user", return_value={"tipousuario": "Vendedor"}), patch("ecom.cliente_relay_views.alta_cliente_rapido") as alta:
            response = ClienteRapidoRelayAPIView.as_view()(
                _request({"accion": "altaCliente", "nombreCliente": "Nuevo"}, {"clientes.crear"})
            )
        self.assertEqual(response.status_code, 400)
        alta.assert_not_called()

    def test_edicion_rechaza_cliente_fuera_de_cartera(self):
        with patch("ecom.cliente_relay_views._session_user", return_value={"tipousuario": "Vendedor"}), patch("ecom.cliente_relay_views.cliente_accesible_por_sesion", return_value=False):
            response = ClienteRapidoRelayAPIView.as_view()(
                _request({"accion": "editaCliente", "codCliente": 12, "telefonoCliente": "123"}, {"clientes.editar"})
            )
        self.assertEqual(response.status_code, 403)

    def test_edicion_parcial_no_pisa_documentos_ni_geografia(self):
        class Cursor:
            sql = ""
            params = []
            def execute(self, sql, params):
                self.sql, self.params = sql, params

        class Conn:
            cursor_obj = Cursor()
            def __enter__(self): return self
            def __exit__(self, *_args): return None
            def cursor(self): return self.cursor_obj

        class Pool:
            def get_connection(self, _base): return Conn()

        with patch("ecom.services.cliente_rapido_escritura.get_mysql_pool", return_value=Pool()):
            result = edita_cliente_rapido("bestsox", {"codCliente": 12, "telefonoCliente": "123"}, {})
        self.assertEqual(result, 12)
        self.assertEqual(Conn.cursor_obj.sql, "UPDATE cliente SET telefono = %s WHERE cliente.Codigo = %s")
        self.assertEqual(Conn.cursor_obj.params, ["123", 12])

    def test_alta_guarda_transporte_y_domicilio_en_una_transaccion(self):
        class Cursor:
            lastrowid = 42
            sql = ""
            calls = []
            def execute(self, sql, params):
                self.sql = sql
                self.calls.append((sql, params))
            def fetchone(self): return (1,)

        class Conn:
            cursor_obj = Cursor()
            committed = False
            def __enter__(self): return self
            def __exit__(self, *_args): return None
            def cursor(self): return self.cursor_obj
            def autocommit(self, _value): pass
            def commit(self): self.committed = True
            def rollback(self): self.committed = False

        class Pool:
            def get_connection(self, _base): return connection

        connection = Conn()
        with patch("ecom.services.cliente_rapido_escritura.valida_cliente_existe", return_value=[]), patch(
            "ecom.services.cliente_rapido_escritura.trae_cuenta_contable_defecto", return_value=13
        ), patch("ecom.services.cliente_rapido_escritura.get_mysql_pool", return_value=Pool()):
            result = alta_cliente_rapido("bestsox", {
                "nombreCliente": "Nuevo", "tipoDocCliente": "CUIT", "nroCuitCliente": "30-12345678-9",
                "calleCliente": "San Juan", "numeroCliente": "123", "idTransporte": 5,
            }, {"id_vendedor_usr": 7})
        self.assertEqual(result, 42)
        self.assertTrue(connection.committed)
        domicilio = next(params for sql, params in connection.cursor_obj.calls if "INSERT INTO cliente_domicilio" in sql)
        self.assertEqual(domicilio[-1], 5)
