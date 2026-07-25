# -*- coding: utf-8 -*-
"""Tests API pre-check crédito (REQ-VTA-10/11 — Fase A TDD)."""
import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.credito_views import CreditoPreCheckAPIView
from ecom.services.credito_pedidos.evaluacion import (
    ResultadoCredito,
    SEMAFORO_ROJO,
    SEMAFORO_VERDE,
)
from ecom.services.mayorista_credito import NO_AUTORIZADO


def _req_post(path, payload, *, base="emp1"):
    factory = APIRequestFactory()
    req = factory.post(path, data=json.dumps(payload), content_type="application/json")
    middleware = SessionMiddleware(lambda r: HttpResponse())
    middleware.process_request(req)
    req.session["user"] = {"id_usuario": 1, "base_empresa": base}
    req.session.save()
    force_authenticate(req, user=MagicMock(is_authenticated=True, id=1))
    return req


class CreditoPreCheckTests(TestCase):
    def test_flag_off_no_evalua_exposicion(self):
        req = _req_post("/ecom/api/credito/pre-check/", {"id_cliente": 10, "canal": "PED", "total_pedido": "1000"})
        with patch("ecom.credito_views.credito_pedidos_activo", return_value=False):
            resp = CreditoPreCheckAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["activo"])

    @patch("ecom.credito_views.get_connection")
    @patch("ecom.credito_views.credito_pedidos_activo", return_value=True)
    @patch("ecom.credito_views.evaluar_pedido")
    @patch("ecom.credito_views._fetch_cliente_credito")
    def test_flag_on_devuelve_semaforo_y_motivos(
        self, mock_cli, mock_eval, _flag, mock_conn
    ):
        mock_cli.return_value = {
            "Credito": Decimal("5000"),
            "credito_limite_dias": 30,
        }
        mock_eval.return_value = ResultadoCredito(
            autorizacion=NO_AUTORIZADO,
            motivos=["monto"],
            limite=Decimal("5000"),
            exposicion=Decimal("7000"),
            disponible=Decimal("-2000"),
            semaforo=SEMAFORO_ROJO,
        )
        cm = MagicMock()
        mock_conn.return_value.__enter__.return_value = cm
        cm.cursor.return_value = MagicMock()

        req = _req_post("/ecom/api/credito/pre-check/", {"id_cliente": 10, "canal": "PED", "total_pedido": "2000"})
        resp = CreditoPreCheckAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["activo"])
        self.assertEqual(resp.data["credito"]["semaforo"], SEMAFORO_ROJO)
        self.assertIn("monto", resp.data["credito"]["motivos"])
        mock_eval.assert_called_once()
        self.assertFalse(mock_eval.call_args.kwargs.get("persistir"))

    @patch("ecom.credito_views.get_connection")
    @patch("ecom.credito_views.credito_pedidos_activo", return_value=True)
    @patch("ecom.credito_views.evaluar_pedido")
    @patch("ecom.credito_views._fetch_cliente_credito")
    def test_credito_cero_sin_tope_en_respuesta(
        self, mock_cli, mock_eval, _flag, mock_conn
    ):
        mock_cli.return_value = {
            "Credito": Decimal("0"),
            "credito_limite_dias": 30,
        }
        mock_eval.return_value = ResultadoCredito(
            autorizacion="Autorizado",
            limite=Decimal("0"),
            sin_tope_monetario=True,
            semaforo="verde",
        )
        cm = MagicMock()
        mock_conn.return_value.__enter__.return_value = cm
        cm.cursor.return_value = MagicMock()

        req = _req_post("/ecom/api/credito/pre-check/", {"id_cliente": 10, "canal": "PED", "total_pedido": "999999"})
        resp = CreditoPreCheckAPIView.as_view()(req)
        self.assertTrue(resp.data["credito"]["sin_tope_monetario"])
        self.assertIsNone(resp.data["credito"]["disponible"])

    @patch("ecom.credito_views.get_connection")
    @patch("ecom.credito_views.credito_pedidos_activo", return_value=True)
    @patch("ecom.credito_views.evaluar_pedido")
    @patch("ecom.credito_views._fetch_cliente_credito")
    def test_precheck_verde_expone_semaforo_verde(
        self, mock_cli, mock_eval, _flag, mock_conn
    ):
        mock_cli.return_value = {"Credito": Decimal("5000"), "credito_limite_dias": 30}
        mock_eval.return_value = ResultadoCredito(
            autorizacion="Autorizado",
            limite=Decimal("5000"),
            exposicion=Decimal("1000"),
            disponible=Decimal("4000"),
            semaforo=SEMAFORO_VERDE,
        )
        cm = MagicMock()
        mock_conn.return_value.__enter__.return_value = cm
        cm.cursor.return_value = MagicMock()

        response = CreditoPreCheckAPIView.as_view()(
            _req_post(
                "/ecom/api/credito/pre-check/",
                {"id_cliente": 10, "canal": "PED", "total_pedido": "500"},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["credito"]["semaforo"], SEMAFORO_VERDE)
        self.assertEqual(response.data["credito"]["disponible"], 4000.0)
