"""
Middleware para rutas Self-Checkout.

Regla: sin usuario logueado ni sesión de login abierta no se permite operar en self-checkout.
- Si no hay usuario autenticado o no hay sesión (session['user']), se redirige al login.
- Rutas /self-checkout/* y /api/self-checkout/* quedan protegidas; solo /api/self-checkout/health/ se excluye.
"""
import logging

from django.conf import settings
from django.http import JsonResponse, HttpResponseNotFound
from django.shortcuts import redirect

from .permissions import has_any_self_checkout_permission

logger = logging.getLogger(__name__)

LOGIN_URL = '/login/'


def _api_unauthorized(message: str):
    """Respuesta 401 para API con indicación de redirección al login."""
    return JsonResponse({'error': message, 'redirect': LOGIN_URL}, status=401)


class SelfCheckoutPermissionMiddleware:
    """
    Middleware que protege self-checkout: exige usuario logueado y sesión de login.
    Si no hay sesión abierta, redirige al login. Además exige permiso self_checkout (kiosk/supervisor/admin).
    """
    SCO_PATHS = ('/self-checkout/', '/api/self-checkout/')
    HEALTH_PATH = '/api/self-checkout/health/'

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if not any(path.startswith(p) for p in self.SCO_PATHS):
            return self.get_response(request)

        if not getattr(settings, 'SELF_CHECKOUT_ENABLED', True):
            return HttpResponseNotFound()

        if path.rstrip('/') == self.HEALTH_PATH.rstrip('/'):
            return self.get_response(request)

        # Sin usuario logueado: no permitir operar; redirigir al login
        if not request.user.is_authenticated:
            if path.startswith('/api/'):
                return _api_unauthorized('No autenticado. Redirija al login.')
            return redirect(f'{LOGIN_URL}?next={request.get_full_path()}')

        # Sin sesión de login (session['user']): no permitir operar; redirigir al login
        session_user = request.session.get('user', {})
        if not session_user:
            if path.startswith('/api/'):
                return _api_unauthorized('Sesión inválida o cerrada. Redirija al login.')
            return redirect(LOGIN_URL)

        base_empresa = session_user.get('base_empresa')
        if not base_empresa:
            if path.startswith('/api/'):
                return JsonResponse({
                    'error': 'No hay empresa seleccionada. Redirija al login.',
                    'redirect': LOGIN_URL,
                }, status=401)
            return redirect(LOGIN_URL)

        if has_any_self_checkout_permission(request.user, base_empresa):
            return self.get_response(request)

        if path.startswith('/api/'):
            return JsonResponse({'error': 'Sin permiso para Self-Checkout'}, status=403)
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied('Sin permiso para Self-Checkout')
