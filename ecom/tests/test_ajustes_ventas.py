"""Tests pedidos_validan_stock y API ajustes de ventas."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.ajustes_ventas_views import AjustesVentasAPIView
from ecom.services.ecom_config_mysql import pedidos_validan_stock


class TestPedidosValidanStock(SimpleTestCase):
    @patch("ecom.services.ecom_config_mysql.leer_valor_configuracion_ecom")
    def test_default_si_si_falta_fila(self, mock_leer):
        mock_leer.return_value = "Si"
        self.assertTrue(pedidos_validan_stock("emp1"))
        mock_leer.assert_called_once()

    @patch("ecom.services.ecom_config_mysql.leer_valor_configuracion_ecom")
    def test_normaliza_no(self, mock_leer):
        for val in ("No", "no", "0", "false", "FALSE", "off", "n", "N"):
            mock_leer.return_value = val
            self.assertFalse(pedidos_validan_stock("emp1"), msg=val)

    @patch("ecom.services.ecom_config_mysql.leer_valor_configuracion_ecom")
    def test_si_explicito(self, mock_leer):
        for val in ("Si", "si", "1", "true", "Sí"):
            mock_leer.return_value = val
            self.assertTrue(pedidos_validan_stock("emp1"), msg=val)


class _UserConPermiso:
    is_authenticated = True
    is_superuser = False

    def tiene_permiso(self, codigo):
        return codigo == "ecom.config_ajustes_ventas"


class TestAjustesVentasAPI(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    @patch("ecom.ajustes_ventas_views.pedidos_validan_stock", return_value=True)
    @patch("ecom.ajustes_ventas_views._session_base_empresa", return_value="emp1")
    def test_get_devuelve_flag(self, _base, _stock):
        req = self.factory.get("/api/mayoristapp/ajustes-ventas/")
        force_authenticate(req, user=_UserConPermiso())
        req.session = {"user": {"base_empresa": "emp1"}}
        resp = AjustesVentasAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["validar_stock_pedidos"])

    @patch("ecom.ajustes_ventas_views.escribir_valor_configuracion_ecom", return_value=True)
    @patch("ecom.ajustes_ventas_views._session_base_empresa", return_value="emp1")
    def test_post_desactiva_validacion(self, _base, mock_escribir):
        req = self.factory.post(
            "/api/mayoristapp/ajustes-ventas/",
            {"validar_stock_pedidos": False},
            format="json",
        )
        force_authenticate(req, user=_UserConPermiso())
        req.session = {"user": {"base_empresa": "emp1"}}
        resp = AjustesVentasAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["validar_stock_pedidos"])
        mock_escribir.assert_called_once_with("emp1", "ecom_validar_stock_pedidos", "No")
