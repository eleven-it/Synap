"""API REST v1 — listado de pedidos (piloto)."""

from __future__ import annotations

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.administranet_types import to_int_or_none
from ecom.api.serializers.comprobantes import pedidos_request_to_relay_body
from ecom.permissions import EcomComprobantesReadPermission
from ecom.services.comprobantes_relay import (
    detalle_pedido_relay,
    listar_pedidos_relay,
    sugerencias_nro_comp_relay,
)
from ecom.services.mayoristapp_session import leer_idcliente_mayoristapp


def _session_base_empresa(request: Request) -> str | None:
    data = (getattr(request, "session", None) or {}).get("user") or {}
    be = data.get("base_empresa")
    return str(be).strip() if be else None


def _session_user(request: Request) -> dict:
    return (getattr(request, "session", None) or {}).get("user") or {}


def _error_response(message: str, code: str, status: int = 400) -> Response:
    return Response({"ok": False, "error": message, "code": code}, status=status)


class PedidosListV1APIView(APIView):
    """
    POST ``/ecom/api/v1/mayoristapp/comprobantes/pedidos/``

    Contrato REST Synap (snake_case). Delega en ``listar_pedidos_relay``.
    """

    permission_classes = [EcomComprobantesReadPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return _error_response(
                "No se encontró base_empresa en la sesión.",
                "sin_base_empresa",
            )
        body = pedidos_request_to_relay_body(dict(request.data))
        page_size = to_int_or_none(request.data.get("page_size")) or to_int_or_none(
            body.get("limit")
        ) or 500
        body["limit"] = page_size
        idc = leer_idcliente_mayoristapp(request)
        rows = listar_pedidos_relay(
            base,
            body,
            _session_user(request),
            idc,
            limit=page_size,
        )
        page = to_int_or_none(request.data.get("page")) or 1
        return Response(
            {
                "ok": True,
                "page": page,
                "page_size": page_size,
                "total": len(rows),
                "results": rows,
            }
        )


class PedidosSugerenciasNumeroV1APIView(APIView):
    """
    GET ``/ecom/api/v1/mayoristapp/comprobantes/pedidos/sugerencias-numero/?q=…``
    """

    permission_classes = [EcomComprobantesReadPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return _error_response(
                "No se encontró base_empresa en la sesión.",
                "sin_base_empresa",
            )
        q = (request.query_params.get("q") or "").strip()
        idc = leer_idcliente_mayoristapp(request)
        nums = sugerencias_nro_comp_relay(
            base,
            "PED",
            q,
            _session_user(request),
            idc,
        )
        return Response({"ok": True, "total": len(nums), "results": nums})


class PedidosDetalleV1APIView(APIView):
    """
    GET ``/ecom/api/v1/mayoristapp/comprobantes/pedidos/<cod_mov>/detalle/``
    """

    permission_classes = [EcomComprobantesReadPermission]

    def get(self, request: Request, cod_mov: int) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return _error_response(
                "No se encontró base_empresa en la sesión.",
                "sin_base_empresa",
            )
        sess = getattr(request, "session", None) or {}
        usa_manual = str(sess.get("usa_id_manual") or "").strip().lower() in (
            "si",
            "sí",
            "1",
            "true",
        )
        rows = detalle_pedido_relay(base, cod_mov, usa_id_manual=usa_manual)
        return Response({"ok": True, "total": len(rows), "results": rows})
