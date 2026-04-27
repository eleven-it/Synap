"""
Criterios compartidos para acceso al flujo de captura de factura de compra (web y API).

Debe coincidir con el menú Synap (Stock / Compras → captura y expedientes): ``compras.ver``
o permisos del modelo ``ExpedienteFacturaCompra`` según la acción.
"""

from __future__ import annotations


def usuario_puede_acceder_modulo_captura(user) -> bool:
    """Listado web, pantalla de captura móvil y lecturas API al mismo nivel que el menú."""
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    return user.has_perm("compras.ver") or user.has_perm("factura_compra_captura.ver")


def usuario_puede_crear_expediente_desde_captura(user) -> bool:
    """POST de alta de expediente: rol captura dedicado o acceso compras con captura en menú."""
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    if user.has_perm("factura_compra_captura.crear"):
        return True
    if user.has_perm("compras.ver"):
        return True
    return False
