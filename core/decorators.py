from functools import wraps
from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponseForbidden

def permiso_requerido(permiso):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.session.get("user", {})
            permisos = set(user.get("permisos", []))

            if permiso in permisos:
                return view_func(request, *args, **kwargs)

            # 🔒 Si no tiene el permiso, renderizar error 403
            return redirect(reverse("core:error_403"))
        return _wrapped_view
    return decorator

