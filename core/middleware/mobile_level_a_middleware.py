"""
Restricción de navegación en dispositivos móviles (PWA / Synap móvil).

Solo se permiten rutas del «Nivel A»: login, perfil, TPV (self_checkout) con
plantillas mobile dedicadas, APIs necesarias para el TPV, PWA y estáticos,
informes/MPR/dashboard, y pedido simple mayorista (en adaptación móvil).

Usuarios no autenticados: no se bloquea aquí (las vistas redirigen a login).
Usuarios autenticados en móvil en rutas no permitidas: 403 con mensaje claro.
/admin/ se bloquea siempre en móvil.
"""
from __future__ import annotations

import re

from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.utils.deprecation import MiddlewareMixin

# Prefijos permitidos (infraestructura, login completo, PWA).
_MOBILE_ALLOWED_PREFIXES = (
    '/login/',
    '/static/',
    '/media/',
    '/offline/',
    '/set-device-hint/',
    '/mobile/proximamente/',
    '/__/auth/handler',
)

# Rutas exactas (raíz).
_MOBILE_ALLOWED_EXACT = frozenset(
    {
        '/sw.js',
        '/manifest.json',
        '/favicon.ico',
    }
)

# APIs requeridas por el TPV (kiosco, selector, carritos pendientes, pagos MP si el módulo está activo).
_MOBILE_ALLOWED_API_PREFIXES = (
    '/api/self-checkout/',
    '/api/mercadopago/',
    # Módulo de informes (catálogo, dashboards, builder, exportación).
    '/api/reports/',
    # WebAuthn unlock PWA (desbloqueo biométrico post-login).
    '/login/api/webauthn/',
)

# Pantallas HTML self_checkout Nivel A + ticket post-venta (ventana de impresión usada por kiosco.html).
_SELF_CHECKOUT_PAGE_PATTERNS = tuple(
    re.compile(p)
    for p in (
        r'^/self_checkout/?$',
        r'^/self_checkout/kiosco/[^/]+/?$',
        r'^/self_checkout/config/?$',
        r'^/self_checkout/config/carritos-pendientes/?$',
        r'^/self_checkout/talonarios/?$',
        r'^/self_checkout/ticket/\d+/?$',
    )
)

# Catálogo, workspace, dashboards y builder (UI responsive en escritorio + móvil).
_REPORTS_MOBILE_PAGE_PATTERNS = tuple(
    re.compile(p)
    for p in (r'^/reports(?:/.*)?$',)
)

# MPR (enlace «Tablero MPR» desde Command Center).
_MPR_MOBILE_PAGE_PATTERNS = tuple(
    re.compile(p)
    for p in (r'^/mpr(?:/.*)?$',)
)

# Dashboard principal Synap (tarjetas Command Center / Reports / Workspace).
_CORE_MOBILE_PAGE_PATTERNS = tuple(
    re.compile(p)
    for p in (
        r'^/core/dashboard/?$',
    )
)

# Pedido simple + masivo mayorista (UI responsive; acceso móvil Nivel A).
# Pantallas: venta/compra (redirect legacy), hub de pedidos y pedido masivo (modo simple vía ?modo=simple).
# APIs: prefijo /ecom/api/mayoristapp/ (carrito, catálogo, hub, jerarquía, masivo, etc.).
_ECOM_PEDIDO_SIMPLE_PAGE_PATTERNS = tuple(
    re.compile(p)
    for p in (
        r'^/ecom/mayoristapp/venta/?$',
        r'^/ecom/mayoristapp/compra/?$',
        r'^/ecom/mayoristapp/pedidos/?$',
        r'^/ecom/mayoristapp/pedido-masivo-sucursales/?$',
    )
)

# Sub-rutas API mayoristapp explícitas para Nivel A (incluidas en el prefijo global).
_ECOM_MAYORISTAPP_API_NIVEL_A_SUFFIXES = (
    '/pedidos/hub/',
    '/pedidos/hub/archivar-draft/',
    '/jerarquia/nodos/',
    '/jerarquia/usuarios/',
    '/aprobacion/',  # reservado fase aprobación comercial
)

_ECOM_PEDIDO_SIMPLE_API_PREFIX = '/ecom/api/mayoristapp/'


def mobile_path_es_ruta_tpv(path: str) -> bool:
    """True si la ruta es HTML o API del módulo TPV / self_checkout."""
    if path.startswith('/api/self-checkout/') or path.startswith('/api/mercadopago/'):
        return True
    for rx in _SELF_CHECKOUT_PAGE_PATTERNS:
        if rx.match(path):
            return True
    return False


def mobile_path_allowed_for_level_a(path: str) -> bool:
    """True si la ruta puede atenderse en dispositivo móvil."""
    if path in _MOBILE_ALLOWED_EXACT:
        return True
    for prefix in _MOBILE_ALLOWED_PREFIXES:
        if path.startswith(prefix):
            return True
    for prefix in _MOBILE_ALLOWED_API_PREFIXES:
        if path.startswith(prefix):
            return True
    for rx in _SELF_CHECKOUT_PAGE_PATTERNS:
        if rx.match(path):
            return True
    for rx in _REPORTS_MOBILE_PAGE_PATTERNS:
        if rx.match(path):
            return True
    for rx in _MPR_MOBILE_PAGE_PATTERNS:
        if rx.match(path):
            return True
    for rx in _CORE_MOBILE_PAGE_PATTERNS:
        if rx.match(path):
            return True
    if path.startswith(_ECOM_PEDIDO_SIMPLE_API_PREFIX):
        return True
    for rx in _ECOM_PEDIDO_SIMPLE_PAGE_PATTERNS:
        if rx.match(path):
            return True
    return False


def _mobile_blocked_response(request):
    """403 HTML o JSON según el tipo de petición."""
    from core.pwa_nivel_a import tpv_visible_en_movil

    user = getattr(request, 'user', None)
    tpv_visible = tpv_visible_en_movil(user, request) if user else False
    accept = (request.headers.get('Accept') or '').lower()
    is_api = request.path.startswith('/api/')
    wants_json = (
        is_api
        or 'application/json' in accept
        or request.headers.get('x-requested-with') == 'XMLHttpRequest'
    )
    if wants_json:
        mensaje = (
            'Esta ruta no está disponible en dispositivos móviles. '
            'Use Synap desde un ordenador'
        )
        if tpv_visible:
            mensaje += ' o acceda solo a login, perfil o TPV.'
        else:
            mensaje += ' o acceda solo a login o perfil.'
        return JsonResponse({'error': mensaje}, status=403)
    html = render_to_string(
        'core/mobile_desktop_only.html',
        {'tpv_visible_movil': tpv_visible},
    )
    return HttpResponse(html, status=403, content_type='text/html; charset=utf-8')


class MobileLevelAOnlyMiddleware(MiddlewareMixin):
    """
    En móvil, restringe la app autenticada al Nivel A.

    Debe ejecutarse después de DeviceDetectionMiddleware y RequestUserMiddleware.
    """

    def process_request(self, request):
        if not getattr(request, 'is_mobile', False):
            return None

        path = request.path or '/'

        user = getattr(request, 'user', None)
        if mobile_path_es_ruta_tpv(path) and user is not None and user.is_authenticated:
            from core.pwa_nivel_a import tpv_visible_en_movil

            if not tpv_visible_en_movil(user, request):
                return _mobile_blocked_response(request)

        if mobile_path_allowed_for_level_a(path):
            return None

        # Panel de administración Django: no forma parte del alcance móvil aprobado.
        if path.startswith('/admin/'):
            return _mobile_blocked_response(request)

        # Dejar pasar anónimos para que @login_required / sesión administraNET redirijan a login.
        if user is None or not user.is_authenticated:
            return None

        return _mobile_blocked_response(request)
