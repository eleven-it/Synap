"""
API listado recibos mayoristapp (``relay-recibos.php`` → ``lista_recibos`` con ``consulta=1``).
"""

from __future__ import annotations

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ecom.permissions import EcomMayoristappSessionPermission
from ecom.services.recibos_relay import listar_recibos_relay
from core.utils.administranet_types import to_int_or_none


def _session_base_empresa(request: Request) -> str | None:
    data = (getattr(request, "session", None) or {}).get("user") or {}
    be = data.get("base_empresa")
    return str(be).strip() if be else None


def _session_user(request: Request) -> dict:
    return (getattr(request, "session", None) or {}).get("user") or {}


def _consulta_activa(request: Request) -> bool:
    q = request.query_params.get("consulta") or request.data.get("consulta")
    return str(q).strip() == "1"


class RecibosListadoRelayAPIView(APIView):
    """
    POST ``/ecom/api/mayoristapp/recibos/listado/?ajax=1&consulta=1``

    Paridad ``relay-recibos.php`` (listado HTML). Cuerpo JSON: ``campoBusca``,
    ``fechaDesde``, ``fechaHasta``, ``filtraCliente``, ``filtraVendedor`` (igual que PHP).
    Requiere ``id_usuario`` en sesión salvo cuando ``filtraVendedor`` está presente (p. ej. ``todos``).
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        if "ajax" not in request.query_params:
            return Response({"detail": "Parámetro ajax requerido."}, status=400)
        if not _consulta_activa(request):
            return Response({"detail": "Parámetro consulta=1 requerido (query o cuerpo)."}, status=400)
        lim = to_int_or_none(request.data.get("limit")) or 500
        rows, err = listar_recibos_relay(base, dict(request.data), _session_user(request), limit=lim)
        if err:
            return Response({"detail": err}, status=400)
        return Response({"total": len(rows or []), "filas": rows})

