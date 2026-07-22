"""Tests promoción en línea, PDF, permisos y stepper de pedido."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.pedido_gestion_views import CompraMayoristaContextoAPIView, PedidoComprobantePDFAPIView
from ecom.services.comprobantes_relay import _where_pedidos
from ecom.services.pedido_cabecera_relay import stepper_estados_pedido
from ecom.services.pedido_permisos import puede_ver_todos_pedidos
from ecom.services.promocion_etiqueta import etiqueta_promocion_linea


def _session_user():
    return {"id_usuario": 1, "base_empresa": "test_base", "tipousuario": "vendedor"}


def _req_get(path: str, session_extra: dict | None = None):
    factory = APIRequestFactory()
    req = factory.get(path)
    middleware = SessionMiddleware(lambda r: HttpResponse())
    middleware.process_request(req)
    req.session["user"] = _session_user()
    if session_extra:
        for k, v in session_extra.items():
            req.session[k] = v
    req.session.save()
    force_authenticate(req, user=MagicMock(is_authenticated=True, id=1))
    return req


class TestPromocionEtiqueta(TestCase):
    def test_etiqueta_importe_descuento(self):
        txt = etiqueta_promocion_linea(
            {"promocion": "Si", "promocion_tipo": "Importe descuento", "promocion_por": 15}
        )
        self.assertIn("15%", txt)

    def test_sin_promo_vacia(self):
        self.assertEqual(etiqueta_promocion_linea({"promocion": "No"}), "")


class TestPedidoPDFView(TestCase):
    @patch("ecom.pedido_gestion_views.cabecera_pedido_relay")
    @patch("ecom.pedido_gestion_views.generar_pedido_pdf")
    def test_pdf_ok(self, mock_pdf, mock_cab):
        mock_pdf.return_value = (True, None, b"%PDF-fake")
        mock_cab.return_value = {"nro_comprobante": "0001-00001234"}
        req = _req_get("/ecom/api/mayoristapp/comprobantes/pedidos/5/pdf/")
        resp = PedidoComprobantePDFAPIView.as_view()(req, cod_mov=5)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")


class TestCompraContextoAPI(TestCase):
    @patch("ecom.pedido_gestion_views.listar_puntos_venta_usuario")
    @patch("ecom.pedido_gestion_views.leer_cliente_seleccionado")
    def test_contexto_pv_y_cliente(self, mock_cli, mock_pv):
        mock_pv.return_value = [{"id_punto_venta": 3, "label": "0003"}]
        mock_cli.return_value = {"Codigo": 10, "nombre_cliente": "ACME"}
        req = _req_get(
            "/ecom/api/mayoristapp/compra/contexto/",
            session_extra={"mayoristapp": {"idcliente": 10}},
        )
        resp = CompraMayoristaContextoAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["id_punto_venta_default"], 3)
        self.assertEqual(resp.data["idcliente"], 10)


class TestStepperEstados(TestCase):
    def test_preparado_marca_completados(self):
        pasos = stepper_estados_pedido("Preparado")
        activos = [p for p in pasos if p.get("activo")]
        self.assertEqual(len(activos), 1)
        self.assertEqual(activos[0]["clave"], "preparado")
        pend = next(p for p in pasos if p["clave"] == "pendiente")
        self.assertTrue(pend.get("completado"))


class TestPedidoPermisos(TestCase):
    def test_todos_clientes_permite_ver_todos(self):
        self.assertTrue(puede_ver_todos_pedidos({"todos_clientes": "Si"}))

    def test_vendedor_normal_no_ver_todos(self):
        self.assertFalse(puede_ver_todos_pedidos({"todos_clientes": "No", "id_vendedor_usr": 1}))

    def test_puesto_supervisor_ve_todos(self):
        from ecom.services.pedido_permisos import puesto_ve_todos_pedidos

        self.assertTrue(puede_ver_todos_pedidos({"nombre_puesto": "Supervisor", "todos_clientes": "No"}))
        self.assertTrue(puesto_ve_todos_pedidos({"nombre_puesto": "Supervisor venta"}))
        self.assertTrue(puesto_ve_todos_pedidos({"nombre_puesto": "Administración"}))
        self.assertTrue(puesto_ve_todos_pedidos({"nombre_puesto": "Administracion"}))
        self.assertFalse(puesto_ve_todos_pedidos({"nombre_puesto": "Vendedor"}))

    def test_where_pedidos_sin_filtro_viajante_si_supervisor(self):
        sql, params = _where_pedidos(
            {"vendedor": "true", "filtraVendedor": "todos"},
            {"todos_clientes": "Si"},
            None,
        )
        self.assertEqual(sql, "")
        self.assertEqual(params, [])
