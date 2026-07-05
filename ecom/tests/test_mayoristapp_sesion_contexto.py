# Tests contexto sesión mayoristapp (paridad control.php).

import unittest
from unittest.mock import MagicMock, patch

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory

from ecom.services.mayoristapp_sesion_contexto import contexto_usuario_mayoristapp


def _request_con_sesion(user: dict, extra: dict | None = None):
    factory = RequestFactory()
    req = factory.get("/")
    middleware = SessionMiddleware(lambda r: HttpResponse())
    middleware.process_request(req)
    req.session["user"] = user
    if extra:
        for k, v in extra.items():
            req.session[k] = v
    req.session.save()
    return req


class TestMayoristappSesionContexto(unittest.TestCase):
    @patch("ecom.services.mayoristapp_sesion_contexto._cargar_campos_mayoristapp_mysql")
    def test_hidrata_desde_mysql(self, mock_load):
        mock_load.return_value = {
            "id_vendedor_usr": 7,
            "todos_clientes": "Si",
            "supervisor_venta": "No",
        }
        req = _request_con_sesion(
            {"id_usuario": 10, "id_puesto": 2, "base_empresa": "emp1", "cod_usuario": "vend1"}
        )
        ctx = contexto_usuario_mayoristapp(req, persistir=True)
        self.assertEqual(ctx["id_vendedor_usr"], 7)
        self.assertEqual(ctx["todos_clientes"], "Si")
        self.assertEqual(req.session["user"]["id_vendedor_usr"], 7)
        self.assertEqual(req.session["todos_clientes"], "Si")

    def test_fusiona_raiz_php(self):
        req = _request_con_sesion(
            {"base_empresa": "emp1"},
            {"usa_id_manual": "Si", "todos_clientes": "Si"},
        )
        ctx = contexto_usuario_mayoristapp(req, persistir=False)
        self.assertEqual(ctx["usa_id_manual"], "Si")
        self.assertEqual(ctx["todos_clientes"], "Si")

    @patch("ecom.services.mayoristapp_sesion_contexto._cargar_campos_mayoristapp_mysql")
    def test_sobrescribe_sesion_stale_con_mysql(self, mock_load):
        mock_load.return_value = {
            "id_vendedor_usr": 2,
            "todos_clientes": "Si",
            "supervisor_venta": "Si",
        }
        req = _request_con_sesion(
            {
                "id_usuario": 1,
                "id_puesto": 1,
                "base_empresa": "administranet92",
                "cod_usuario": "vend1",
                "id_vendedor_usr": None,
                "todos_clientes": "No",
            },
            {"todos_clientes": "No"},
        )
        ctx = contexto_usuario_mayoristapp(req, persistir=False)
        self.assertEqual(ctx["id_vendedor_usr"], 2)
        self.assertEqual(ctx["todos_clientes"], "Si")

    @patch("ecom.services.mayoristapp_sesion_contexto._cargar_campos_mayoristapp_mysql")
    def test_supervisor_cod_usuario_todos_clientes(self, mock_load):
        mock_load.return_value = {"id_vendedor_usr": 1}
        req = _request_con_sesion(
            {"id_usuario": 1, "base_empresa": "emp1", "cod_usuario": "supervisor"}
        )
        ctx = contexto_usuario_mayoristapp(req, persistir=False)
        self.assertEqual(ctx["todos_clientes"], "Si")
