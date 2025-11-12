from rest_framework.permissions import BasePermission


class BaseReportsPermission(BasePermission):
    """Base para permisos del módulo."""

    required_permission = ""

    def has_permission(self, request, view):
        """Verifica permisos básicos y autenticación."""
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return False

        if getattr(user, "is_superuser", False):
            return True

        if hasattr(user, "tiene_permiso") and callable(user.tiene_permiso):
            return user.tiene_permiso(self.required_permission)

        if hasattr(user, "get_permisos_totales"):
            permisos = user.get_permisos_totales()
            return "*" in permisos or self.required_permission in permisos

        return False


class OperationalReportsPermission(BaseReportsPermission):
    """Permiso para informes operativos."""

    required_permission = "reports.view_operational"


class ManagerialReportsPermission(BaseReportsPermission):
    """Permiso para informes gerenciales."""

    required_permission = "reports.view_managerial"


