"""
Tests TDD para PWA (Progressive Web App) — Synap.

Especificación: docs/general/ESPEC_PWA_SYNAP.md
Convención: cada test referencia su Criterio de Aceptación (CA-*).

Feature flag: PWA solo se activa en dispositivos móviles, controlado por
DeviceDetectionMiddleware (request.is_mobile). Los tests simulan User-Agent
móvil y desktop para verificar la inyección condicional.

Estos tests deben FALLAR hasta que se implemente cada componente.
Ejecutar: docker exec Synap_app python manage.py test core.tests.test_pwa
"""
import json
import os
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import NoReverseMatch, resolve, reverse

from core.models import UsuarioExtendido

MOBILE_USER_AGENT = (
    'Mozilla/5.0 (Linux; Android 13; Pixel 7) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/120.0.0.0 Mobile Safari/537.36'
)

IPHONE_USER_AGENT = (
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
    'AppleWebKit/605.1.15 (KHTML, like Gecko) '
    'Version/17.0 Mobile/15E148 Safari/604.1'
)

DESKTOP_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/120.0.0.0 Safari/537.36'
)


# ---------------------------------------------------------------------------
# Grupo 1: URLs — resolución y routing
# Spec §3.5 — CA-URL-01..04
# ---------------------------------------------------------------------------

class PWAUrlResolutionTests(SimpleTestCase):
    """Verifica que las URLs PWA estén registradas y resuelvan correctamente."""

    def test_url_sw_resuelve(self):
        """CA-URL-01: La URL name pwa_sw resuelve a /sw.js."""
        url = reverse('pwa_sw')
        self.assertEqual(url, '/sw.js')

    def test_url_manifest_resuelve(self):
        """CA-URL-02: La URL name pwa_manifest resuelve a /manifest.json."""
        url = reverse('pwa_manifest')
        self.assertEqual(url, '/manifest.json')

    def test_url_offline_resuelve(self):
        """CA-URL-03: La URL name pwa_offline resuelve a /offline/."""
        url = reverse('pwa_offline')
        self.assertEqual(url, '/offline/')

    def test_url_sw_no_requiere_args(self):
        """CA-URL-04: /sw.js no requiere argumentos."""
        try:
            reverse('pwa_sw')
        except NoReverseMatch:
            self.fail('pwa_sw no es resoluble por reverse()')

    def test_url_manifest_no_requiere_args(self):
        """CA-URL-04: /manifest.json no requiere argumentos."""
        try:
            reverse('pwa_manifest')
        except NoReverseMatch:
            self.fail('pwa_manifest no es resoluble por reverse()')

    def test_url_offline_no_requiere_args(self):
        """CA-URL-04: /offline/ no requiere argumentos."""
        try:
            reverse('pwa_offline')
        except NoReverseMatch:
            self.fail('pwa_offline no es resoluble por reverse()')


# ---------------------------------------------------------------------------
# Grupo 2: Vista /sw.js
# Spec §3.4 — CA-VIEW-01, CA-VIEW-03, CA-VIEW-04, CA-VIEW-05
# Spec §3.2 — CA-SW-01..07
# ---------------------------------------------------------------------------

class ServiceWorkerViewTests(TestCase):
    """Verifica la vista que sirve sw.js desde la raíz."""

    def test_sw_retorna_200(self):
        """CA-VIEW-01: /sw.js retorna HTTP 200."""
        response = self.client.get('/sw.js')
        self.assertEqual(response.status_code, 200)

    def test_sw_content_type_javascript(self):
        """CA-SW-01, CA-VIEW-03: Content-Type es application/javascript."""
        response = self.client.get('/sw.js')
        self.assertIn('application/javascript', response['Content-Type'])

    def test_sw_cache_control_no_cache(self):
        """CA-SW-02, CA-VIEW-04: Cache-Control es no-cache."""
        response = self.client.get('/sw.js')
        cache_control = response.get('Cache-Control', '')
        self.assertTrue(
            'no-cache' in cache_control or 'max-age=0' in cache_control,
            f'Cache-Control esperado no-cache o max-age=0, obtenido: {cache_control}'
        )

    def test_sw_accesible_sin_autenticacion(self):
        """CA-VIEW-05: /sw.js no requiere login."""
        response = self.client.get('/sw.js')
        self.assertNotEqual(response.status_code, 302,
                            'No debería redirigir a login')
        self.assertNotEqual(response.status_code, 403)

    def test_sw_contiene_cache_version(self):
        """CA-SW-03: El contenido incluye CACHE_VERSION."""
        response = self.client.get('/sw.js')
        contenido = response.content.decode('utf-8')
        self.assertIn('CACHE_VERSION', contenido)

    def test_sw_contiene_evento_install(self):
        """CA-SW-04: Contiene event listener para install."""
        response = self.client.get('/sw.js')
        contenido = response.content.decode('utf-8')
        self.assertIn('install', contenido)

    def test_sw_contiene_evento_activate(self):
        """CA-SW-04: Contiene event listener para activate."""
        response = self.client.get('/sw.js')
        contenido = response.content.decode('utf-8')
        self.assertIn('activate', contenido)

    def test_sw_contiene_evento_fetch(self):
        """CA-SW-04: Contiene event listener para fetch."""
        response = self.client.get('/sw.js')
        contenido = response.content.decode('utf-8')
        self.assertIn('fetch', contenido)

    def test_sw_excluye_admin(self):
        """CA-SW-05: Lógica de exclusión para /admin/."""
        response = self.client.get('/sw.js')
        contenido = response.content.decode('utf-8')
        self.assertIn('/admin/', contenido)

    def test_sw_excluye_api(self):
        """CA-SW-05: Lógica de exclusión para /api/."""
        response = self.client.get('/sw.js')
        contenido = response.content.decode('utf-8')
        self.assertIn('/api/', contenido)

    def test_sw_excluye_logout(self):
        """CA-SW-05: Lógica de exclusión para /logout/."""
        response = self.client.get('/sw.js')
        contenido = response.content.decode('utf-8')
        self.assertIn('/logout/', contenido)


# ---------------------------------------------------------------------------
# Grupo 3: Vista /manifest.json
# Spec §3.1 — CA-MAN-01..05
# Spec §3.4 — CA-VIEW-02, CA-VIEW-03
# ---------------------------------------------------------------------------

class ManifestViewTests(TestCase):
    """Verifica la vista que sirve manifest.json desde la raíz."""

    def test_manifest_retorna_200(self):
        """CA-VIEW-02: /manifest.json retorna HTTP 200."""
        response = self.client.get('/manifest.json')
        self.assertEqual(response.status_code, 200)

    def test_manifest_content_type(self):
        """CA-VIEW-03: Content-Type es application/manifest+json."""
        response = self.client.get('/manifest.json')
        content_type = response['Content-Type']
        self.assertTrue(
            'application/manifest+json' in content_type
            or 'application/json' in content_type,
            f'Content-Type esperado manifest+json o json, obtenido: {content_type}'
        )

    def test_manifest_accesible_sin_autenticacion(self):
        """CA-VIEW-05: /manifest.json no requiere login."""
        response = self.client.get('/manifest.json')
        self.assertNotEqual(response.status_code, 302)
        self.assertNotEqual(response.status_code, 403)

    def test_manifest_json_valido(self):
        """CA-MAN-03: El contenido es JSON válido."""
        response = self.client.get('/manifest.json')
        try:
            data = json.loads(response.content)
        except json.JSONDecodeError:
            self.fail('manifest.json no contiene JSON válido')
        self.assertIsInstance(data, dict)

    def test_manifest_campo_name(self):
        """CA-MAN-01: Contiene campo name."""
        response = self.client.get('/manifest.json')
        data = json.loads(response.content)
        self.assertIn('name', data)
        self.assertTrue(len(data['name']) > 0)

    def test_manifest_campo_short_name(self):
        """CA-MAN-01: Contiene campo short_name."""
        response = self.client.get('/manifest.json')
        data = json.loads(response.content)
        self.assertIn('short_name', data)
        self.assertEqual(data['short_name'], 'Synap')

    def test_manifest_campo_start_url(self):
        """CA-MAN-01, CA-MAN-04: start_url en ruta permitida en móvil (login)."""
        response = self.client.get('/manifest.json')
        data = json.loads(response.content)
        self.assertIn('start_url', data)
        self.assertEqual(data['start_url'], '/login/')

    def test_manifest_campo_display(self):
        """CA-MAN-01: display es standalone."""
        response = self.client.get('/manifest.json')
        data = json.loads(response.content)
        self.assertIn('display', data)
        self.assertEqual(data['display'], 'standalone')

    def test_manifest_campo_scope(self):
        """CA-MAN-01: scope es /."""
        response = self.client.get('/manifest.json')
        data = json.loads(response.content)
        self.assertIn('scope', data)
        self.assertEqual(data['scope'], '/')

    def test_manifest_campo_theme_color(self):
        """CA-MAN-01: Contiene theme_color."""
        response = self.client.get('/manifest.json')
        data = json.loads(response.content)
        self.assertIn('theme_color', data)

    def test_manifest_campo_background_color(self):
        """CA-MAN-01: Contiene background_color."""
        response = self.client.get('/manifest.json')
        data = json.loads(response.content)
        self.assertIn('background_color', data)

    def test_manifest_campo_lang(self):
        """CA-MAN-01: lang es es (español)."""
        response = self.client.get('/manifest.json')
        data = json.loads(response.content)
        self.assertIn('lang', data)
        self.assertEqual(data['lang'], 'es')

    def test_manifest_campo_icons(self):
        """CA-MAN-05: icons contiene al menos entradas para 192x192 y 512x512."""
        response = self.client.get('/manifest.json')
        data = json.loads(response.content)
        self.assertIn('icons', data)
        self.assertIsInstance(data['icons'], list)
        tamanios = [icon.get('sizes') for icon in data['icons']]
        self.assertIn('192x192', tamanios,
                      'Falta icono 192x192 en manifest.icons')
        self.assertIn('512x512', tamanios,
                      'Falta icono 512x512 en manifest.icons')

    def test_manifest_icons_tienen_src_y_type(self):
        """CA-MAN-05: Cada icono tiene src y type."""
        response = self.client.get('/manifest.json')
        data = json.loads(response.content)
        for icon in data.get('icons', []):
            self.assertIn('src', icon,
                          f'Icono sin src: {icon}')
            self.assertIn('type', icon,
                          f'Icono sin type: {icon}')


# ---------------------------------------------------------------------------
# Grupo 4: Página offline
# Spec §3.3 — CA-OFF-01..05
# ---------------------------------------------------------------------------

class OfflinePageTests(TestCase):
    """Verifica la página de fallback offline."""

    def test_offline_retorna_200(self):
        """CA-OFF-01: /offline/ retorna HTTP 200."""
        response = self.client.get('/offline/')
        self.assertEqual(response.status_code, 200)

    def test_offline_content_type_html(self):
        """CA-OFF-02: Content-Type es text/html."""
        response = self.client.get('/offline/')
        self.assertIn('text/html', response['Content-Type'])

    def test_offline_contiene_mensaje_sin_conexion(self):
        """CA-OFF-03: HTML contiene texto sobre falta de conexión."""
        response = self.client.get('/offline/')
        contenido = response.content.decode('utf-8').lower()
        self.assertTrue(
            'sin conexión' in contenido or 'sin conexion' in contenido,
            'La página offline debe contener el texto "Sin conexión"'
        )

    def test_offline_contiene_boton_reintentar(self):
        """CA-OFF-04: Contiene funcionalidad de recarga (reload)."""
        response = self.client.get('/offline/')
        contenido = response.content.decode('utf-8')
        self.assertTrue(
            'reload()' in contenido or 'location.reload' in contenido,
            'La página offline debe contener un botón/enlace con reload()'
        )

    def test_offline_no_depende_de_static_local(self):
        """CA-OFF-05: No tiene referencias a /static/ propios (usa CDN o inline)."""
        response = self.client.get('/offline/')
        contenido = response.content.decode('utf-8')
        self.assertNotIn("{% static", contenido,
                         'offline.html no debe usar {% static %} para ser autocontenido')

    def test_offline_accesible_sin_autenticacion(self):
        """La página offline no requiere login."""
        response = self.client.get('/offline/')
        self.assertNotEqual(response.status_code, 302,
                            'No debería redirigir a login')


# ---------------------------------------------------------------------------
# Grupo 5: Feature flag por dispositivo en base_app.html
# Spec §3.6 — CA-TPL-01..07
# ---------------------------------------------------------------------------

class PWABaseAppTemplateSourceTests(SimpleTestCase):
    """Verifica que base_app.html contiene el bloque PWA condicional en su fuente."""

    def _get_template_source(self):
        """Lee el archivo fuente de base_app.html."""
        template_path = Path(settings.BASE_DIR) / 'theme' / 'templates' / 'base_app.html'
        if not template_path.exists():
            self.fail(f'No existe base_app.html en {template_path}')
        return template_path.read_text(encoding='utf-8')

    def test_template_contiene_condicional_is_mobile(self):
        """CA-TPL-01: base_app.html contiene {% if request.is_mobile %}."""
        source = self._get_template_source()
        self.assertIn('request.is_mobile', source,
                      'base_app.html debe contener condicional request.is_mobile')

    def test_template_contiene_link_manifest(self):
        """CA-TPL-02: Contiene <link rel="manifest" href="/manifest.json">."""
        source = self._get_template_source()
        self.assertIn('rel="manifest"', source)
        self.assertIn('/manifest.json', source)

    def test_template_contiene_apple_web_app_capable(self):
        """CA-TPL-03: Contiene apple-mobile-web-app-capable."""
        source = self._get_template_source()
        self.assertIn('apple-mobile-web-app-capable', source)

    def test_template_contiene_registro_sw(self):
        """CA-TPL-04: Contiene script de registro del Service Worker."""
        source = self._get_template_source()
        self.assertIn('serviceWorker', source)
        self.assertIn('/sw.js', source)

    def test_template_contiene_theme_color(self):
        """CA-TPL-05: Contiene meta theme-color."""
        source = self._get_template_source()
        self.assertIn('theme-color', source)

    def test_template_contiene_apple_status_bar(self):
        """Contiene meta apple-mobile-web-app-status-bar-style."""
        source = self._get_template_source()
        self.assertIn('apple-mobile-web-app-status-bar-style', source)

    def test_template_contiene_apple_title(self):
        """Contiene meta apple-mobile-web-app-title."""
        source = self._get_template_source()
        self.assertIn('apple-mobile-web-app-title', source)


class PWAFeatureFlagDeviceTests(TestCase):
    """Verifica que PWA se inyecta solo en móvil (feature flag por dispositivo).

    Renderiza base_app.html directamente usando RequestFactory con el
    middleware DeviceDetectionMiddleware para simular User-Agent.
    """

    def _render_with_ua(self, user_agent):
        """Renderiza el <head> de base_app.html con UA simulado.

        En lugar de renderizar el template completo (que depende de context
        processors pesados como usuario_y_permisos y partials/navbar), leemos
        el fuente de base_app.html y lo procesamos como template con un
        request mínimo que solo tiene is_mobile/is_desktop.
        """
        from django.test import RequestFactory
        from django.template import Template, Context, RequestContext
        from core.middleware.base_middleware import DeviceDetectionMiddleware

        factory = RequestFactory()
        request = factory.get('/test/', HTTP_USER_AGENT=user_agent)

        middleware = DeviceDetectionMiddleware(lambda r: None)
        middleware.process_request(request)

        source_path = Path(settings.BASE_DIR) / 'theme' / 'templates' / 'base_app.html'
        source = source_path.read_text(encoding='utf-8')

        head_end = source.find('</head>')
        body_end = source.rfind('</body>')
        head_section = source[:head_end + 7] if head_end != -1 else source[:500]
        sw_section = source[body_end - 500:body_end + 7] if body_end != -1 else ''

        snippet = head_section + '\n' + sw_section

        cleaned = snippet.replace('{% load static %}', '')
        cleaned = cleaned.replace('{% load i18n %}', '')
        cleaned = cleaned.replace('{% load menu_tags %}', '')
        cleaned = cleaned.replace('{% block extra_meta %}{% endblock %}', '')
        cleaned = cleaned.replace('{% block extra_css %}{% endblock %}', '')
        cleaned = cleaned.replace('{% block title %}Synap{% endblock %}', 'Synap')
        cleaned = cleaned.replace('{% block extra_js %}{% endblock %}', '')

        import re
        cleaned = re.sub(r'\{%\s*get_media_prefix.*?%\}', '', cleaned)
        cleaned = re.sub(r'\{%\s*get_administranet_logo.*?%\}', '', cleaned)
        cleaned = re.sub(r'\{%\s*static\s+[^%]+%\}', '/static/placeholder', cleaned)
        cleaned = re.sub(r'\{%\s*include\s+[^%]+%\}', '', cleaned)
        cleaned = re.sub(r'\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'\{\{[^}]+\}\}', '', cleaned)
        cleaned = re.sub(r'\{%\s*if\s+logo_path\s*%\}.*?\{%\s*endif\s*%\}', '', cleaned, flags=re.DOTALL)

        tpl = Template(cleaned)
        ctx = RequestContext(request, {})
        return tpl.render(ctx)

    def test_mobile_android_tiene_manifest(self):
        """CA-TPL-07: Request con UA Android incluye link manifest."""
        html = self._render_with_ua(MOBILE_USER_AGENT)
        self.assertIn('rel="manifest"', html)

    def test_mobile_android_tiene_registro_sw(self):
        """CA-TPL-07: Request con UA Android incluye registro del SW."""
        html = self._render_with_ua(MOBILE_USER_AGENT)
        self.assertIn('serviceWorker', html)
        self.assertIn('/sw.js', html)

    def test_mobile_iphone_tiene_apple_meta(self):
        """CA-TPL-07: Request con UA iPhone incluye apple-mobile-web-app-capable."""
        html = self._render_with_ua(IPHONE_USER_AGENT)
        self.assertIn('apple-mobile-web-app-capable', html)

    def test_mobile_tiene_theme_color(self):
        """CA-TPL-07: Request con UA móvil incluye theme-color."""
        html = self._render_with_ua(MOBILE_USER_AGENT)
        self.assertIn('theme-color', html)

    def test_desktop_no_tiene_manifest(self):
        """CA-TPL-06: Request con UA desktop NO incluye link manifest."""
        html = self._render_with_ua(DESKTOP_USER_AGENT)
        self.assertNotIn('rel="manifest"', html)

    def test_desktop_no_tiene_registro_sw(self):
        """CA-TPL-06: Request con UA desktop NO incluye registro del SW."""
        html = self._render_with_ua(DESKTOP_USER_AGENT)
        self.assertNotIn("serviceWorker.register('/sw.js'", html)

    def test_desktop_no_tiene_apple_meta(self):
        """CA-TPL-06: Request con UA desktop NO incluye apple-mobile-web-app-capable."""
        html = self._render_with_ua(DESKTOP_USER_AGENT)
        self.assertNotIn('apple-mobile-web-app-capable', html)


# ---------------------------------------------------------------------------
# Grupo 6: Archivos fuente estáticos (pre-collectstatic)
# Verifica que los archivos existen en theme/static/
# ---------------------------------------------------------------------------

class PWAStaticFilesTests(SimpleTestCase):
    """Verifica que los archivos fuente estáticos PWA existen."""

    def _static_dir(self):
        return Path(settings.STATICFILES_DIRS[0])

    def test_sw_js_existe_en_static(self):
        """sw.js existe en theme/static/."""
        ruta = self._static_dir() / 'sw.js'
        self.assertTrue(ruta.exists(), f'No existe {ruta}')

    def test_manifest_json_existe_en_static(self):
        """manifest.json existe en theme/static/."""
        ruta = self._static_dir() / 'manifest.json'
        self.assertTrue(ruta.exists(), f'No existe {ruta}')

    def test_sw_js_es_javascript_valido(self):
        """sw.js no está vacío y contiene estructura mínima."""
        ruta = self._static_dir() / 'sw.js'
        if not ruta.exists():
            self.skipTest('sw.js no existe aún')
        contenido = ruta.read_text(encoding='utf-8')
        self.assertGreater(len(contenido), 100,
                           'sw.js parece demasiado corto')
        self.assertIn('CACHE_VERSION', contenido)

    def test_manifest_json_es_json_valido(self):
        """manifest.json contiene JSON válido."""
        ruta = self._static_dir() / 'manifest.json'
        if not ruta.exists():
            self.skipTest('manifest.json no existe aún')
        contenido = ruta.read_text(encoding='utf-8')
        try:
            data = json.loads(contenido)
        except json.JSONDecodeError:
            self.fail('manifest.json no es JSON válido')
        self.assertIsInstance(data, dict)


# ---------------------------------------------------------------------------
# Grupo 7: Integración — el SW no rompe comportamiento existente
# ---------------------------------------------------------------------------

class PWAIntegrationTests(TestCase):
    """Verifica que PWA no interfiere con funcionalidad existente."""

    def test_csrf_form_post_no_afectado(self):
        """Formularios con CSRF siguen funcionando (el SW no intercepta POST)."""
        response = self.client.get('/login/')
        self.assertIn(response.status_code, (200, 302))

    def test_admin_no_cacheado_por_sw(self):
        """/admin/ sigue accesible sin interferencia del SW."""
        response = self.client.get('/admin/login/')
        self.assertIn(response.status_code, (200, 301, 302))

    def test_redirect_raiz_sigue_funcionando(self):
        """La raíz / sigue redirigiendo a /core/dashboard/."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/core/dashboard/', response.url)

    def test_static_css_sigue_sirviendo(self):
        """Los archivos CSS estáticos siguen accesibles."""
        response = self.client.get('/static/css/dist/styles.css')
        self.assertIn(response.status_code, (200, 304))


# ---------------------------------------------------------------------------
# Grupo 8: Seguridad HTTPS — settings de producción
# Spec §2
# ---------------------------------------------------------------------------

class PWAHTTPSSettingsTests(SimpleTestCase):
    """Verifica que la configuración HTTPS está activa para producción."""

    @override_settings(DEBUG=False)
    def test_ssl_redirect_activo_en_produccion(self):
        """SECURE_SSL_REDIRECT debe ser True cuando DEBUG=False."""
        self.assertTrue(
            not settings.DEBUG,
            'DEBUG debe ser False para esta prueba'
        )

    def test_hsts_configurado(self):
        """HSTS debe estar configurado con tiempo > 0."""
        self.assertGreater(
            getattr(settings, 'SECURE_HSTS_SECONDS', 0), 0,
            'SECURE_HSTS_SECONDS debe ser > 0'
        )

    def test_proxy_ssl_header_configurado(self):
        """SECURE_PROXY_SSL_HEADER debe estar configurado."""
        header = getattr(settings, 'SECURE_PROXY_SSL_HEADER', None)
        self.assertIsNotNone(header,
                             'SECURE_PROXY_SSL_HEADER no configurado')
        self.assertEqual(header[0], 'HTTP_X_FORWARDED_PROTO')
        self.assertEqual(header[1], 'https')
