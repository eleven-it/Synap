"""Tests: filtro de menú PWA / móvil (Nivel A)."""
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from core.middleware.base_middleware import DeviceDetectionMiddleware
from core.pwa_nivel_a import (
    PWA_ECOM_MENU_ITEM_IDS,
    PWA_MENU_APP_IDS,
    ecom_visible_en_movil,
    filtrar_apps_menu_para_pwa_movil,
    filtrar_submenus_ecom_para_pwa_movil,
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

    @patch('core.pwa_nivel_a.usuario_tiene_ecom_en_menu', return_value=True)
    @patch('core.pwa_nivel_a.usuario_tiene_tpv_en_menu', return_value=False)
    def test_movil_ecom_hub_y_venta_si_modulo_habilitado(self, _tpv, _ecom):
        request = _req(MOBILE_UA)
        apps = [
            {'id': 'reports'},
            {
                'id': 'ecom',
                'submenus': [
                    {
                        'seccion': 'Portal',
                        'items': [
                            {'label': 'Venta', 'menu_item_id': 'ecom_compra'},
                            {'label': 'Pedidos', 'menu_item_id': 'ecom_pedidos'},
                            {'label': 'Clientes', 'menu_item_id': 'ecom_clientes'},
                        ],
                    }
                ],
            },
        ]
        out = filtrar_apps_menu_para_pwa_movil(apps, request)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]['id'], 'ecom')
        ids = {i['menu_item_id'] for i in out[0]['submenus'][0]['items']}
        self.assertEqual(ids, {'ecom_compra', 'ecom_pedidos'})

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

    @patch('core.pwa_nivel_a.usuario_tiene_ecom_en_menu', return_value=True)
    def test_sidebar_ecom_con_modulo(self, _mock):
        self.assertTrue(sidebar_visible_en_pwa('ecom'))

    @patch('core.pwa_nivel_a.usuario_tiene_ecom_en_menu', return_value=False)
    def test_sidebar_ecom_sin_modulo(self, _mock):
        self.assertFalse(sidebar_visible_en_pwa('ecom'))

    def test_filtrar_submenus_ecom_solo_hub_venta(self):
        submenus = [
            {
                'seccion': 'Portal',
                'items': [
                    {'label': 'Venta', 'menu_item_id': 'ecom_compra'},
                    {'label': 'Clientes', 'menu_item_id': 'ecom_clientes'},
                ],
            },
            {
                'seccion': 'Comprobantes',
                'items': [
                    {'label': 'Pedidos', 'menu_item_id': 'ecom_pedidos'},
                ],
            },
        ]
        out = filtrar_submenus_ecom_para_pwa_movil(submenus)
        self.assertEqual(len(out), 2)
        ids = {i['menu_item_id'] for s in out for i in s['items']}
        self.assertEqual(ids, PWA_ECOM_MENU_ITEM_IDS)

    def test_constantes(self):
        self.assertIn('self_checkout', PWA_MENU_APP_IDS)
        self.assertIn('ecom', PWA_MENU_APP_IDS)


class TpvVisibleEnMovilTests(SimpleTestCase):
    @patch('core.pwa_nivel_a.usuario_tiene_tpv_en_menu', return_value=True)
    def test_alias_tpv_visible(self, _mock):
        self.assertTrue(tpv_visible_en_movil(object(), _req(MOBILE_UA)))
