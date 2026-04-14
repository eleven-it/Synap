"""
Permisos DRF: sesión Synap con ``base_empresa`` para operaciones sobre MySQL legacy.
"""

from rest_framework.permissions import BasePermission


class TiendanubeAdministranetSessionPermission(BasePermission):
    """
    Usuario autenticado y sesión con ``user.base_empresa`` (misma idea que ecom mayoristapp).
    """

    message = "Se requiere sesión con base_empresa (AdministraNET)."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if getattr(user, "is_superuser", False):
            return True
        if hasattr(user, "is_admin") and user.is_admin():
            return True
        session = getattr(request, "session", None)
        if not session:
            return False
        data = session.get("user") or {}
        return bool(data.get("base_empresa"))
