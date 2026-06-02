"""Tests: filtro de menú PWA / móvil (Nivel A)."""
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from core.middleware.base_middleware import DeviceDetectionMiddleware
from core.pwa_nivel_a import (
    PWA_MENU_APP_IDS,
    filtrar_apps_menu_para_pwa_movil,
    sidebar_visible_en_pwa,
    tpv_visible_en_movil,
)

MOBILE_UA = (
    'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
)
DESKTOP_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)


def _req(ua):
    rf = RequestFactory()
    request = rf.get('/test/', HTTP_USER_AGENT=ua)
    DeviceDetectionMiddleware(lambda r: None).process_request(request)
    return request


class FiltrarAppsMenuPwaTests(SimpleTestCase):
    def test_escritorio_no_reduce_lista(self):
        request = _req(DESKTOP_UA)
        apps = [{'id': 'reports'}, {'id': 'self_checkout'}]
        out = filtrar_apps_menu_para_pwa_movil(apps, request)
        self.assertEqual(len(out), 2)

    @patch('core.pwa_nivel_a.usuario_tiene_tpv_en_menu', return_value=True)
    def test_movil_solo_self_checkout_si_tpv_habilitado(self, _mock):
        request = _req(MOBILE_UA)
        self.assertTrue(getattr(request, 'is_mobile'))
        apps = [{'id': 'reports'}, {'id': 'self_checkout'}]
        out = filtrar_apps_menu_para_pwa_movil(apps, request)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]['id'], 'self_checkout')

    @patch('core.pwa_nivel_a.usuario_tiene_tpv_en_menu', return_value=False)
    def test_movil_sin_tpv_menu_vacio(self, _mock):
        request = _req(MOBILE_UA)
        apps = [{'id': 'self_checkout'}]
        out = filtrar_apps_menu_para_pwa_movil(apps, request)
        self.assertEqual(out, [])

    def test_request_none_no_filtra(self):
        apps = [{'id': 'reports'}]
        out = filtrar_apps_menu_para_pwa_movil(apps, None)
        self.assertEqual(out, apps)


class SidebarPwaTests(SimpleTestCase):
    @patch('core.pwa_nivel_a.usuario_tiene_tpv_en_menu', return_value=True)
    def test_sidebar_self_checkout_con_tpv(self, _mock):
        self.assertTrue(sidebar_visible_en_pwa('self_checkout'))

    @patch('core.pwa_nivel_a.usuario_tiene_tpv_en_menu', return_value=False)
    def test_sidebar_self_checkout_sin_tpv(self, _mock):
        self.assertFalse(sidebar_visible_en_pwa('self_checkout'))

    def test_sidebar_reports_no(self):
        self.assertFalse(sidebar_visible_en_pwa('reports'))

    def test_constantes(self):
        self.assertIn('self_checkout', PWA_MENU_APP_IDS)


class TpvVisibleEnMovilTests(SimpleTestCase):
    @patch('core.pwa_nivel_a.usuario_tiene_tpv_en_menu', return_value=True)
    def test_alias_tpv_visible(self, _mock):
        self.assertTrue(tpv_visible_en_movil(object(), _req(MOBILE_UA)))
