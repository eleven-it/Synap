"""
Tests: restricción móvil «solo Nivel A» (MobileLevelAOnlyMiddleware).

Ejecutar: docker exec Synap_app python manage.py test core.tests.test_mobile_level_a_middleware
"""
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
DESKTOP_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)


def _session_middleware():
    return SessionMiddleware(lambda req: HttpResponse())


def _build_request(method, path, ua, session_user=None, accept_json=False):
    rf = RequestFactory()
    extra = {'HTTP_USER_AGENT': ua}
    if accept_json:
        extra['HTTP_ACCEPT'] = 'application/json'
    if method.upper() == 'GET':
        request = rf.get(path, **extra)
    else:
        request = rf.post(path, **extra)
    _session_middleware().process_request(request)
    if session_user is not None:
        request.session['user'] = session_user
        request.session.save()
    else:
        request.session.save()
    DeviceDetectionMiddleware(lambda r: None).process_request(request)
    from core.middleware.base_middleware import get_usuario_extendiendo_desde_sesion

    request.user = get_usuario_extendiendo_desde_sesion(request)
    return request


def _minimal_session_user():
    return {
        'id_usuario': 1,
        'cod_usuario': 'moviltest',
        'nombre_usuario': 'M',
        'apellido_usuario': 'Test',
        'nombre_completo': 'M Test',
        'id_empresa': 1,
        'id_sucursal': 1,
        'id_puesto': 1,
        'base_empresa': 'test_base',
    }


class MobilePathAllowedUnitTests(SimpleTestCase):
    def test_self_checkout_index_y_kiosco(self):
        self.assertTrue(mobile_path_allowed_for_level_a('/self_checkout/'))
        self.assertTrue(mobile_path_allowed_for_level_a('/self_checkout/kiosco/K1/'))

    def test_self_checkout_config_y_carritos(self):
        self.assertTrue(mobile_path_allowed_for_level_a('/self_checkout/config/'))
        self.assertTrue(mobile_path_allowed_for_level_a('/self_checkout/config/carritos-pendientes/'))

    def test_self_checkout_talonarios_lista(self):
        self.assertTrue(mobile_path_allowed_for_level_a('/self_checkout/talonarios/'))

    def test_self_checkout_ticket_impresion(self):
        self.assertTrue(mobile_path_allowed_for_level_a('/self_checkout/ticket/99/'))

    def test_self_checkout_formularios_no_permitidos(self):
        self.assertFalse(mobile_path_allowed_for_level_a('/self_checkout/config/nuevo/'))
        self.assertFalse(mobile_path_allowed_for_level_a('/self_checkout/config/K1/editar/'))
        self.assertFalse(mobile_path_allowed_for_level_a('/self_checkout/talonarios/nuevo-pv/'))
        self.assertFalse(mobile_path_allowed_for_level_a('/self_checkout/talonarios/agregar/'))
        self.assertFalse(mobile_path_allowed_for_level_a('/self_checkout/talonarios/1/FA/editar/'))

    def test_api_self_checkout_prefijo(self):
        self.assertTrue(mobile_path_allowed_for_level_a('/api/self-checkout/health/'))

    def test_core_dashboard_permitido(self):
        self.assertTrue(mobile_path_allowed_for_level_a('/core/dashboard/'))

    def test_reports_catalog_y_workspace_permitidos(self):
        self.assertTrue(mobile_path_allowed_for_level_a('/reports/'))
        self.assertTrue(mobile_path_allowed_for_level_a('/reports/workspace/'))

    def test_command_center_gerencial_permitido(self):
        self.assertTrue(
            mobile_path_allowed_for_level_a('/reports/dashboard/command-center-gerencial/')
        )

    def test_resumen_ejecutivo_ventas_permitido(self):
        self.assertTrue(
            mobile_path_allowed_for_level_a('/reports/dashboard/resumen-ejecutivo-ventas/')
        )

    def test_api_pv_canal_ejecutivo_permitido(self):
        self.assertTrue(mobile_path_allowed_for_level_a('/api/reports/pv-canal-ejecutivo/'))

    def test_api_executive_dashboard_permitido(self):
        self.assertTrue(
            mobile_path_allowed_for_level_a('/api/reports/executive-dashboard/')
        )
        self.assertTrue(
            mobile_path_allowed_for_level_a(
                '/api/reports/executive-dashboard/ventas/resumen/'
            )
        )

    def test_api_executive_summary_permitido(self):
        self.assertTrue(mobile_path_allowed_for_level_a('/api/reports/executive-summary/'))

    def test_cash_flow_waterfall_permitido(self):
        self.assertTrue(
            mobile_path_allowed_for_level_a('/reports/dashboard/cash_flow_waterfall/')
        )

    def test_api_reports_query_permitido(self):
        self.assertTrue(mobile_path_allowed_for_level_a('/api/reports/query/'))

    def test_mpr_tablero_permitido(self):
        self.assertTrue(mobile_path_allowed_for_level_a('/mpr/'))
        self.assertTrue(mobile_path_allowed_for_level_a('/mpr/opt/list/'))


@override_settings(
    SESSION_ENGINE='django.contrib.sessions.backends.cache',
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'mobile-level-a-tests',
        }
    },
)
class MobileLevelAMiddlewareRequestTests(SimpleTestCase):
    """Pruebas sin BD usando RequestFactory."""

    def setUp(self):
        self.mw = MobileLevelAOnlyMiddleware(lambda r: None)

    def test_movil_autenticado_dashboard_sin_bloqueo(self):
        req = _build_request('GET', '/core/dashboard/', MOBILE_UA, _minimal_session_user())
        resp = self.mw.process_request(req)
        self.assertIsNone(resp)

    def test_movil_anonimo_dashboard_sin_bloqueo_middleware(self):
        req = _build_request('GET', '/core/dashboard/', MOBILE_UA, None)
        resp = self.mw.process_request(req)
        self.assertIsNone(resp)

    def test_escritorio_autenticado_dashboard_sin_bloqueo(self):
        req = _build_request('GET', '/core/dashboard/', DESKTOP_UA, _minimal_session_user())
        resp = self.mw.process_request(req)
        self.assertIsNone(resp)

    def test_movil_autenticado_login_perfil_sin_bloqueo(self):
        req = _build_request('GET', '/login/perfil/', MOBILE_UA, _minimal_session_user())
        resp = self.mw.process_request(req)
        self.assertIsNone(resp)

    def test_movil_api_reports_catalog_sin_bloqueo(self):
        req = _build_request(
            'GET',
            '/api/reports/catalog/',
            MOBILE_UA,
            _minimal_session_user(),
            accept_json=True,
        )
        resp = self.mw.process_request(req)
        self.assertIsNone(resp)

    def test_movil_dashboard_informe_legacy_sin_bloqueo(self):
        self.assertTrue(
            mobile_path_allowed_for_level_a('/reports/dashboard/ventas_netas/')
        )
        req = _build_request(
            'GET',
            '/reports/dashboard/pedidos-pendientes/',
            MOBILE_UA,
            _minimal_session_user(),
        )
        resp = self.mw.process_request(req)
        self.assertIsNone(resp)

    def test_movil_reports_builder_sin_bloqueo(self):
        self.assertTrue(mobile_path_allowed_for_level_a('/reports/builder/'))
        self.assertTrue(mobile_path_allowed_for_level_a('/reports/builder/data-map/'))

    def test_movil_autenticado_command_center_sin_bloqueo(self):
        req = _build_request(
            'GET',
            '/reports/dashboard/command-center-gerencial/',
            MOBILE_UA,
            _minimal_session_user(),
        )
        resp = self.mw.process_request(req)
        self.assertIsNone(resp)

    def test_movil_autenticado_executive_dashboard_api_sin_bloqueo(self):
        req = _build_request(
            'GET',
            '/api/reports/executive-dashboard/',
            MOBILE_UA,
            _minimal_session_user(),
            accept_json=True,
        )
        resp = self.mw.process_request(req)
        self.assertIsNone(resp)

    def test_movil_autenticado_resumen_ejecutivo_ventas_sin_bloqueo(self):
        req = _build_request(
            'GET',
            '/reports/dashboard/resumen-ejecutivo-ventas/',
            MOBILE_UA,
            _minimal_session_user(),
        )
        resp = self.mw.process_request(req)
        self.assertIsNone(resp)

    def test_movil_admin_siempre_403_aunque_anonimo(self):
        req = _build_request('GET', '/admin/login/', MOBILE_UA, None)
        # Sin usuario en sesión, /admin/ sigue bloqueado
        resp = self.mw.process_request(req)
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status_code, 403)
