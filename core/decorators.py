from functools import wraps
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied


def _cod_usuario_es_supervisor(user) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    cod = (getattr(user, "cod_usuario", None) or "").strip().lower()
    return cod == "supervisor"


def solo_usuario_supervisor(view_func):
    """
    Solo permite acceso al usuario administraNET con cod_usuario ``supervisor``.
    No equivale al rol "Supervisor" ni a is_superuser de Django.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return redirect("login:login")
        if not _cod_usuario_es_supervisor(user):
            raise PermissionDenied(
                "Solo el usuario supervisor puede usar esta función."
            )
        return view_func(request, *args, **kwargs)

    return _wrapped_view

def administranet_login_required(view_func):
    """
    Decorador para verificar que el usuario esté autenticado mediante sesión de administraNET
    Reemplaza @login_required de Django que verifica request.user.is_authenticated
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Verificar sesión personalizada de administraNET
        if "user" not in request.session:
            return redirect("login:login")
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def tiene_permiso(codigo_permiso):
    """
    Verifica si el usuario tiene un permiso específico.
    Si alguno de sus roles es 'Administrador', se le concede acceso total automáticamente.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = getattr(request, 'user', None)

            if not user or not getattr(user, "is_authenticated", False):
                return redirect("login:login")

            # ✅ Acceso total si es supervisor de administraNET o tiene rol "Administrador"
            if hasattr(user, "is_admin") and user.is_admin():
                return view_func(request, *args, **kwargs)
            
            # ✅ Acceso total si es supervisor (verificación adicional)
            if hasattr(user, "cod_usuario"):
                cod_usuario_lower = (user.cod_usuario or '').lower()
                if cod_usuario_lower == 'supervisor':
                    return view_func(request, *args, **kwargs)
            
            # ✅ Acceso total si algún rol es "Administrador"
            if hasattr(user, "roles"):
                if any(rol.nombre.lower() == "administrador" for rol in user.roles.all()):
                    return view_func(request, *args, **kwargs)

            # 🔐 Evaluar permiso individual
            if hasattr(user, "tiene_permiso") and user.tiene_permiso(codigo_permiso):
                return view_func(request, *args, **kwargs)

            raise PermissionDenied
        return _wrapped_view
    return decorator
