"""Contrato PDF y alcance de cartera de los reportes mayoristas."""

from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from ecom.mayoristapp_listado_views import CarteraReportePDFView


class CarteraReportePDFTests(SimpleTestCase):
    def _request(self):
        request = RequestFactory().get("/ecom/mayoristapp/portal/no-cancelados/pdf/")
        request.user = SimpleNamespace(is_authenticated=True)
        request.session = {
            "user": {"base_empresa": "administranet2"},
            "mayoristapp": {"idcliente": 904},
        }
        return request

    @patch("ecom.mayoristapp_web_views.asegurar_contexto_mayoristapp")
    @patch("ecom.mayoristapp_listado_views.cliente_accesible_por_sesion", return_value=False)
    def test_rechaza_cliente_fuera_de_cartera(self, _acceso, _contexto):
        response = CarteraReportePDFView.as_view()(self._request(), slug="no-cancelados")
        self.assertEqual(response.status_code, 403)

    @patch("ecom.mayoristapp_web_views.asegurar_contexto_mayoristapp")
    @patch("ecom.mayoristapp_listado_views.cliente_accesible_por_sesion", return_value=True)
    @patch("ecom.mayoristapp_listado_views.listar_no_cancelados_relay",
           return_value={"filas": [{"SaldoSigned": 10}], "saldo_al_dia": 10})
    @patch("ecom.mayoristapp_listado_views.get_empresa_para_reporte", return_value={})
    @patch("ecom.mayoristapp_listado_views.generar_pdf_cartera", return_value=b"%PDF-1.4\n")
    def test_entrega_pdf_del_cliente_seleccionado(self, renderer, _empresa, relay, acceso, _contexto):
        response = CarteraReportePDFView.as_view()(self._request(), slug="no-cancelados")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF-"))
        self.assertIn("no-cancelados-904.pdf", response["Content-Disposition"])
        acceso.assert_called_once_with("administranet2", 904, {"base_empresa": "administranet2"}, solo_cartera=True)
        self.assertEqual(relay.call_args.args[2], 904)
        self.assertTrue(relay.call_args.args[1]["solo_cobranzas"])
        self.assertEqual(renderer.call_args.args[-1], 10)
