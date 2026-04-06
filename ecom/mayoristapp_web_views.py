"""
Vistas HTML mayoristapp (UX migrada desde PHP), sesión administraNET.
"""

from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView

from ecom.services.viajantes_opciones import opciones_viajantes_para_filtro


class MayoristappWebSessionMixin:
    """Sesión con ``user`` + ``base_empresa`` (legacy MySQL)."""

    def dispatch(self, request, *args, **kwargs):
        if "user" not in request.session:
            return redirect("login:login")
        if not getattr(request.user, "is_authenticated", False):
            return redirect("login:login")
        data = request.session.get("user") or {}
        if not data.get("base_empresa"):
            messages.warning(request, "Seleccione una empresa con base de datos para usar el portal mayorista.")
            return redirect("core:dashboard")
        return super().dispatch(request, *args, **kwargs)


class PresupuestosVendedorView(MayoristappWebSessionMixin, TemplateView):
    """
    Paridad ``lista-presupuestos-vendedor.php``: filtros + listado de presupuestos (PRE).
    Los datos se cargan vía POST JSON a la API ``relay-presupuestos`` ya migrada.
    """

    template_name = "ecom/presupuestos_vendedor.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sess_user = self.request.session.get("user") or {}
        base = str(sess_user.get("base_empresa") or "").strip()

        viajantes = {"opciones": [], "valor_por_defecto": "todos", "mostrar_opcion_todos": True}
        try:
            viajantes = opciones_viajantes_para_filtro(base, sess_user)
        except Exception:
            pass

        usa_manual = str(self.request.session.get("usa_id_manual") or "").strip().lower() in (
            "si",
            "sí",
            "1",
            "true",
        )

        context.update(
            {
                "page_title": "Presupuestos del vendedor",
                "presupuestos_api_url": reverse("ecom:mayoristapp_comprobantes_presupuestos"),
                "viajantes_opciones": viajantes.get("opciones") or [],
                "filtra_vendedor_default": viajantes.get("valor_por_defecto") or "todos",
                "usa_id_manual_cliente": usa_manual,
            }
        )
        return context
