"""Decorators y guards para permisos Self-Checkout (modelo AdministraNET).

Sin usuario logueado o sin sesión de login no se permite operar; las respuestas 401 incluyen
redirect al login para que el frontend redirija.
"""
import logging
from functools import wraps

from django.http import JsonResponse

from .permissions import has_permission

logger = logging.getLogger(__name__)

LOGIN_REDIRECT = '/login/'


def require_self_checkout_permission(permission: str):
    """
    Requiere usuario logueado, sesión (session['user']) y permiso self_checkout.
    Si no hay usuario o sesión, devuelve 401 con redirect al login.
    """
    perm_key = f'self_checkout.{permission}' if '.' not in permission else permission

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({
                    'error': 'No autenticado. Redirija al login.',
                    'redirect': LOGIN_REDIRECT,
                }, status=401)
            session_user = request.session.get('user', {})
            if not session_user:
                return JsonResponse({
                    'error': 'Sesión inválida o cerrada. Redirija al login.',
                    'redirect': LOGIN_REDIRECT,
                }, status=401)
            base_empresa = session_user.get('base_empresa')
            if not base_empresa:
                return JsonResponse({
                    'error': 'No hay empresa seleccionada. Redirija al login.',
                    'redirect': LOGIN_REDIRECT,
                }, status=401)
            if has_permission(request.user, perm_key, base_empresa):
                return view_func(request, *args, **kwargs)
            logger.info(
                'SCO_DENIED perm=%s path=%s user_id=%s',
                perm_key, request.path,
                getattr(request.user, 'id_usuario', getattr(request.user, 'pk', '?'))
            )
            return JsonResponse({'error': 'Sin permiso'}, status=403)
        return _wrapped
    return decorator
