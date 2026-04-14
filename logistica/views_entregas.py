"""
Pantalla operativa Entregas (módulo Logística).
Acceso: permiso ``logistica_editar_entregas`` (o comodín ``logistica.*``) en el puesto.
"""

from __future__ import annotations

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView

from ecom.mayoristapp_web_views import MayoristappWebSessionMixin


class LogisticaEntregasView(MayoristappWebSessionMixin, TemplateView):
    """Pantalla operativa Entregas (listado Hoy / Mi ruta, filtros ruta/chofer, registro de entrega)."""

    template_name = "logistica/entregas.html"

    def dispatch(self, request, *args, **kwargs):
        if "user" not in request.session:
            return redirect("login:login")
        if not getattr(request.user, "is_authenticated", False):
            return redirect("login:login")
        data = request.session.get("user") or {}
        if not data.get("base_empresa"):
            messages.warning(
                request,
                "Seleccione una empresa con base de datos para usar logística.",
            )
            return redirect("core:dashboard")
        user = request.user
        if getattr(user, "is_superuser", False):
            return super().dispatch(request, *args, **kwargs)
        if hasattr(user, "tiene_permiso") and callable(user.tiene_permiso):
            if user.tiene_permiso("logistica_editar_entregas"):
                return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied(
            "No tiene permiso para acceder a la operación de entregas."
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Entregas"
        lista_url = reverse("logistica:api_entregas_lista")
        context["logistica_entregas_api_base"] = lista_url.rsplit("/lista/", 1)[0].rstrip("/")
        return context
