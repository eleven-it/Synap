# -*- coding: utf-8 -*-
"""Tests vistas móviles conteo inventario físico (Fase 4 — Strict TDD)."""
import datetime
from unittest.mock import patch

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import reverse

from core.middleware.base_middleware import DeviceDetectionMiddleware

MOBILE_UA = (
    'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
)

_CAMPANA_ACTIVA = {
    'id_campana': 5,
    'fecha': datetime.date(2026, 7, 23),
    'estado': 'EnConteo',
    'depositos': [1, 2],
    'catalogo_version': 'abc123',
    'contadores': [10],
}


def _session_middleware():
    return SessionMiddleware(lambda req: HttpResponse())


def _mobile_request(path='/stock/conteo/'):
    rf = RequestFactory()
    request = rf.get(path, HTTP_USER_AGENT=MOBILE_UA)
    _session_middleware().process_request(request)
    request.session['user'] = {
        'id_usuario': 10,
        'cod_usuario': 'supervisor',
        'base_empresa': 'test_base',
        'nombre_empresa': 'Empresa Test',
        'nombre_usuario': 'Ana',
        'apellido_usuario': 'Cont',
    }
    request.session.save()
    DeviceDetectionMiddleware(lambda r: None).process_request(request)
    from core.middleware.base_middleware import get_usuario_extendiendo_desde_sesion

    request.user = get_usuario_extendiendo_desde_sesion(request)
    return request


@override_settings(
    SESSION_ENGINE='django.contrib.sessions.backends.cache',
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'inv-fisico-mobile-tests',
        }
    },
)
class InvFisicoMobileViewTests(SimpleTestCase):
    @patch('stock.mobile_views.listar_campanas_para_contador', return_value=[_CAMPANA_ACTIVA])
    @patch('stock.mobile_views.listar_depositos_elegibles', return_value=[
        {'id_deposito': 1, 'nombre': 'Dep A', 'tipo_mpr': 'Terminado'},
        {'id_deposito': 2, 'nombre': 'Dep B', 'tipo_mpr': 'Terminado'},
    ])
    def test_mis_conteos_renderiza_campanas(self, _deps, _campanas):
        from stock.mobile_views import conteo_mis_view

        request = _mobile_request()
        response = conteo_mis_view(request)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('Mis conteos', content)
        self.assertIn('EnConteo', content)
        self.assertNotIn('saldo_snapshot', content)
        self.assertNotIn('diferencia', content)

    @patch('stock.mobile_views.obtener_campana', return_value=_CAMPANA_ACTIVA)
    @patch('stock.mobile_views.usuario_asignado_a_campana', return_value=True)
    @patch('stock.mobile_views.listar_depositos_elegibles', return_value=[
        {'id_deposito': 1, 'nombre': 'Dep A', 'tipo_mpr': 'Terminado'},
    ])
    def test_conteo_campana_renderiza_escaner(self, _deps, _asignado, _campana):
        from stock.mobile_views import conteo_campana_view

        request = _mobile_request('/stock/conteo/5/?deposito=1')
        response = conteo_campana_view(request, id_campana=5)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('html5-qrcode', content)
        self.assertIn('InvFisicoOffline', content)
        self.assertIn('scanner-container', content)
        self.assertIn('pendientes de sync', content.lower())

    def test_url_conteo_campana_resuelve(self):
        self.assertEqual(reverse('stock:conteo_campana', kwargs={'id_campana': 5}), '/stock/conteo/5/')


@override_settings(
    SESSION_ENGINE='django.contrib.sessions.backends.cache',
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'inv-fisico-mobile-shell-tests',
        }
    },
)
class InvFisicoShellPwaTests(SimpleTestCase):
    """Con UA móvil se usan los templates dedicados y se oculta el chrome Synap."""

    def test_selector_devuelve_templates_mobile(self):
        from core.utils.template_selector import get_template_for_device

        request = _mobile_request('/stock/conteo/5/')
        self.assertTrue(request.is_mobile)
        self.assertEqual(
            get_template_for_device(request, 'stock/conteo/conteo.html'),
            'stock/conteo/mobile/conteo.html',
        )
        self.assertEqual(
            get_template_for_device(request, 'stock/conteo/mis_conteos.html'),
            'stock/conteo/mobile/mis_conteos.html',
        )

    @patch('stock.mobile_views.obtener_campana', return_value=_CAMPANA_ACTIVA)
    @patch('stock.mobile_views.usuario_asignado_a_campana', return_value=True)
    @patch('stock.mobile_views.listar_depositos_elegibles', return_value=[
        {'id_deposito': 1, 'nombre': 'Dep A', 'tipo_mpr': 'Terminado'},
    ])
    def test_conteo_movil_usa_template_mobile(self, _deps, _asignado, _campana):
        from stock.mobile_views import conteo_campana_view

        request = _mobile_request('/stock/conteo/5/?deposito=1')
        with patch('stock.mobile_views.render') as mock_render:
            mock_render.return_value = HttpResponse()
            conteo_campana_view(request, id_campana=5)
        self.assertEqual(mock_render.call_args[0][1], 'stock/conteo/mobile/conteo.html')

    @patch('stock.mobile_views.listar_campanas_para_contador', return_value=[_CAMPANA_ACTIVA])
    @patch('stock.mobile_views.listar_depositos_elegibles', return_value=[
        {'id_deposito': 1, 'nombre': 'Dep A', 'tipo_mpr': 'Terminado'},
    ])
    def test_mis_conteos_usa_template_mobile(self, _deps, _campanas):
        from stock.mobile_views import conteo_mis_view

        request = _mobile_request('/stock/conteo/')
        with patch('stock.mobile_views.render') as mock_render:
            mock_render.return_value = HttpResponse()
            conteo_mis_view(request)
        self.assertEqual(mock_render.call_args[0][1], 'stock/conteo/mobile/mis_conteos.html')

    @patch('stock.mobile_views.obtener_campana', return_value=_CAMPANA_ACTIVA)
    @patch('stock.mobile_views.usuario_asignado_a_campana', return_value=True)
    @patch('stock.mobile_views.listar_depositos_elegibles', return_value=[
        {'id_deposito': 1, 'nombre': 'Dep A', 'tipo_mpr': 'Terminado'},
    ])
    def test_conteo_movil_oculta_chrome_y_es_fullscreen(self, _deps, _asignado, _campana):
        from stock.mobile_views import conteo_campana_view

        request = _mobile_request('/stock/conteo/5/?deposito=1')
        content = conteo_campana_view(request, id_campana=5).content.decode('utf-8')
        self.assertIn("classList.add('conteo-pwa')", content)
        self.assertIn('viewport-fit=cover', content)
        self.assertIn('100dvh', content)
        self.assertIn('env(safe-area-inset-top)', content)
        self.assertIn('body.conteo-pwa header.w-full.fixed { display: none !important; }', content)
        self.assertIn('body.conteo-pwa #status-bar { display: none !important; }', content)
        # Flujo operario: pad numérico, registrar y cantidad explícita en el historial
        self.assertIn('agregarDigitoCantidad', content)
        self.assertIn('Registrar conteo', content)
        self.assertIn('Cant.', content)
        self.assertIn('Mis conteos', content)

    @patch('stock.mobile_views.listar_campanas_para_contador', return_value=[_CAMPANA_ACTIVA])
    @patch('stock.mobile_views.listar_depositos_elegibles', return_value=[
        {'id_deposito': 1, 'nombre': 'Dep A', 'tipo_mpr': 'Terminado'},
    ])
    def test_mis_conteos_movil_oculta_chrome(self, _deps, _campanas):
        from stock.mobile_views import conteo_mis_view

        content = conteo_mis_view(_mobile_request('/stock/conteo/')).content.decode('utf-8')
        self.assertIn("classList.add('conteo-pwa')", content)
        self.assertIn('viewport-fit=cover', content)
        self.assertIn('body.conteo-pwa #status-bar { display: none !important; }', content)
        self.assertIn('Contar', content)


class ListarCampanasParaContadorTests(SimpleTestCase):
    @patch('stock.services.inventario_fisico.listar_campanas')
    def test_filtra_por_contador_y_estado_en_conteo(self, mock_listar):
        from stock.services.inventario_fisico import listar_campanas_para_contador

        mock_listar.return_value = [
            {'id_campana': 1, 'estado': 'EnConteo', 'contadores_json': '[10]'},
            {'id_campana': 2, 'estado': 'EnConteo', 'contadores_json': '[99]'},
            {'id_campana': 3, 'estado': 'Borrador', 'contadores_json': '[10]'},
        ]
        out = listar_campanas_para_contador('base', 10)
        ids = [c['id_campana'] for c in out]
        self.assertEqual(ids, [1])
