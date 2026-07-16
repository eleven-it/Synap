# Tests E2E API checkout→pendiente→aprobar/rechazar y regresión master OFF (REQ-GLOB-01, REQ-APR-04).

from unittest.mock import MagicMock, patch

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.pedido_gestion_views import (
    AprobacionPedidoAprobarAPIView,
    AprobacionPedidoRechazarAPIView,
    AprobacionPendientesAPIView,
)
from ecom.services.mayorista_checkout_service import CheckoutInput
from ecom.services import mayorista_checkout_service as checkout_svc
from ecom.services.aprobacion_pedidos import ESTADO_PENDIENTE
from ecom.services.pedidos_hub_pipeline import construir_hub_pedidos
from ecom.tests.test_mayorista_checkout_service import FakeConn, TestCheckoutAprobacionComercial


def _session_user(cod=10, permisos=None):
    return {
        "id_usuario": 1,
        "base_empresa": "test_base",
        "CodViajante": cod,
        "synap_permisos": permisos or ["ecom.pedidos.aprobar", "ecom.pedidos.ver"],
    }


def _req(method, path, session_user=None, body=None):
    factory = APIRequestFactory()
    if method == "GET":
        req = factory.get(path)
    else:
        req = factory.post(path, body or {}, format="json")
    middleware = SessionMiddleware(lambda r: HttpResponse())
    middleware.process_request(req)
    req.session["user"] = session_user or _session_user()
    req.session.save()
    user = MagicMock(is_authenticated=True, id=1, is_superuser=False)
    force_authenticate(req, user=user)
    return req


class TestAprobacionFlujoAPI(TestCase):
    @patch("ecom.pedido_gestion_views.listar_pendientes_comerciales")
    def test_get_pendientes_ok(self, mock_listar):
        mock_listar.return_value = [
            {"CodigoMovimiento": 9001, "estado_aprobacion_comercial": ESTADO_PENDIENTE},
        ]
        req = _req("GET", "/ecom/api/mayoristapp/aprobacion/pendientes/")
        with patch("ecom.permissions._user_has_perm", return_value=True):
            resp = AprobacionPendientesAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["total"], 1)

    @patch("ecom.pedido_gestion_views.resolver")
    def test_post_aprobar_ok(self, mock_resolver):
        mock_resolver.return_value = (
            True,
            "Aprobado",
            {"estado_aprobacion_comercial": "aprobado"},
        )
        req = _req(
            "POST",
            "/ecom/api/mayoristapp/aprobacion/9001/aprobar/",
            body={"motivo": "OK comercial"},
        )
        with patch("ecom.permissions._user_has_perm", return_value=True):
            with patch(
                "ecom.pedido_gestion_views.ctx_desde_request",
                return_value={"id_vendedor_usr": 10},
            ):
                resp = AprobacionPedidoAprobarAPIView.as_view()(req, cod_mov=9001)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["estado_aprobacion_comercial"], "aprobado")
        mock_resolver.assert_called_once()

    @patch("ecom.pedido_gestion_views.resolver")
    def test_post_rechazar_requiere_motivo(self, mock_resolver):
        req = _req("POST", "/ecom/api/mayoristapp/aprobacion/9001/rechazar/", body={})
        with patch("ecom.permissions._user_has_perm", return_value=True):
            with patch(
                "ecom.pedido_gestion_views.ctx_desde_request",
                return_value={"id_vendedor_usr": 10},
            ):
                resp = AprobacionPedidoRechazarAPIView.as_view()(req, cod_mov=9001)
        self.assertEqual(resp.status_code, 400)
        mock_resolver.assert_not_called()

    @patch("ecom.pedido_gestion_views.resolver")
    def test_post_rechazar_ok(self, mock_resolver):
        mock_resolver.return_value = (
            True,
            "Rechazado",
            {"estado_aprobacion_comercial": "rechazado"},
        )
        req = _req(
            "POST",
            "/ecom/api/mayoristapp/aprobacion/9001/rechazar/",
            body={"motivo": "Descuento excesivo"},
        )
        with patch("ecom.permissions._user_has_perm", return_value=True):
            with patch(
                "ecom.pedido_gestion_views.ctx_desde_request",
                return_value={"id_vendedor_usr": 10},
            ):
                resp = AprobacionPedidoRechazarAPIView.as_view()(req, cod_mov=9001)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["estado_aprobacion_comercial"], "rechazado")


class TestFlujoCheckoutPendienteAprobar(TestCheckoutAprobacionComercial):
    """Encadena checkout con flag ON (pendiente) y API aprobar."""

    @patch("ecom.pedido_gestion_views.resolver")
    @patch("ecom.services.aprobacion_pedidos.aprobacion_pedidos_activa", return_value=True)
    @patch.object(checkout_svc, "aprobacion_pedidos_activa", return_value=True)
    @patch.object(checkout_svc, "evaluar_reglas", return_value=(True, ["monto"]))
    def test_checkout_pendiente_luego_aprobar_api(
        self, _eval, _flag_co, _flag_apr, mock_resolver
    ):
        state = {"codmov": 1000, "talonario": {"Nro": 57, "PV": 3}}
        conn = FakeConn(state)
        cart = self._cart(tipo="PED")
        with self._with_patches(conn):
            ok, err, _ = checkout_svc.confirmar(
                cart,
                CheckoutInput(tipo="PED", id_punto_venta=3),
                id_usuario=5,
                cod_viajante=42,
            )
        self.assertTrue(ok, err)
        self.assertEqual(state.get("aprobacion_update"), ("pendiente", 1001))

        mock_resolver.return_value = (
            True,
            "Aprobado",
            {"estado_aprobacion_comercial": "aprobado", "CodigoMovimiento": 1001},
        )
        req = _req(
            "POST",
            "/ecom/api/mayoristapp/aprobacion/1001/aprobar/",
            session_user=_session_user(cod=10),
            body={"motivo": "OK"},
        )
        with patch("ecom.permissions._user_has_perm", return_value=True):
            with patch(
                "ecom.pedido_gestion_views.ctx_desde_request",
                return_value={"id_vendedor_usr": 10},
            ):
                resp = AprobacionPedidoAprobarAPIView.as_view()(req, cod_mov=1001)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["estado_aprobacion_comercial"], "aprobado")


class TestRegresionMasterOFF(TestCase):
    @patch("ecom.services.pedidos_hub_pipeline.aprobacion_pedidos_activa", return_value=False)
    @patch("ecom.services.pedidos_hub_pipeline._borradores_carrito_legacy", return_value=[])
    @patch("ecom.services.pedidos_hub_pipeline._borradores_masivo", return_value=[])
    @patch("ecom.services.pedidos_hub_pipeline._pedidos_mysql", return_value=[])
    @patch("ecom.services.pedidos_hub_pipeline._masivos_anulados", return_value=[])
    def test_hub_master_off_sin_aprobacion_comercial(
        self,
        mock_anulados,
        mock_pedidos,
        mock_borr_m,
        mock_borr_c,
        _apr,
    ):
        sess = {"CodViajante": 10, "vendedor_a_cargo": [20, 21], "id_usuario": 1}
        hub = construir_hub_pedidos("emp1", sess, vista="kanban", dias=30)
        self.assertFalse(hub["aprobacion_comercial_activa"])
        self.assertEqual(hub["layout_movil"], "chips_cards")
        self.assertIn("columnas", hub)
        mock_pedidos.assert_called_once()
        call_kwargs = mock_pedidos.call_args
        self.assertFalse(call_kwargs.kwargs.get("aprobacion_on"))

    @patch("ecom.pedido_gestion_views.listar_pendientes_comerciales", return_value=[])
    def test_pendientes_vacio_master_off(self, mock_listar):
        req = _req("GET", "/ecom/api/mayoristapp/aprobacion/pendientes/")
        with patch("ecom.permissions._user_has_perm", return_value=True):
            resp = AprobacionPendientesAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["total"], 0)
