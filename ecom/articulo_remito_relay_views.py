"""API artículos remitados mayoristapp."""

from __future__ import annotations

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.administranet_types import to_int_or_none
from ecom.permissions import EcomMayoristappSessionPermission
from ecom.services.articulo_remito_relay import listar_articulo_remito_relay
from ecom.services.mayoristapp_session import leer_idcliente_mayoristapp


def _session_base_empresa(request: Request) -> str | None:
    data = (getattr(request, "session", None) or {}).get("user") or {}
    be = data.get("base_empresa")
    return str(be).strip() if be else None


def _session_user(request: Request) -> dict:
    return (getattr(request, "session", None) or {}).get("user") or {}


class ArticuloRemitoListadoRelayAPIView(APIView):
    """POST ``/ecom/api/mayoristapp/articulo-remito/listado/?ajax=1``"""

    permission_classes = [EcomMayoristappSessionPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        if "ajax" not in request.query_params:
            return Response({"detail": "Parámetro ajax requerido."}, status=400)
        lim = to_int_or_none(request.data.get("limit")) or 500
        idc = leer_idcliente_mayoristapp(request)
        rows = listar_articulo_remito_relay(
            base, dict(request.data), _session_user(request), idc, limit=lim
        )
        return Response({"total": len(rows), "filas": rows})
