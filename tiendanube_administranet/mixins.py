"""
Mixins de sesión para la integración Tienda Nube ↔ AdministraNET (mismo criterio que Reportes).
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect


class TiendanubeAdministranetLoginMixin(LoginRequiredMixin):
    """
    Requiere sesión administraNET (clave ``user`` en sesión) y usuario autenticado.
    """

    def dispatch(self, request, *args, **kwargs):
        if "user" not in request.session:
            return redirect("login:login")
        if not getattr(request.user, "is_authenticated", False):
            return redirect("login:login")
        return super().dispatch(request, *args, **kwargs)
