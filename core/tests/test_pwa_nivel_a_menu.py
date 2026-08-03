"""Tests: filtro de menú PWA / móvil (Nivel A)."""
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from core.middleware.base_middleware import DeviceDetectionMiddleware
from ecom.menu_config import MENU_CONFIG

from core.pwa_nivel_a import (
    PWA_CONTABILIDAD_DEEP_LINKS,
    PWA_CONTABILIDAD_MENU_ITEM_IDS,
    PWA_ECOM_DEEP_LINKS,
    PWA_ECOM_MENU_ITEM_IDS,
    PWA_MENU_APP_IDS,
    PWA_MPR_DEEP_LINKS,
    PWA_MPR_MENU_ITEM_IDS,
    ecom_visible_en_movil,
    filtrar_apps_menu_para_pwa_movil,
    filtrar_submenus_contabilidad_para_pwa_movil,
    filtrar_submenus_ecom_para_pwa_movil,
    filtrar_submenus_mpr_para_pwa_movil,
    mpr_visible_en_movil,
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
    def test_movil_ecom_hub_venta_y_masivo_si_modulo_habilitado(self, _tpv, _ecom):
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
                            {'label': 'Masivo', 'menu_item_id': 'ecom_pedido_masivo'},
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
        self.assertEqual(ids, {'ecom_compra', 'ecom_pedidos', 'ecom_pedido_masivo'})

    @patch('core.pwa_nivel_a.usuario_tiene_mpr_en_menu', return_value=True)
    @patch('core.pwa_nivel_a.usuario_tiene_ecom_en_menu', return_value=False)
    @patch('core.pwa_nivel_a.usuario_tiene_tpv_en_menu', return_value=False)
    def test_movil_mpr_kpis_e_inventario_si_modulo_habilitado(self, _tpv, _ecom, _mpr):
        request = _req(MOBILE_UA)
        apps = [
            {'id': 'reports'},
            {
                'id': 'mpr',
                'submenus': [
                    {
                        'seccion': 'Producción diaria',
                        'items': [
                            {'label': 'Tablero KPIs', 'menu_item_id': 'mpr_prod_kpis'},
                            {'label': 'Inventario', 'menu_item_id': 'mpr_prod_inventario'},
                            {'label': 'Parte', 'menu_item_id': 'mpr_prod_parte'},
                        ],
                    }
                ],
            },
        ]
        out = filtrar_apps_menu_para_pwa_movil(apps, request)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]['id'], 'mpr')
        ids = {i['menu_item_id'] for i in out[0]['submenus'][0]['items']}
        self.assertEqual(ids, {'mpr_prod_kpis', 'mpr_prod_inventario'})

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

    @patch('core.pwa_nivel_a.usuario_tiene_mpr_en_menu', return_value=True)
    def test_sidebar_mpr_con_modulo(self, _mock):
        self.assertTrue(sidebar_visible_en_pwa('mpr'))

    @patch('core.pwa_nivel_a.usuario_tiene_mpr_en_menu', return_value=False)
    def test_sidebar_mpr_sin_modulo(self, _mock):
        self.assertFalse(sidebar_visible_en_pwa('mpr'))

    def test_filtrar_submenus_ecom_solo_hub_venta_masivo(self):
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
                    {'label': 'Masivo', 'menu_item_id': 'ecom_pedido_masivo'},
                ],
            },
        ]
        out = filtrar_submenus_ecom_para_pwa_movil(submenus)
        self.assertEqual(len(out), 2)
        ids = {i['menu_item_id'] for s in out for i in s['items']}
        self.assertEqual(ids, PWA_ECOM_MENU_ITEM_IDS)

    def test_filtrar_submenus_mpr_solo_kpis_e_inventario(self):
        submenus = [
            {
                'seccion': 'Producción diaria',
                'items': [
                    {'label': 'Tablero KPIs', 'menu_item_id': 'mpr_prod_kpis'},
                    {'label': 'Inventario', 'menu_item_id': 'mpr_prod_inventario'},
                    {'label': 'Parte', 'menu_item_id': 'mpr_prod_parte'},
                ],
            },
            {
                'seccion': 'Armado y stock',
                'items': [
                    {'label': 'Armado', 'menu_item_id': 'mpr_op_armado'},
                ],
            },
        ]
        out = filtrar_submenus_mpr_para_pwa_movil(submenus)
        self.assertEqual(len(out), 1)
        ids = {i['menu_item_id'] for s in out for i in s['items']}
        self.assertEqual(ids, PWA_MPR_MENU_ITEM_IDS)

    def test_constantes(self):
        self.assertIn('self_checkout', PWA_MENU_APP_IDS)
        self.assertIn('ecom', PWA_MENU_APP_IDS)
        self.assertIn('mpr', PWA_MENU_APP_IDS)
        self.assertIn('contabilidad', PWA_MENU_APP_IDS)
        # ADR-2: reports NO entra al navbar PWA; acceso vía Command Center / deep-link allowlist.
        self.assertNotIn('reports', PWA_MENU_APP_IDS)
        self.assertEqual(PWA_MPR_MENU_ITEM_IDS, frozenset({'mpr_prod_kpis', 'mpr_prod_inventario'}))
        self.assertEqual(PWA_CONTABILIDAD_MENU_ITEM_IDS, frozenset({'contabilidad_cotizacion_dolar'}))
        self.assertIn('/contabilidad/cotizacion-dolar/', PWA_CONTABILIDAD_DEEP_LINKS)
        self.assertIn('/mpr/', PWA_MPR_DEEP_LINKS)
        self.assertIn('/mpr/inventario/', PWA_MPR_DEEP_LINKS)

    def test_filtrar_submenus_contabilidad_solo_cotizacion(self):
        submenus = [
            {
                'seccion': 'Auditoría',
                'items': [
                    {'menu_item_id': 'contabilidad_auditoria_tablero', 'label': 'Tablero'},
                    {'menu_item_id': 'contabilidad_cotizacion_dolar', 'label': 'Cotización'},
                ],
            },
        ]
        out = filtrar_submenus_contabilidad_para_pwa_movil(submenus)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]['items'][0]['menu_item_id'], 'contabilidad_cotizacion_dolar')

    def test_ecom_compra_deep_link_masivo_simple(self):
        items = [
            c
            for c in MENU_CONFIG[0]["children"]
            if c.get("name") == "ecom_compra"
        ]
        self.assertEqual(len(items), 1)
        compra = items[0]
        self.assertIn("modo=simple", compra["deep_link"])
        self.assertIn("/pedido-masivo-sucursales/", compra["deep_link"])
        self.assertTrue(
            any(
                compra["deep_link"].startswith(dl.rstrip("/"))
                or dl.rstrip("/") in compra["deep_link"]
                for dl in PWA_ECOM_DEEP_LINKS
                if "pedido-masivo-sucursales" in dl
            )
        )


class TpvVisibleEnMovilTests(SimpleTestCase):
    @patch('core.pwa_nivel_a.usuario_tiene_tpv_en_menu', return_value=True)
    def test_alias_tpv_visible(self, _mock):
        self.assertTrue(tpv_visible_en_movil(object(), _req(MOBILE_UA)))


class MprVisibleEnMovilTests(SimpleTestCase):
    @patch('core.pwa_nivel_a.usuario_tiene_mpr_en_menu', return_value=True)
    def test_alias_mpr_visible(self, _mock):
        self.assertTrue(mpr_visible_en_movil(object(), _req(MOBILE_UA)))
