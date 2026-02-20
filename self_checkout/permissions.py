"""
Permisos Self-Checkout según AdministraNET (MySQL).
Delega en core.services.administranet_permisos_usuario (única fuente).
"""
import logging
from typing import Any

from core.constantes_permisos import SCO_KIOSK, SCO_SUPERVISOR, SCO_ADMIN, SCO_PERMISSIONS
from core.services.administranet_permisos_usuario import get_permisos_totales_administranet

logger = logging.getLogger(__name__)

# Jerarquía: admin implica supervisor y kiosk; supervisor implica kiosk
SCO_HIERARCHY = {
    SCO_KIOSK: [SCO_SUPERVISOR, SCO_ADMIN],
    SCO_SUPERVISOR: [SCO_ADMIN],
    SCO_ADMIN: [],
}


def has_permission(
    user: Any,
    perm_key: str,
    base_empresa: str,
) -> bool:
    """
    Verifica si el usuario tiene el permiso en AdministraNET.
    Usuario supervisor (cod_usuario) tiene todos los permisos.
    Para Self-Checkout se considera la jerarquía kiosk < supervisor < admin.
    """
    if not user:
        return False

    if hasattr(user, "is_admin") and callable(user.is_admin) and user.is_admin():
        return True

    id_puesto = getattr(user, "id_puesto", None) if not isinstance(user, dict) else user.get("id_puesto")
    cod_usuario = getattr(user, "cod_usuario", None) if not isinstance(user, dict) else user.get("cod_usuario")
    nombre_puesto = getattr(user, "nombre_puesto", None) if not isinstance(user, dict) else user.get("nombre_puesto")

    if not id_puesto or not base_empresa:
        return False

    permisos = get_permisos_totales_administranet(
        base_empresa=base_empresa,
        id_puesto=id_puesto,
        cod_usuario=cod_usuario,
        nombre_puesto=nombre_puesto,
    )

    if "*" in permisos:
        return True

    perms_to_check = [perm_key] + SCO_HIERARCHY.get(perm_key, [])
    return any(p in permisos for p in perms_to_check)


def has_sc_permission(user: Any, perm_code: str, base_empresa: str) -> bool:
    """
    Alias de has_permission para permisos Self-Checkout.
    perm_code: 'kiosk' | 'supervisor' | 'admin' o key completo 'self_checkout.kiosk'.
    """
    key = perm_code if perm_code.startswith("self_checkout.") else f"self_checkout.{perm_code}"
    return has_permission(user, key, base_empresa)


def has_any_self_checkout_permission(user: Any, base_empresa: str) -> bool:
    """True si tiene al menos uno de kiosk, supervisor o admin."""
    return any(has_permission(user, p, base_empresa) for p in SCO_PERMISSIONS)
