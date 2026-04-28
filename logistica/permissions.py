"""Permisos REST — módulo Logística."""

from rest_framework.permissions import BasePermission


class LogisticaEntregasPermission(BasePermission):
    """
    Sesión AdministraNET con ``base_empresa`` y permiso ``logistica_editar_entregas``
    (o comodín ``logistica.*`` vía ``tiene_permiso``).
    """

    message = "Se requiere permiso para operar entregas (logistica_editar_entregas) y empresa con base de datos."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return False
        session = getattr(request, "session", None)
        if not session:
            return False
        data = session.get("user") or {}
        if not data.get("base_empresa"):
            return False
        if getattr(user, "is_superuser", False):
            return True
        if hasattr(user, "is_admin") and callable(user.is_admin) and user.is_admin():
            return True
        if hasattr(user, "tiene_permiso") and callable(user.tiene_permiso):
            return user.tiene_permiso("logistica_editar_entregas")
        return False
