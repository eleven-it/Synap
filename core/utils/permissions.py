"""
Utilidades de permisos para el sistema core
"""

from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from core.decorators import tiene_permiso


def user_has_full_access(user) -> bool:
    """
    Define el criterio canónico de acceso total en Synap.

    Regla de negocio vigente:
    - superuser Django => acceso total
    - user.is_admin() => acceso total
    - cod_usuario == 'supervisor' => acceso total
    """
    if not user:
        return False
    if getattr(user, "is_superuser", False):
        return True
    if hasattr(user, "is_admin") and callable(user.is_admin) and user.is_admin():
        return True
    cod_usuario = getattr(user, "cod_usuario", "") or ""
    return cod_usuario.lower() == "supervisor"


def get_user_permission_set(user):
    """Obtiene permisos efectivos, forzando '*' para usuarios con acceso total."""
    if user_has_full_access(user):
        return {"*"}
    if hasattr(user, "get_permisos_totales"):
        try:
            return set(user.get_permisos_totales())
        except Exception:
            return set()
    return set()


class CorePermissionRequiredMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """
    Mixin personalizado para verificación de permisos del core
    Extiende PermissionRequiredMixin con funcionalidades específicas del sistema
    """
    
    def dispatch(self, request, *args, **kwargs):
        """Verifica permisos antes de procesar la vista"""
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Verificar si el usuario tiene rol administrador (acceso total)
        if user_has_full_access(request.user):
            return super().dispatch(request, *args, **kwargs)
        
        # Verificar permisos específicos
        if hasattr(self, 'permission_required'):
            if isinstance(self.permission_required, str):
                permissions = [self.permission_required]
            else:
                permissions = self.permission_required
            
            for permission in permissions:
                if hasattr(request.user, 'tiene_permiso') and request.user.tiene_permiso(permission):
                    return super().dispatch(request, *args, **kwargs)
        
        # Si no tiene permisos, mostrar error
        messages.error(request, _("No tienes permisos para acceder a esta página."))
        raise PermissionDenied
    
    def handle_no_permission(self):
        """Maneja el caso cuando el usuario no tiene permisos"""
        messages.error(self.request, _("Debes iniciar sesión para acceder a esta página."))
        return redirect('login:login')


class CoreModulePermissionMixin(CorePermissionRequiredMixin):
    """
    Mixin para verificar permisos de módulos específicos
    """
    
    module_permission = None
    
    def dispatch(self, request, *args, **kwargs):
        """Verifica permisos del módulo antes de procesar la vista"""
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Verificar si el usuario tiene rol administrador (acceso total)
        if user_has_full_access(request.user):
            return super().dispatch(request, *args, **kwargs)
        
        # Verificar permisos del módulo
        if self.module_permission:
            if hasattr(request.user, 'tiene_permiso_modulo') and request.user.tiene_permiso_modulo(self.module_permission):
                return super().dispatch(request, *args, **kwargs)
        
        # Si no tiene permisos, mostrar error
        messages.error(request, _("No tienes permisos para acceder al módulo {module}.").format(
            module=self.module_permission or 'solicitado'
        ))
        raise PermissionDenied


def require_core_permission(permission_code):
    """
    Decorador para verificar permisos del core en vistas basadas en funciones
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, _("Debes iniciar sesión para acceder a esta página."))
                return redirect('login:login')
            
            # Verificar si el usuario tiene rol administrador (acceso total)
            if hasattr(request.user, 'is_admin') and request.user.is_admin():
                return view_func(request, *args, **kwargs)
            
            # Verificar permiso específico
            if hasattr(request.user, 'tiene_permiso') and request.user.tiene_permiso(permission_code):
                return view_func(request, *args, **kwargs)
            
            # Si no tiene permisos, mostrar error
            messages.error(request, _("No tienes permisos para acceder a esta página."))
            raise PermissionDenied
        
        return wrapper
    return decorator 