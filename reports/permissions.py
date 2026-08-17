from rest_framework.permissions import BasePermission

INVENTARIO_DEPOSITO_SLUG = "inventario-deposito-articulo"
# Slugs MPR en catálogo Reportes con acceso OR mpr.reportes / mpr.ver.
MPR_CATALOG_OR_PERMISSION_SLUGS = frozenset({INVENTARIO_DEPOSITO_SLUG})


def _user_has_permission_code(user, code: str) -> bool:
    """Evalúa un permiso Synap (superuser, comodín o tiene_permiso)."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    if hasattr(user, "tiene_permiso") and callable(user.tiene_permiso):
        return user.tiene_permiso(code)
    if hasattr(user, "get_permisos_totales"):
        permisos = user.get_permisos_totales()
        return "*" in permisos or code in permisos
    return False


def user_has_mpr_reportes(user) -> bool:
    """True si el usuario puede ver reportes MPR (mpr.reportes o mpr.ver)."""
    return _user_has_permission_code(user, "mpr.reportes") or _user_has_permission_code(
        user, "mpr.ver"
    )


def user_can_access_inventario_deposito(user) -> bool:
    """
    Acceso al informe inventario-deposito-articulo:
    reports.view_operational, mpr.reportes o mpr.ver.
    """
    if _user_has_permission_code(user, "reports.view_operational"):
        return True
    return user_has_mpr_reportes(user)


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


class DabraConsolidadoRemitosPermission(BaseReportsPermission):
    """Permiso dedicado al informe DABRA consolidado remitos."""

    required_permission = "reports.dabra_consolidado_remitos"


class BuilderReportsPermission(BaseReportsPermission):
    """Permiso para usar el Report Builder."""

    required_permission = "reports.builder"

    def has_permission(self, request, view):
        return super().has_permission(request, view)


class InventarioDepositoCatalogPermission(BasePermission):
    """
    Puerta de API para query/export: operativo/gerencial Reportes, o MPR
    solo cuando el slug del body es inventario-deposito-articulo.
    """

    def has_permission(self, request, view):
        if OperationalReportsPermission().has_permission(request, view):
            return True
        if ManagerialReportsPermission().has_permission(request, view):
            return True
        slug = None
        data = getattr(request, "data", None)
        if isinstance(data, dict):
            slug = data.get("slug")
        if slug in MPR_CATALOG_OR_PERMISSION_SLUGS:
            return user_has_mpr_reportes(getattr(request, "user", None))
        return False
