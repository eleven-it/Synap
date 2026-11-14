"""Alcance del cliente y exportación PDF de la cartera."""

from unittest.mock import MagicMock, patch

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.cartera_report_pdf_views import CarteraReportPDFAPIView


class CarteraReportPDFViewTests(TestCase):
    def _request(self):
        req = APIRequestFactory().post(
            "/ecom/api/mayoristapp/reportes/no-cancelados/pdf/",
            {"campoBusca": "-"}, format="json",
        )
        SessionMiddleware(lambda _req: HttpResponse()).process_request(req)
        req.session["user"] = {"base_empresa": "test_base", "tipousuario": "vendedor"}
        req.session["mayoristapp"] = {"idcliente": 12, "cliente": [{"cliente": "Cliente 12"}]}
        force_authenticate(req, user=MagicMock(is_authenticated=True, id=1))
        return req

    @patch("ecom.cartera_report_pdf_views.cliente_accesible_por_sesion", return_value=False)
    def test_rechaza_cliente_fuera_de_cartera(self, _mock_access):
        response = CarteraReportPDFAPIView.as_view()(self._request(), tipo="no-cancelados")
        self.assertEqual(response.status_code, 403)

    @patch("ecom.cartera_report_pdf_views.generar_reporte_cartera_pdf", return_value=b"%PDF-demo")
    @patch("ecom.cartera_report_pdf_views.listar_no_cancelados_relay", return_value={"filas": [], "saldo_al_dia": 0})
    @patch("ecom.cartera_report_pdf_views.cliente_accesible_por_sesion", return_value=True)
    def test_descarga_reporte_del_cliente_activo(self, _mock_access, _mock_rows, mock_pdf):
        response = CarteraReportPDFAPIView.as_view()(self._request(), tipo="no-cancelados")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("cliente-12", response["Content-Disposition"])
        self.assertEqual(mock_pdf.call_args.kwargs["cliente_codigo"], 12)
