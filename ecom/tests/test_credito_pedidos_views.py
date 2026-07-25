# -*- coding: utf-8 -*-
"""Contratos HTTP y segregación de permisos del workflow de crédito."""

import json
from unittest.mock import MagicMock, patch

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.credito_views import (
    CreditoAprobarAPIView,
    CreditoColaFinanzasView,
    CreditoPlantillasAPIView,
    CreditoPoliticaListView,
    CreditoPoliticasAPIView,
)


def _request_post(path, payload, permisos):
    request = APIRequestFactory().post(
        path, data=json.dumps(payload), content_type="application/json"
    )
    middleware = SessionMiddleware(lambda req: HttpResponse())
    middleware.process_request(request)
    request.session["user"] = {
        "id_usuario": 7,
        "base_empresa": "empresa_test",
        "synap_permisos": permisos,
    }
    user = MagicMock(is_authenticated=True, is_superuser=False, id=7)
    force_authenticate(request, user=user)
    return request


class CreditoPoliticasHttpTests(SimpleTestCase):
    @patch("ecom.credito_views.mysql_cursor")
    def test_configurar_crea_politica_ped(self, mock_mysql_cursor):
        cursor = MagicMock()
        mock_mysql_cursor.return_value.__enter__.return_value = cursor
        request = _request_post(
            "/ecom/api/credito/politicas/",
            {"id_cliente": "25", "canal": "PED", "limite_dias": "30"},
            ["finance.credito.configurar"],
        )

        response = CreditoPoliticasAPIView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["ok"])
        cursor.execute.assert_called_once()
        self.assertEqual(cursor.execute.call_args.args[1], (25, "PED", 30, "Si"))

    def test_sin_permiso_configurar_recibe_403(self):
        request = _request_post(
            "/ecom/api/credito/politicas/",
            {"canal": "PED", "limite_dias": 30},
            [],
        )

        response = CreditoPoliticasAPIView.as_view()(request)

        self.assertEqual(response.status_code, 403)

    def test_whatsapp_se_rechaza_por_fuera_de_alcance(self):
        request = _request_post(
            "/ecom/api/credito/politicas/",
            {"canal": "WHATSAPP", "limite_dias": 30},
            ["finance.credito.configurar"],
        )

        response = CreditoPoliticasAPIView.as_view()(request)

        self.assertEqual(response.status_code, 400)
        self.assertIn("PED o PRE", response.data["error"])

    def test_plantilla_whatsapp_tambien_se_rechaza(self):
        request = _request_post(
            "/ecom/api/credito/plantillas/",
            {"canal": "WHATSAPP", "asunto": "Aviso", "cuerpo": "Texto"},
            ["finance.credito.configurar"],
        )

        response = CreditoPlantillasAPIView.as_view()(request)

        self.assertEqual(response.status_code, 400)
        self.assertIn("PED o PRE", response.data["error"])

    @patch("ecom.credito_views.mysql_cursor")
    def test_solo_configurar_no_puede_aprobar_y_si_crear_politica(
        self, mock_mysql_cursor
    ):
        cursor = MagicMock()
        mock_mysql_cursor.return_value.__enter__.return_value = cursor
        config_request = _request_post(
            "/ecom/api/credito/politicas/",
            {"canal": "PRE", "limite_dias": 15},
            ["finance.credito.configurar"],
        )
        aprobar_request = _request_post(
            "/ecom/api/credito/pedidos/99/aprobar/",
            {},
            ["finance.credito.configurar"],
        )

        config_response = CreditoPoliticasAPIView.as_view()(config_request)
        aprobar_response = CreditoAprobarAPIView.as_view()(aprobar_request, cod_mov=99)

        self.assertEqual(config_response.status_code, 200)
        self.assertEqual(aprobar_response.status_code, 403)


class CreditoSegregacionVistasTests(SimpleTestCase):
    def test_vistas_exponen_permisos_finanzas_separados(self):
        self.assertEqual(
            CreditoColaFinanzasView.permiso_requerido, "finance.credito.aprobar"
        )
        self.assertEqual(
            CreditoPoliticaListView.permiso_requerido,
            "finance.credito.configurar",
        )
