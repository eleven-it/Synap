# -*- coding: utf-8 -*-
"""Tests whitelist Nivel A para conteo inventario físico (Fase 5 — Strict TDD)."""
from unittest.mock import patch

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from core.middleware.base_middleware import DeviceDetectionMiddleware
from core.middleware.mobile_level_a_middleware import (
    MobileLevelAOnlyMiddleware,
    mobile_path_allowed_for_level_a,
)

MOBILE_UA = (
    'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
)


def _session_middleware():
    return SessionMiddleware(lambda req: HttpResponse())


def _build_request(path, session_user=None, accept_json=False):
    rf = RequestFactory()
    extra = {'HTTP_USER_AGENT': MOBILE_UA}
    if accept_json:
        extra['HTTP_ACCEPT'] = 'application/json'
    request = rf.get(path, **extra)
    _session_middleware().process_request(request)
    if session_user is not None:
        request.session['user'] = session_user
    request.session.save()
    DeviceDetectionMiddleware(lambda r: None).process_request(request)
    from core.middleware.base_middleware import get_usuario_extendiendo_desde_sesion

    request.user = get_usuario_extendiendo_desde_sesion(request)
    return request


def _minimal_session_user():
    return {
        'id_usuario': 1,
        'cod_usuario': 'supervisor',
        'nombre_usuario': 'Cont',
        'apellido_usuario': 'Test',
        'nombre_completo': 'Cont Test',
        'id_empresa': 1,
        'id_sucursal': 1,
        'id_puesto': 1,
        'base_empresa': 'test_base',
    }


class InvFisicoMobilePathAllowedTests(SimpleTestCase):
    """Rutas conteo permitidas; otras stock bloqueadas en móvil."""

    def test_conteo_mis_permitido(self):
        self.assertTrue(mobile_path_allowed_for_level_a('/stock/conteo/'))

    def test_conteo_campana_permitido(self):
        self.assertTrue(mobile_path_allowed_for_level_a('/stock/conteo/42/'))

    def test_api_conteo_prefetch_permitido(self):
        self.assertTrue(mobile_path_allowed_for_level_a('/stock/api/conteo/prefetch/'))

    def test_api_conteo_sync_permitido(self):
        self.assertTrue(mobile_path_allowed_for_level_a('/stock/api/conteo/sync/'))

    def test_stock_alta_movimiento_bloqueado(self):
        self.assertFalse(mobile_path_allowed_for_level_a('/stock/ingreso-movimiento/'))

    def test_stock_inventario_fisico_escritorio_bloqueado(self):
        self.assertFalse(mobile_path_allowed_for_level_a('/stock/inventario-fisico/'))

    def test_stock_inventario_tabla_bloqueado(self):
        self.assertFalse(mobile_path_allowed_for_level_a('/stock/inventario/'))

    def test_stock_api_ingreso_bloqueado(self):
        self.assertFalse(mobile_path_allowed_for_level_a('/stock/api/ingreso/datos-iniciales/'))


@override_settings(
    SESSION_ENGINE='django.contrib.sessions.backends.cache',
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'inv-fisico-middleware-tests',
        }
    },
)
class InvFisicoMobileMiddlewareRequestTests(SimpleTestCase):
    """Pruebas sin BD usando RequestFactory."""

    def setUp(self):
        self.mw = MobileLevelAOnlyMiddleware(lambda r: None)

    def test_movil_autenticado_conteo_sin_bloqueo(self):
        req = _build_request('/stock/conteo/', _minimal_session_user())
        self.assertIsNone(self.mw.process_request(req))

    def test_movil_autenticado_api_conteo_sync_sin_bloqueo(self):
        req = _build_request(
            '/stock/api/conteo/sync/',
            _minimal_session_user(),
            accept_json=True,
        )
        self.assertIsNone(self.mw.process_request(req))

    @patch('core.pwa_nivel_a.tpv_visible_en_movil', return_value=False)
    def test_movil_autenticado_stock_ingreso_403(self, _mock):
        req = _build_request('/stock/ingreso-movimiento/', _minimal_session_user())
        resp = self.mw.process_request(req)
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status_code, 403)
