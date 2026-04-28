"""
Vista web + API JSON — Estado de pedidos (pantalla preparación / logística).
"""

from __future__ import annotations

from django.urls import reverse
from django.views.generic import TemplateView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ecom.mayoristapp_web_views import MayoristappWebSessionMixin
from ecom.permissions import EcomMayoristappSessionPermission
from ecom.services.logistica_estado_pedidos_relay import (
    estado_pedidos_kanban_json,
    listar_sucursales_tv,
    parse_cod_sucursal_request,
)


def _session_base_empresa(request: Request) -> str | None:
    data = (getattr(request, "session", None) or {}).get("user") or {}
    be = data.get("base_empresa")
    return str(be).strip() if be else None


class EstadoPedidosPreparacionView(MayoristappWebSessionMixin, TemplateView):
    """
    Paridad ``logistica_pantalla_preparacion.php``: tablero Preparado / En preparación / En remito.
    """

    template_name = "ecom/estado_pedidos_preparacion.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Estado de pedidos",
                "estado_pedidos_api_url": reverse("ecom:mayoristapp_logistica_estado_pedidos"),
            }
        )
        return context


class EstadoPedidosKanbanAPIView(APIView):
    """
    GET ``/ecom/api/mayoristapp/logistica/estado-pedidos/?ajax=1``

    - ``?sucursales=1`` — lista sucursales (mismo criterio que PHP).
    - ``?ajax=1`` — JSON kanban; opcional ``cod_sucursal``.
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)

        if request.query_params.get("sucursales") == "1":
            try:
                sucursales = listar_sucursales_tv(base_empresa=base)
            except Exception as exc:
                return Response({"detail": str(exc)}, status=500)
            return Response({"sucursales": sucursales})

        if "ajax" not in request.query_params:
            return Response({"detail": "Parámetro ajax requerido."}, status=400)

        cod = parse_cod_sucursal_request(request.query_params.get("cod_sucursal"))
        try:
            payload = estado_pedidos_kanban_json(base_empresa=base, cod_sucursal=cod)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=500)
        return Response(payload)
