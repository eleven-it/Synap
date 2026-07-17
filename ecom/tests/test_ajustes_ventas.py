"""Tests pedidos_validan_stock, workflow comercial y APIs ajustes de ventas."""

from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.ajustes_ventas_views import AjustesVentasAPIView, AjustesWorkflowAPIView
from ecom.services.ecom_config_mysql import (
    KEY_APROBACION_PEDIDOS_ACTIVA,
    KEY_ENVIAR_MAIL_CONFIRMAR_PEDIDO,
    KEY_VALIDAR_STOCK_PEDIDOS,
    KEY_WORKFLOW_JERARQUIA_COMERCIAL,
    aprobacion_pedidos_activa,
    guardar_config_workflow_comercial,
    leer_config_workflow_comercial,
    pedidos_envian_mail_confirmacion,
    pedidos_validan_stock,
    workflow_jerarquia_comercial_activo,
)


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


class TestPedidosEnvianMailConfirmacion(SimpleTestCase):
    @patch("ecom.services.ecom_config_mysql.leer_valor_configuracion_ecom")
    def test_default_si_si_falta_fila(self, mock_leer):
        mock_leer.return_value = "Si"
        self.assertTrue(pedidos_envian_mail_confirmacion("emp1"))
        mock_leer.assert_called_once_with("emp1", KEY_ENVIAR_MAIL_CONFIRMAR_PEDIDO, "Si")

    @patch("ecom.services.ecom_config_mysql.leer_valor_configuracion_ecom")
    def test_normaliza_no(self, mock_leer):
        mock_leer.return_value = "No"
        self.assertFalse(pedidos_envian_mail_confirmacion("emp1"))


class TestWorkflowJerarquiaComercial(SimpleTestCase):
    @patch("ecom.services.ecom_config_mysql.leer_valor_configuracion_ecom")
    def test_master_default_no(self, mock_leer):
        mock_leer.return_value = "No"
        self.assertFalse(workflow_jerarquia_comercial_activo("emp1"))

    @patch("ecom.services.ecom_config_mysql.leer_valor_configuracion_ecom")
    def test_aprobacion_subflag_ignorado_si_master_no(self, mock_leer):
        def side_effect(base, key, default=""):
            if key == KEY_WORKFLOW_JERARQUIA_COMERCIAL:
                return "No"
            if key == KEY_APROBACION_PEDIDOS_ACTIVA:
                return "Si"
            return default

        mock_leer.side_effect = side_effect
        self.assertFalse(aprobacion_pedidos_activa("emp1"))

    @patch("ecom.services.ecom_config_mysql.leer_valor_configuracion_ecom")
    def test_aprobacion_activa_si_master_si(self, mock_leer):
        def side_effect(base, key, default=""):
            if key == KEY_WORKFLOW_JERARQUIA_COMERCIAL:
                return "Si"
            if key == KEY_APROBACION_PEDIDOS_ACTIVA:
                return "Si"
            return default

        mock_leer.side_effect = side_effect
        self.assertTrue(aprobacion_pedidos_activa("emp1"))


class TestGuardarConfigWorkflow(SimpleTestCase):
    @patch("ecom.services.ecom_config_mysql.leer_valor_configuracion_ecom")
    @patch("ecom.services.ecom_config_mysql.escribir_valor_configuracion_ecom")
    def test_persiste_flags_y_umbrales(self, mock_escribir, mock_leer):
        valores = {}

        def leer_side_effect(base, key, default=""):
            return valores.get(key, default)

        def escribir_side_effect(base, key, val):
            valores[key] = val
            return True

        mock_leer.side_effect = leer_side_effect
        mock_escribir.side_effect = escribir_side_effect

        cfg = guardar_config_workflow_comercial(
            "emp1",
            {
                "workflow_jerarquia_comercial": True,
                "aprobacion_pedidos_activa": True,
                "objetivos_en_pedidos": True,
                "backorder_en_pedidos": False,
                "umbral_monto": "50000",
                "umbral_desc_pie": "15",
                "umbral_desc_renglon": "",
            },
        )

        self.assertEqual(valores[KEY_WORKFLOW_JERARQUIA_COMERCIAL], "Si")
        self.assertEqual(valores[KEY_APROBACION_PEDIDOS_ACTIVA], "Si")
        self.assertTrue(cfg["workflow_jerarquia_comercial"])
        self.assertTrue(cfg["aprobacion_pedidos_activa"])
        self.assertEqual(cfg["umbral_monto"], "50000")
        self.assertEqual(cfg["umbral_desc_pie"], "15")

    @patch("ecom.services.ecom_config_mysql.leer_valor_configuracion_ecom")
    def test_leer_config_incluye_umbrales(self, mock_leer):
        def side_effect(base, key, default=""):
            valores = {
                KEY_WORKFLOW_JERARQUIA_COMERCIAL: "Si",
                KEY_APROBACION_PEDIDOS_ACTIVA: "Si",
                "ecom_aprobacion_umbral_monto": "1000.50",
                "ecom_aprobacion_umbral_desc_pie": "",
                "ecom_aprobacion_umbral_desc_renglon": "5",
                "ecom_objetivos_en_pedidos": "No",
                "ecom_backorder_en_pedidos": "Si",
            }
            return valores.get(key, default)

        mock_leer.side_effect = side_effect
        cfg = leer_config_workflow_comercial("emp1")
        self.assertTrue(cfg["workflow_jerarquia_comercial"])
        self.assertTrue(cfg["aprobacion_pedidos_activa"])
        self.assertEqual(cfg["umbral_monto"], "1000.5")
        self.assertEqual(cfg["umbral_desc_renglon"], "5")


class _UserConPermiso:
    is_authenticated = True
    is_superuser = False

    def tiene_permiso(self, codigo):
        return codigo == "ecom.config_ajustes_ventas"


class TestAjustesVentasAPI(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    @patch("ecom.ajustes_ventas_views.pedidos_validan_stock", return_value=True)
    @patch("ecom.ajustes_ventas_views.pedidos_envian_mail_confirmacion", return_value=True)
    @patch("ecom.ajustes_ventas_views._session_base_empresa", return_value="emp1")
    def test_get_devuelve_flags(self, _base, _mail, _stock):
        req = self.factory.get("/api/mayoristapp/ajustes-ventas/")
        force_authenticate(req, user=_UserConPermiso())
        req.session = {"user": {"base_empresa": "emp1"}}
        resp = AjustesVentasAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["validar_stock_pedidos"])
        self.assertTrue(resp.data["enviar_mail_confirmar_pedido"])

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

    @patch("ecom.ajustes_ventas_views.escribir_valor_configuracion_ecom", return_value=True)
    @patch("ecom.ajustes_ventas_views._session_base_empresa", return_value="emp1")
    def test_post_desactiva_mail_confirmacion(self, _base, mock_escribir):
        req = self.factory.post(
            "/api/mayoristapp/ajustes-ventas/",
            {"enviar_mail_confirmar_pedido": False},
            format="json",
        )
        force_authenticate(req, user=_UserConPermiso())
        req.session = {"user": {"base_empresa": "emp1"}}
        resp = AjustesVentasAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["enviar_mail_confirmar_pedido"])
        mock_escribir.assert_called_once_with(
            "emp1", KEY_ENVIAR_MAIL_CONFIRMAR_PEDIDO, "No"
        )


class TestAjustesWorkflowAPI(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    @patch("ecom.ajustes_ventas_views.leer_config_workflow_comercial")
    @patch("ecom.ajustes_ventas_views._session_base_empresa", return_value="emp1")
    def test_get_devuelve_workflow(self, _base, mock_leer):
        mock_leer.return_value = {
            "workflow_jerarquia_comercial": False,
            "aprobacion_pedidos_activa": False,
            "aprobacion_pedidos_activa_raw": False,
            "objetivos_en_pedidos": True,
            "backorder_en_pedidos": False,
            "umbral_monto": "",
            "umbral_desc_pie": "",
            "umbral_desc_renglon": "",
        }
        req = self.factory.get("/api/mayoristapp/ajustes/workflow/")
        force_authenticate(req, user=_UserConPermiso())
        req.session = {"user": {"base_empresa": "emp1"}}
        resp = AjustesWorkflowAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["objetivos_en_pedidos"])

    @patch("ecom.ajustes_ventas_views.guardar_config_workflow_comercial")
    @patch("ecom.ajustes_ventas_views._session_base_empresa", return_value="emp1")
    def test_post_persiste_workflow(self, _base, mock_guardar):
        mock_guardar.return_value = {
            "workflow_jerarquia_comercial": True,
            "aprobacion_pedidos_activa": True,
            "aprobacion_pedidos_activa_raw": True,
            "objetivos_en_pedidos": False,
            "backorder_en_pedidos": True,
            "umbral_monto": "10000",
            "umbral_desc_pie": "",
            "umbral_desc_renglon": "",
        }
        req = self.factory.post(
            "/api/mayoristapp/ajustes/workflow/",
            {
                "workflow_jerarquia_comercial": True,
                "aprobacion_pedidos_activa": True,
                "umbral_monto": "10000",
            },
            format="json",
        )
        force_authenticate(req, user=_UserConPermiso())
        req.session = {"user": {"base_empresa": "emp1"}}
        resp = AjustesWorkflowAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["workflow_jerarquia_comercial"])
        mock_guardar.assert_called_once()
        payload = mock_guardar.call_args[0][1]
        self.assertTrue(payload["workflow_jerarquia_comercial"])
