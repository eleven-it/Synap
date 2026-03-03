"""Permisos por rol (Admin, Agente, Supervisor)."""
from rest_framework import permissions


def _get_role(request):
    if not request.user or not request.user.is_authenticated:
        return None
    if hasattr(request.user, "agent_profile"):
        return request.user.agent_profile.role
    return None


class IsAgentOrAdmin(permissions.BasePermission):
    """Acceso para Agente, Supervisor o Admin."""

    def has_permission(self, request, view):
        role = _get_role(request)
        return role in ("admin", "agent", "supervisor")


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return _get_role(request) == "admin"
