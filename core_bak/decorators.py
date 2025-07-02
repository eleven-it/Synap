from functools import wraps
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied

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
