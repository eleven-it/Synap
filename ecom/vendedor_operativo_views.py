"""APIs vendedor operativo mayoristapp (cartera supervisor + selección)."""

from __future__ import annotations

from typing import Any, Dict

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.administranet_types import to_int_or_none
from ecom.catalogo_producto_relay_views import _session_base_empresa
from ecom.permissions import EcomMayoristappSessionPermission
from ecom.services.mayorista_cart_service import reiniciar_borrador_compra_vendedor
from ecom.services.mayoristapp_session import limpiar_cliente_seleccion_mayoristapp
from ecom.services.mayoristapp_sesion_contexto import asegurar_contexto_mayoristapp
from ecom.services.vendedor_operativo import (
    guardar_cod_viajante_operativo,
    listar_cartera_operativa,
    resolver_viajante_operativo,
)


def _sess_user(request) -> Dict[str, Any]:
    return (getattr(request, "session", None) or {}).get("user") or {}


class VendedoresCarteraRelayAPIView(APIView):
    """
    GET /ecom/api/mayoristapp/vendedores-cartera/
    → {vendedores:[{cod_viajante,nombre}], operativo, propio, mostrar_selector}
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "Sin base_empresa."}, status=400)
        ctx = asegurar_contexto_mayoristapp(request)
        payload = listar_cartera_operativa(base, ctx)
        return Response(payload)


class VendedorOperativoRelayAPIView(APIView):
    """
    POST /ecom/api/mayoristapp/vendedor-operativo/
    Body: {cod_viajante} → {ok, operativo}
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"ok": False, "detail": "Sin base_empresa."}, status=400)
        ctx = asegurar_contexto_mayoristapp(request)
        body = request.data if isinstance(request.data, dict) else {}
        cod = to_int_or_none(body.get("cod_viajante"))
        if cod is None:
            return Response({"ok": False, "detail": "Falta cod_viajante válido."}, status=400)
        if not guardar_cod_viajante_operativo(request, cod):
            return Response(
                {"ok": False, "detail": "El vendedor no pertenece a su cartera."},
                status=403,
            )
        sess = _sess_user(request)
        id_u = to_int_or_none(sess.get("id_usuario"))
        if id_u is not None:
            limpiar_cliente_seleccion_mayoristapp(request)
            reiniciar_borrador_compra_vendedor(base, id_u)
        operativo = resolver_viajante_operativo(asegurar_contexto_mayoristapp(request))
        return Response({"ok": True, "operativo": operativo, "contexto_limpiado": True})
