"""
Sistema de permisos personalizado para el chat basado en roles de osTicket
"""

import logging
from functools import wraps
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

logger = logging.getLogger(__name__)


def require_osticket_permission(permission):
    """
    Decorador que verifica que el usuario tenga un permiso específico en osTicket
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Verificar autenticación básica
            if not request.user.is_authenticated:
                return JsonResponse({
                    'success': False,
                    'error': 'Usuario no autenticado'
                }, status=401)
            
            # Verificar sesión de osTicket
            osticket_user_id = request.session.get('osticket_user_id')
            if not osticket_user_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Sesión de osTicket no válida'
                }, status=401)
            
            # Obtener permisos del usuario
            user_roles = request.session.get('osticket_roles', {})
            user_permissions = user_roles.get('permissions', [])
            
            # Verificar permiso
            if permission not in user_permissions:
                return JsonResponse({
                    'success': False,
                    'error': f'Permiso requerido: {permission}'
                }, status=403)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_osticket_role(role_type):
    """
    Decorador que verifica que el usuario tenga un rol específico en osTicket
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Verificar autenticación básica
            if not request.user.is_authenticated:
                return JsonResponse({
                    'success': False,
                    'error': 'Usuario no autenticado'
                }, status=401)
            
            # Verificar sesión de osTicket
            osticket_user_id = request.session.get('osticket_user_id')
            if not osticket_user_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Sesión de osTicket no válida'
                }, status=403)
            
            # Obtener rol del usuario
            user_roles = request.session.get('osticket_roles', {})
            user_role_type = user_roles.get('type', 'user')
            
            # Verificar rol
            if user_role_type != role_type:
                return JsonResponse({
                    'success': False,
                    'error': f'Rol requerido: {role_type}'
                }, status=403)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# Permisos específicos del chat
CHAT_PERMISSIONS = {
    'send_message': 'create_ticket',
    'view_history': 'view_own_tickets',
    'create_ticket': 'create_ticket',
    'view_tickets': 'view_own_tickets',
    'admin_chat': 'admin',
    'manage_agents': 'manage_tickets'
}

# Decoradores específicos para el chat
def can_send_message(view_func):
    """Verifica que el usuario pueda enviar mensajes"""
    return require_osticket_permission(CHAT_PERMISSIONS['send_message'])(view_func)

def can_view_history(view_func):
    """Verifica que el usuario pueda ver el historial"""
    return require_osticket_permission(CHAT_PERMISSIONS['view_history'])(view_func)

def can_create_ticket(view_func):
    """Verifica que el usuario pueda crear tickets"""
    return require_osticket_permission(CHAT_PERMISSIONS['create_ticket'])(view_func)

def can_view_tickets(view_func):
    """Verifica que el usuario pueda ver tickets"""
    return require_osticket_permission(CHAT_PERMISSIONS['view_tickets'])(view_func)

def is_admin(view_func):
    """Verifica que el usuario sea administrador"""
    return require_osticket_permission(CHAT_PERMISSIONS['admin_chat'])(view_func)

def is_staff(view_func):
    """Verifica que el usuario sea staff"""
    return require_osticket_role('staff')(view_func)


class ChatPermissionMixin:
    """
    Mixin para vistas basadas en clases que requieren permisos específicos
    """
    
    def dispatch(self, request, *args, **kwargs):
        """Verifica permisos antes de procesar la vista"""
        # Verificar autenticación básica
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Usuario no autenticado'
            }, status=401)
        
        # Verificar sesión de osTicket
        osticket_user_id = request.session.get('osticket_user_id')
        if not osticket_user_id:
            return JsonResponse({
                'success': False,
                'error': 'Sesión de osTicket no válida'
            }, status=403)
        
        # Verificar permisos específicos si están definidos
        if hasattr(self, 'required_permission'):
            user_roles = request.session.get('osticket_roles', {})
            user_permissions = user_roles.get('permissions', [])
            
            if self.required_permission not in user_permissions:
                return JsonResponse({
                    'success': False,
                    'error': f'Permiso requerido: {self.required_permission}'
                }, status=403)
        
        if hasattr(self, 'required_role'):
            user_roles = request.session.get('osticket_roles', {})
            user_role_type = user_roles.get('type', 'user')
            
            if user_role_type != self.required_role:
                return JsonResponse({
                    'success': False,
                    'error': f'Rol requerido: {self.required_role}'
                }, status=403)
        
        return super().dispatch(request, *args, **kwargs)


def get_user_permissions(request):
    """
    Obtiene los permisos del usuario autenticado
    """
    if not request.user.is_authenticated:
        return []
    
    user_roles = request.session.get('osticket_roles', {})
    return user_roles.get('permissions', [])


def has_permission(request, permission):
    """
    Verifica si el usuario tiene un permiso específico
    """
    user_permissions = get_user_permissions(request)
    return permission in user_permissions


def has_role(request, role_type):
    """
    Verifica si el usuario tiene un rol específico
    """
    if not request.user.is_authenticated:
        return False
    
    user_roles = request.session.get('osticket_roles', {})
    return user_roles.get('type') == role_type


# Ejemplo de uso en vistas
def example_protected_view(request):
    """
    Ejemplo de vista protegida con permisos
    """
    if not has_permission(request, 'create_ticket'):
        return JsonResponse({
            'success': False,
            'error': 'No tienes permisos para crear tickets'
        }, status=403)
    
    # Lógica de la vista aquí
    return JsonResponse({'success': True, 'message': 'Vista protegida accedida'})
