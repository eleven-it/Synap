from functools import wraps
from django.shortcuts import render
from django.http import HttpResponseForbidden

def tiene_permiso(codigo_permiso):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = getattr(request, "user", None)

            if not user or not getattr(user, "is_authenticated", False):
                return render(request, "core/403.html", status=403)

            if hasattr(user, "tiene_permiso") and user.tiene_permiso(codigo_permiso):
                return view_func(request, *args, **kwargs)

            return render(request, "core/403.html", status=403)

        return _wrapped_view
    return decorator


def permiso_requerido(permiso):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.session.get("user", {})
            permisos = set(user.get("permisos", []))

            if permiso in permisos:
                return view_func(request, *args, **kwargs)

            return render(request, "core/403.html", status=403)
        return _wrapped_view
    return decorator
