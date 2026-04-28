"""
Resolución de la base MySQL (administraNET) para el pool compartido de Synap.

La conexión efectiva usa ``settings.DATABASES['mysql']`` y el nombre de esquema
``base_empresa``, alineado con ``RequestScopedMysqlMiddleware`` y la sesión de login.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from django.core.exceptions import PermissionDenied

if TYPE_CHECKING:
    from django.http import HttpRequest

    from .models import AdministraNETConfig


def get_session_base_empresa(request: Optional["HttpRequest"]) -> str:
    """
    Nombre del esquema MySQL de la empresa activa en sesión (login AdministraNET).

    Vacío si no hay sesión o no hay ``base_empresa`` (p. ej. usuario no autenticado en ese flujo).
    """
    if not request or not getattr(request, "session", None):
        return ""
    return ((request.session.get("user") or {}).get("base_empresa") or "").strip()


def resolve_mysql_base_empresa(
    request: Optional["HttpRequest"],
    adminet_config: Optional["AdministraNETConfig"],
) -> str:
    """
    Determina el nombre de base MySQL a usar con ``core.mysql_pool.get_connection``.

    - Con ``request``: la base de ``AdministraNETConfig`` debe coincidir con
      ``session['user']['base_empresa']``, salvo usuario administrador (supervisor).
    - Sin ``request`` (Celery, comandos): se usa ``adminet_config.database``.
    """
    cfg_db = (getattr(adminet_config, "database", None) or "").strip() if adminet_config else ""

    if request is None:
        if not cfg_db:
            raise ValueError(
                "Sin request HTTP: indique AdministraNETConfig.database para el pool MySQL."
            )
        return cfg_db

    user = getattr(request, "user", None)
    session_user = (request.session.get("user") or {}) if getattr(request, "session", None) else {}
    session_base = (session_user.get("base_empresa") or "").strip()

    if user and getattr(user, "is_admin", lambda: False)() and cfg_db:
        return cfg_db

    if session_base and cfg_db and session_base != cfg_db:
        raise PermissionDenied(
            "La configuración de integración apunta a otra base que la empresa activa en sesión."
        )

    resolved = session_base or cfg_db
    if not resolved:
        raise PermissionDenied(
            "No hay base de empresa en sesión ni en la configuración AdministraNET."
        )
    return resolved
