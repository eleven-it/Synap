"""
Permisos API e-com / mayoristapp.

Sesión administraNET: misma idea que ReportsLoginRequiredMixin (user en sesión + base_empresa).
"""

from rest_framework.permissions import BasePermission


def _session_base_empresa(request) -> bool:
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


def _user_has_perm(request, codigo: str) -> bool:
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    if hasattr(user, "tiene_permiso") and user.tiene_permiso("*"):
        return True
    if hasattr(user, "tiene_permiso") and user.tiene_permiso("ecom.*"):
        return True
    if hasattr(user, "tiene_permiso") and user.tiene_permiso(codigo):
        return True
    return False


class EcomMayoristappSessionPermission(BasePermission):
    """
    Usuario autenticado (Synap) y sesión con ``user.base_empresa`` para MySQL legacy.
    Compatibilidad con relays legacy sin permiso de módulo explícito.
    """

    message = "Se requiere sesión con base_empresa (mayoristapp)."

    def has_permission(self, request, view):
        return _session_base_empresa(request)


class EcomModulePermission(BasePermission):
    """Acceso al módulo ecom: sesión mayoristapp + ``ecom.ver``."""

    message = "Se requiere permiso ecom.ver y sesión con base_empresa."

    def has_permission(self, request, view):
        if not _session_base_empresa(request):
            return False
        user = getattr(request, "user", None)
        if getattr(user, "is_superuser", False):
            return True
        return _user_has_perm(request, "ecom.ver")


class EcomComprobantesReadPermission(BasePermission):
    """Listados de comprobantes: ``ecom.comprobantes.ver`` (``base_empresa`` valida la vista)."""

    message = "Se requiere permiso ecom.comprobantes.ver."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if getattr(user, "is_superuser", False):
            return True
        return _user_has_perm(request, "ecom.comprobantes.ver")


class EcomCobranzasReadPermission(BasePermission):
    """Consulta de recibos/cobranzas: ``ecom.cobranzas.ver``."""

    message = "Se requiere permiso ecom.cobranzas.ver."

    def has_permission(self, request, view):
        if not _session_base_empresa(request):
            return False
        user = getattr(request, "user", None)
        if getattr(user, "is_superuser", False):
            return True
        return _user_has_perm(request, "ecom.cobranzas.ver")


class EcomCobranzasWritePermission(BasePermission):
    """Alta de recibos e imputación: ``ecom.cobranzas.editar``."""

    message = "Se requiere permiso ecom.cobranzas.editar."

    def has_permission(self, request, view):
        if not _session_base_empresa(request):
            return False
        user = getattr(request, "user", None)
        if getattr(user, "is_superuser", False):
            return True
        return _user_has_perm(request, "ecom.cobranzas.editar")


class EcomConfigVendedorClienteMarcaPermission(BasePermission):
    """Config territorio Vendedor→Cliente→Marca."""

    message = "Se requiere permiso ecom.config_vendedor_cliente_marca."

    def has_permission(self, request, view):
        if not _session_base_empresa(request):
            return False
        user = getattr(request, "user", None)
        if getattr(user, "is_superuser", False):
            return True
        return _user_has_perm(request, "ecom.config_vendedor_cliente_marca")


class EcomConfigAjustesVentasPermission(BasePermission):
    """Config ajustes de ventas ecom (validación stock en pedidos)."""

    message = "Se requiere permiso ecom.config_ajustes_ventas."

    def has_permission(self, request, view):
        if not _session_base_empresa(request):
            return False
        user = getattr(request, "user", None)
        if getattr(user, "is_superuser", False):
            return True
        return _user_has_perm(request, "ecom.config_ajustes_ventas")


class EcomPedidoMasivoUsarPermission(BasePermission):
    """Matriz de pedido masivo por sucursales."""

    message = "Se requiere permiso ecom.pedido_masivo.usar."

    def has_permission(self, request, view):
        if not _session_base_empresa(request):
            return False
        user = getattr(request, "user", None)
        if getattr(user, "is_superuser", False):
            return True
        return _user_has_perm(request, "ecom.pedido_masivo.usar")


class EcomPedidoCapturaPermission(BasePermission):
    """
    Captura de pedidos (simple o masivo): ``ecom.pedidos.crear`` **o**
    ``ecom.pedido_masivo.usar``. La matriz multi-columna exige además
    ``ecom.pedido_masivo.usar`` (ver ``usuario_puede_matriz_multi_columna``).
    """

    message = "Se requiere permiso ecom.pedidos.crear o ecom.pedido_masivo.usar."

    def has_permission(self, request, view):
        if not _session_base_empresa(request):
            return False
        user = getattr(request, "user", None)
        if getattr(user, "is_superuser", False):
            return True
        return _user_has_perm(request, "ecom.pedidos.crear") or _user_has_perm(
            request, "ecom.pedido_masivo.usar"
        )


def usuario_puede_matriz_multi_columna(request) -> bool:
    """Matriz con más de una sucursal requiere ``ecom.pedido_masivo.usar``."""
    user = getattr(request, "user", None)
    if getattr(user, "is_superuser", False):
        return True
    if not _session_base_empresa(request):
        return False
    return _user_has_perm(request, "ecom.pedido_masivo.usar")


def _permisos_desde_sesion(sess_user: dict) -> set:
    permisos = (sess_user or {}).get("synap_permisos") or (sess_user or {}).get("permisos") or []
    if isinstance(permisos, str):
        permisos = [p.strip() for p in permisos.split(",") if p.strip()]
    return {str(p).strip() for p in permisos if p}


def _tiene_permiso_finance(sess_user: dict, codigo: str) -> bool:
    codigos = _permisos_desde_sesion(sess_user)
    if "*" in codigos:
        return True
    if codigo in codigos:
        return True
    if "finance.*" in codigos:
        return True
    return False


def puede_aprobar_credito(sess_user: dict) -> bool:
    """Cola Finanzas: aprobar/rechazar PED por crédito."""
    return _tiene_permiso_finance(sess_user, "finance.credito.aprobar")


def puede_configurar_credito(sess_user: dict) -> bool:
    """ABM políticas de crédito y plantillas de aviso."""
    return _tiene_permiso_finance(sess_user, "finance.credito.configurar")


class EcomPedidosVerPermission(BasePermission):
    """Hub / listado de pedidos."""

    message = "Se requiere permiso ecom.pedidos.ver."

    def has_permission(self, request, view):
        if not _session_base_empresa(request):
            return False
        user = getattr(request, "user", None)
        if getattr(user, "is_superuser", False):
            return True
        return _user_has_perm(request, "ecom.pedidos.ver")


class EcomJerarquiaEditarPermission(BasePermission):
    """ABM organigrama comercial."""

    message = "Se requiere permiso ecom.jerarquia.editar."

    def has_permission(self, request, view):
        if not _session_base_empresa(request):
            return False
        user = getattr(request, "user", None)
        if getattr(user, "is_superuser", False):
            return True
        return _user_has_perm(request, "ecom.jerarquia.editar")


class EcomPedidosAprobarPermission(BasePermission):
    """Resolver cola de aprobación comercial."""

    message = "Se requiere permiso ecom.pedidos.aprobar."

    def has_permission(self, request, view):
        if not _session_base_empresa(request):
            return False
        user = getattr(request, "user", None)
        if getattr(user, "is_superuser", False):
            return True
        return _user_has_perm(request, "ecom.pedidos.aprobar")
