from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import PermissionDenied

from core.models import UsuarioExtendido
from core.utils.permissions import get_user_permission_set, user_has_full_access


@dataclass
class PolicyContext:
    user: object
    owner_user: UsuarioExtendido | None
    empresa: object | None
    legacy_user_id: int | None
    legacy_user_code: str
    base_empresa: str
    timezone: str
    locale: str
    permissions: set[str]


class PolicyGate:
    """Validaciones mínimas de acceso para el módulo IA."""

    @staticmethod
    def is_full_access_user(user) -> bool:
        return user_has_full_access(user)

    @classmethod
    def build_context(cls, request) -> PolicyContext:
        user = request.user
        empresa = getattr(user, "empresa_activa", None)
        owner_user = user if isinstance(user, UsuarioExtendido) else None

        session_user = request.session.get("user", {}) if hasattr(request, "session") else {}
        legacy_user_id = session_user.get("id_usuario") or getattr(user, "id_usuario", None)
        legacy_user_code = session_user.get("cod_usuario") or getattr(user, "cod_usuario", "") or ""
        base_empresa = session_user.get("base_empresa") or getattr(user, "base_empresa", "") or ""
        timezone = session_user.get("timezone") or "America/Argentina/Buenos_Aires"
        locale = session_user.get("idioma") or getattr(user, "idioma", "es") or "es"

        if owner_user is None and legacy_user_id:
            try:
                owner_user = UsuarioExtendido.objects.get(id=legacy_user_id)
            except UsuarioExtendido.DoesNotExist:
                owner_user = None

        permissions = get_user_permission_set(user)

        return PolicyContext(
            user=user,
            owner_user=owner_user,
            empresa=empresa,
            legacy_user_id=legacy_user_id,
            legacy_user_code=legacy_user_code,
            base_empresa=base_empresa,
            timezone=timezone,
            locale=locale,
            permissions=permissions,
        )

    @staticmethod
    def ensure_authenticated(request) -> None:
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            raise PermissionDenied("Debés iniciar sesión para usar el módulo IA.")

    @staticmethod
    def has_permission(user, permission_code: str) -> bool:
        if not permission_code:
            return True
        if PolicyGate.is_full_access_user(user):
            return True
        if hasattr(user, "tiene_permiso") and callable(user.tiene_permiso):
            return user.tiene_permiso(permission_code)
        if hasattr(user, "get_permisos_totales"):
            permissions = user.get_permisos_totales()
            return "*" in permissions or permission_code in permissions
        return False

    @classmethod
    def ensure_agent_access(cls, request, agent) -> PolicyContext:
        cls.ensure_authenticated(request)
        context = cls.build_context(request)
        if agent.required_permission and not cls.has_permission(request.user, agent.required_permission):
            raise PermissionDenied("No tenés permisos para usar este agente.")
        return context
