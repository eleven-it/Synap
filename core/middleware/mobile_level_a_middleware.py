"""
Restricción de navegación en dispositivos móviles (PWA / Synap móvil).

Solo se permiten rutas del «Nivel A»: login, perfil, TPV (self_checkout) con
plantillas mobile dedicadas, APIs necesarias para el TPV, PWA y estáticos.

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
    # Command Center gerencial (HTML + fetch JSON; UI responsive).
    '/api/reports/executive-dashboard/',
    '/api/reports/executive-summary/',
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

# Reportes gerenciales con UI móvil (Command Center, catálogo, workspace).
_REPORTS_MOBILE_PAGE_PATTERNS = tuple(
    re.compile(p)
    for p in (
        r'^/reports/dashboard/command-center-gerencial/?$',
        r'^/reports/?$',
        r'^/reports/workspace/?$',
    )
)

# Dashboard principal Synap (tarjetas Command Center / Reports / Workspace).
_CORE_MOBILE_PAGE_PATTERNS = tuple(
    re.compile(p)
    for p in (
        r'^/core/dashboard/?$',
    )
)


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
    for rx in _CORE_MOBILE_PAGE_PATTERNS:
        if rx.match(path):
            return True
    return False


def _mobile_blocked_response(request):
    """403 HTML o JSON según el tipo de petición."""
    accept = (request.headers.get('Accept') or '').lower()
    is_api = request.path.startswith('/api/')
    wants_json = (
        is_api
        or 'application/json' in accept
        or request.headers.get('x-requested-with') == 'XMLHttpRequest'
    )
    if wants_json:
        return JsonResponse(
            {
                'error': (
                    'Esta ruta no está disponible en dispositivos móviles. '
                    'Use Synap desde un ordenador o acceda solo a login, perfil o TPV.'
                )
            },
            status=403,
        )
    # Sin request en render_to_string: evita context processors (BD) en el middleware.
    html = render_to_string('core/mobile_desktop_only.html', {})
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

        if mobile_path_allowed_for_level_a(path):
            return None

        # Panel de administración Django: no forma parte del alcance móvil aprobado.
        if path.startswith('/admin/'):
            return _mobile_blocked_response(request)

        # Dejar pasar anónimos para que @login_required / sesión administraNET redirijan a login.
        user = getattr(request, 'user', None)
        if user is None or not user.is_authenticated:
            return None

        return _mobile_blocked_response(request)
