"""
Permisos alineados a docs/compras/product_requirements.md §10.
"""

from __future__ import annotations

from rest_framework.permissions import BasePermission

from factura_compra_captura.permisos_modulo import usuario_puede_crear_expediente_desde_captura


def _perm(user, codename: str) -> bool:
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    return user.has_perm(f"factura_compra_captura.{codename}")


class ExpedienteListCreatePermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if getattr(request.user, "is_superuser", False):
            return True
        if request.method == "GET":
            return _perm(request.user, "ver") or request.user.has_perm("compras.ver")
        if request.method == "POST":
            return usuario_puede_crear_expediente_desde_captura(request.user)
        return False


class ExpedienteDetailPatchPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if getattr(request.user, "is_superuser", False):
            return True
        if request.method == "GET":
            return _perm(request.user, "ver") or request.user.has_perm("compras.ver")
        if request.method == "PATCH":
            return _perm(request.user, "editar")
        return False


class ExpedienteTransicionPermission(BasePermission):
    """Según acción del cuerpo JSON."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if getattr(request.user, "is_superuser", False):
            return True
        accion = (request.data.get("accion") or "").strip()
        if accion == "rechazar":
            return _perm(request.user, "rechazar")
        if accion == "simular_posting_exitoso":
            return _perm(request.user, "aprobar")
        return _perm(request.user, "revisar")


class ExpedienteAprobarPermission(BasePermission):
    def has_permission(self, request, view):
        return _perm(request.user, "aprobar")


class ExpedienteEventosPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if getattr(request.user, "is_superuser", False):
            return True
        return _perm(request.user, "ver") or request.user.has_perm("compras.ver")


class DocumentoExpedientePermission(BasePermission):
    """Adjuntos: lectura con ver compras/captura; alta en flujo de captura; reintento OCR acotado."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if getattr(request.user, "is_superuser", False):
            return True
        if request.method == "GET":
            return _perm(request.user, "ver") or request.user.has_perm("compras.ver")
        view_name = getattr(view, "__class__", type).__name__
        if view_name == "DocumentoFuenteReintentarOcrAPIView":
            return _perm(request.user, "editar") or _perm(
                request.user, "reintentar_posting"
            )
        if request.method == "POST":
            return (
                _perm(request.user, "editar")
                or _perm(request.user, "crear")
                or request.user.has_perm("compras.ver")
            )
        return _perm(request.user, "editar")


class ExpedienteResolverProveedorPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if getattr(request.user, "is_superuser", False):
            return True
        return _perm(request.user, "editar")
