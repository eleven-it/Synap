# Tests API alta recibo mayoristapp.

import unittest
from unittest.mock import MagicMock, patch

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import Client, TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.recibo_alta_relay_views import ReciboAltaRelayAPIView
from ecom.services.recibo_medios_sesion import alta_cheque_sesion, alta_retencion_sesion
from ecom.services.recibo_totales_sesion import actualiza_total_array, sincronizar_totales_recibo_sesion
from ecom.services.recibo_alta_service import (
    control_final_recibo_sesion,
    iniciar_recibo_sesion,
)
from ecom.services.recibo_saldo_favor_service import aplicar_saldo_favor_sesion


def _req_post(path: str, body: dict, session_user: dict, session_extra: dict | None = None):
    factory = APIRequestFactory()
    req = factory.post(path, body, format="json")
    middleware = SessionMiddleware(lambda r: HttpResponse())
    middleware.process_request(req)
    req.session["user"] = session_user
    if session_extra:
        for k, v in session_extra.items():
            req.session[k] = v
    req.session.save()
    return req


class TestReciboAltaService(unittest.TestCase):
    def test_iniciar_recibo_sistema(self):
        session = {}
        data = iniciar_recibo_sesion(
            session,
            idcliente=42,
            payload={"tipoNro": "sistema"},
            session_user={"id_punto_venta": 3, "base_empresa": "emp1"},
        )
        self.assertEqual(data["msg"], "ok")
        self.assertEqual(session["recibo"]["nroRecibo"], "0-0")
        self.assertEqual(session["recibo"]["codCliente"], 42)

    def test_sincronizar_total_imputacion_pura(self):
        session = {
            "recibo": {
                "facturas": {
                    "1": {"aimputar": 100.0},
                    "2": {"aimputar": 50.0},
                }
            }
        }
        out = sincronizar_totales_recibo_sesion(session)
        self.assertEqual(out["total"], 150.0)
        self.assertEqual(session["recibo"]["total"], 150.0)

    def test_sincronizar_con_efectivo_y_a_cuenta(self):
        session = {
            "recibo": {
                "facturas": {"1": {"aimputar": 200.0}},
                "efectivo": {"total": 250.0},
            }
        }
        sincronizar_totales_recibo_sesion(session)
        self.assertEqual(session["recibo"]["total"], 250.0)
        self.assertEqual(session["recibo"].get("aCuenta"), 50.0)

    def test_actualiza_total_con_descuento(self):
        session = {
            "recibo": {
                "facturas": {"1": {"aimputar": 1000.0}},
                "descuento": {"porcentaje": 10, "total": 100.0},
            }
        }
        arr = actualiza_total_array(session)
        self.assertEqual(arr["saldo"], 900.0)

    def test_alta_cheque_sesion(self):
        session = {"recibo": {"codCliente": 9, "facturas": {"1": {"aimputar": 500}}}}
        data = alta_cheque_sesion(
            session,
            {
                "numero": "123",
                "importe": 200,
                "codbanco": "1",
                "banco": "Test",
                "librador": "X",
                "cobro": "2026-07-04",
                "idCaja": 1,
            },
        )
        self.assertEqual(data["msg"], "ok")
        self.assertEqual(session["recibo"]["cheques"]["total"], 200.0)

    def test_alta_retencion_sesion(self):
        session = {"recibo": {"codCliente": 9}}
        data = alta_retencion_sesion(
            session,
            {"cod": "1", "certificado": "A1", "monto": 50, "fecha": "2026-07-04", "tipo": "IVA"},
        )
        self.assertEqual(data["msg"], "ok")
        self.assertEqual(session["recibo"]["retencion"]["total"], 50.0)

    def test_sincronizar_con_saldo_a_favor(self):
        session = {
            "recibo": {
                "facturas": {"1": {"aimputar": 300.0}},
                "saldoAFavor": {"total": 100.0},
                "efectivo": {"total": 250.0},
            }
        }
        sincronizar_totales_recibo_sesion(session)
        self.assertEqual(session["recibo"]["total"], 350.0)
        self.assertEqual(session["recibo"].get("aCuenta"), 50.0)

    @patch("ecom.services.recibo_saldo_favor_service.listar_lineas_saldo_favor")
    def test_aplicar_saldo_favor_fifo(self, mock_lineas):
        mock_lineas.return_value = [
            {"id_recibo_factura": 10, "saldo": 80.0, "tipocomprobante": "REC", "nrocomprobante": "0001-1"},
            {"id_recibo_factura": 11, "saldo": 50.0, "tipocomprobante": "REC", "nrocomprobante": "0001-2"},
        ]
        session = {"recibo": {"codCliente": 9, "facturas": {"1": {"aimputar": 120.0}}}}
        data = aplicar_saldo_favor_sesion(session, base_empresa="emp1", monto=100)
        self.assertEqual(data["msg"], "ok")
        self.assertEqual(session["recibo"]["saldoAFavor"]["total"], 100.0)
        self.assertEqual(len(session["recibo"]["saldoAFavor"]["lineas"]), 2)
        self.assertEqual(session["recibo"]["total"], 100.0)

    def test_control_final_ok_imputacion_pura(self):
        session = {"recibo": {"total": 200.0, "totalImputado": 200.0}}
        ctrl = control_final_recibo_sesion(session)
        self.assertEqual(ctrl["msg"], "ok")


class TestReciboAltaRelayAPIView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = True
        return u

    @patch("ecom.recibo_alta_relay_views.ecom_cobranzas_write_enabled", return_value=False)
    def test_iniciar_bloqueado_sin_flag(self, _mock):
        req = _req_post(
            "/ecom/api/mayoristapp/recibos/alta/accion/?ajax=1",
            {"iniciar": 1},
            {"base_empresa": "emp1", "id_punto_venta": 1},
            session_extra={"mayoristapp": {"idcliente": 5}},
        )
        force_authenticate(req, user=self._user())
        resp = ReciboAltaRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 409)

    @patch("ecom.recibo_alta_relay_views.control_fact_temporal_libre", return_value=(True, ""))
    @patch("ecom.recibo_alta_relay_views.ecom_cobranzas_write_enabled", return_value=True)
    def test_iniciar_ok(self, _w, _temp):
        req = _req_post(
            "/ecom/api/mayoristapp/recibos/alta/accion/?ajax=1",
            {"iniciar": 1, "tipoNro": "sistema"},
            {"base_empresa": "emp1", "id_punto_venta": 2},
            session_extra={"mayoristapp": {"idcliente": 9}},
        )
        force_authenticate(req, user=self._user())
        resp = ReciboAltaRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["msg"], "ok")

    def test_sin_idcliente_400(self):
        req = _req_post(
            "/ecom/api/mayoristapp/recibos/alta/accion/?ajax=1",
            {"iniciar": 1},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        with patch("ecom.recibo_alta_relay_views.ecom_cobranzas_write_enabled", return_value=True):
            resp = ReciboAltaRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 400)


class TestAltaReciboWebView(TestCase):
    @patch("ecom.mayoristapp_web_views.leer_idcliente_mayoristapp", return_value=None)
    def test_redirect_sin_cliente(self, _idc):
        client = Client()
        session = client.session
        session["user"] = {"base_empresa": "emp1"}
        session.save()
        resp = client.get("/ecom/mayoristapp/recibos/alta/")
        self.assertIn(resp.status_code, (302, 301))
