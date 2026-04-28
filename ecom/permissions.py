"""
Permisos API e-com / mayoristapp.

Sesión administraNET: misma idea que ReportsLoginRequiredMixin (user en sesión + base_empresa).
"""

from rest_framework.permissions import BasePermission


class EcomMayoristappSessionPermission(BasePermission):
    """
    Usuario autenticado (Synap) y sesión con ``user.base_empresa`` para MySQL legacy.
    No exige ``reports.view_operational``: catálogo base del portal mayorista.
    """

    message = "Se requiere sesión con base_empresa (mayoristapp)."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if getattr(user, "is_superuser", False):
            return True
        session = getattr(request, "session", None)
        if not session:
            return False
        data = session.get("user") or {}
        return bool(data.get("base_empresa"))
