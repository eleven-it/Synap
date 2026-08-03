# -*- coding: utf-8 -*-
"""Tests API cotización dólar."""
import json
from unittest.mock import patch

from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse

from contabilidad_audit.cotizacion_views import cotizacion_api_aceptar, cotizacion_api_vigente


def _session_user(base_empresa: str = "empresa_test"):
    return {
        "id_usuario": 1,
        "cod_usuario": "supervisor",
        "base_empresa": base_empresa,
    }


def _build_request(method, path, session_user=None, body=None):
    factory = RequestFactory()
    if method == "GET":
        request = factory.get(path)
    else:
        request = factory.post(
            path,
            data=body or b"{}",
            content_type="application/json",
        )
    request.session = {"user": session_user or _session_user()}
    request.user = type(
        "U",
        (),
        {
            "is_authenticated": True,
            "cod_usuario": session_user.get("cod_usuario") if session_user else "test",
            "is_admin": lambda self: False,
            "tiene_permiso": lambda self, code: False,
        },
    )()
    setattr(request, "_messages", FallbackStorage(request))
    return request


class CotizacionApiPermissionTest(SimpleTestCase):
    @patch("contabilidad_audit.cotizacion_views._permiso_aceptar", return_value=False)
    def test_post_aceptar_403_sin_permiso(self, _mock_perm):
        request = _build_request(
            "POST",
            "/contabilidad/api/cotizacion/aceptar/",
            session_user=_session_user(),
            body=json.dumps({"valor": 1180}).encode(),
        )
        res = cotizacion_api_aceptar(request)
        self.assertEqual(res.status_code, 403)
        data = json.loads(res.content)
        self.assertFalse(data.get("ok"))
        self.assertIn("permiso", data.get("error", "").lower())

    @patch("contabilidad_audit.cotizacion_views.obtener_vigente", return_value={"valor": 1200, "disponible": True})
    @patch("contabilidad_audit.cotizacion_views._permiso_ver", return_value=True)
    def test_get_vigente_ok(self, _pv, _mock_vig):
        request = _build_request(
            "GET",
            "/contabilidad/api/cotizacion/vigente/",
            session_user=_session_user(),
        )
        res = cotizacion_api_vigente(request)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(json.loads(res.content).get("ok"))

    @patch("contabilidad_audit.cotizacion_views._permiso_ver", return_value=False)
    def test_get_vigente_403(self, _mock_perm):
        request = _build_request(
            "GET",
            "/contabilidad/api/cotizacion/vigente/",
            session_user=_session_user(),
        )
        res = cotizacion_api_vigente(request)
        self.assertEqual(res.status_code, 403)


class CotizacionUrlSmokeTest(TestCase):
    def test_reverse_cotizacion_dolar(self):
        self.assertEqual(
            reverse("contabilidad_audit:cotizacion_dolar"),
            "/contabilidad/cotizacion-dolar/",
        )

    def test_reverse_api_aceptar(self):
        self.assertEqual(
            reverse("contabilidad_audit:cotizacion_api_aceptar"),
            "/contabilidad/api/cotizacion/aceptar/",
        )
