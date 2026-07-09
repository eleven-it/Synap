"""Resolución de landing por rol para operarios MPR.

Centraliza la regla: un operario "puro" (tiene `mpr.parte_operario` y NO
`mpr.ver`) aterriza en su pantalla de carga móvil, sin acceso al resto del
módulo. Reutilizado por el dashboard y la raíz `/`.
"""
from __future__ import annotations

import logging
from typing import Optional

from django.urls import reverse

logger = logging.getLogger(__name__)

PERMISO_OPERARIO = "mpr.parte_operario"
PERMISO_VER = "mpr.ver"


def _tiene_permiso(user, permiso: str) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    fn = getattr(user, "tiene_permiso", None)
    if not callable(fn):
        return False
    try:
        return bool(fn(permiso))
    except Exception:
        return False


def es_operario_puro(user) -> bool:
    """True si el usuario tiene `mpr.parte_operario` y NO tiene `mpr.ver`."""
    return _tiene_permiso(user, PERMISO_OPERARIO) and not _tiene_permiso(user, PERMISO_VER)


def landing_url_para_usuario(user) -> Optional[str]:
    """URL de aterrizaje forzado, o None si el usuario usa el flujo normal."""
    if es_operario_puro(user):
        try:
            return reverse("mpr:parte_movil_operario")
        except Exception as e:  # pragma: no cover - URL siempre registrada
            logger.warning("No se pudo resolver landing de operario: %s", e)
            return None
    return None


# Alias por fidelidad con el spec (mpr-operario-login §Landing).
resolver_landing_usuario = landing_url_para_usuario
