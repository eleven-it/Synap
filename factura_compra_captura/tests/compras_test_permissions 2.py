"""Helpers de permisos para tests API compras (product_requirements §10)."""

from __future__ import annotations

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from factura_compra_captura.models import ExpedienteFacturaCompra

_CODENAMES_COMPLETOS = (
    "crear",
    "ver",
    "editar",
    "revisar",
    "aprobar",
    "rechazar",
    "reintentar_posting",
)


def otorgar_permisos_compras(user, *, excluir: frozenset[str] | None = None) -> None:
    excluir = excluir or frozenset()
    ct = ContentType.objects.get_for_model(ExpedienteFacturaCompra)
    for cn in _CODENAMES_COMPLETOS:
        if cn in excluir:
            continue
        p = Permission.objects.get(content_type=ct, codename=cn)
        user.user_permissions.add(p)
    if hasattr(user, "_perm_cache"):
        user._perm_cache = {}
