"""
Vistas stub Phase 0–1: config ternas y pedido masivo (UI completa en Phase 2/4).
"""

from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import TemplateView

from ecom.services.mayoristapp_sesion_contexto import asegurar_contexto_mayoristapp


def _usuario_tiene_permiso(request, codigo: str) -> bool:
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    if hasattr(user, "tiene_permiso"):
        if user.tiene_permiso("*") or user.tiene_permiso("ecom.*"):
            return True
        return bool(user.tiene_permiso(codigo))
    return False


class _StubMayoristappPermisoView(TemplateView):
    """Sesión mayorista + permiso Synap antes de renderizar."""

    permiso_requerido = ""
    # Cualquiera de estos permisos habilita la pantalla (OR). Si está vacío se
    # usa ``permiso_requerido``.
    permisos_or: tuple = ()

    def _tiene_permiso_acceso(self, request) -> bool:
        if self.permisos_or:
            return any(_usuario_tiene_permiso(request, p) for p in self.permisos_or)
        if self.permiso_requerido:
            return _usuario_tiene_permiso(request, self.permiso_requerido)
        return True

    def dispatch(self, request, *args, **kwargs):
        if "user" not in request.session:
            return redirect("login:login")
        if not getattr(request.user, "is_authenticated", False):
            return redirect("login:login")
        data = request.session.get("user") or {}
        if not data.get("base_empresa"):
            messages.warning(
                request,
                "Seleccione una empresa con base de datos para usar el portal mayorista.",
            )
            return redirect("core:dashboard")
        if not self._tiene_permiso_acceso(request):
            messages.error(request, "No tiene permiso para acceder a esta pantalla.")
            return redirect("ecom:mayoristapp_pedidos_hub")
        asegurar_contexto_mayoristapp(request)
        return super().dispatch(request, *args, **kwargs)


class ConfigVendedorClienteMarcaView(_StubMayoristappPermisoView):
    """Legacy stub — la UI real está en ``vendedor_cliente_marca_views``."""

    template_name = "ecom/placeholder_fase.html"
    permiso_requerido = "ecom.config_vendedor_cliente_marca"
