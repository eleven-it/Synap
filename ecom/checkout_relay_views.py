"""
Vista API del checkout mayorista (Fase P2): confirma el carrito dando de alta el
comprobante (PED/PRE) en MySQL AdministraNET.
"""

from __future__ import annotations

from typing import Any, List

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.administranet_types import to_int_or_none
from ecom.carrito_relay_views import _resolver_contexto
from ecom.models import EcomCart
from ecom.permissions import EcomMayoristappSessionPermission
from ecom.services import mayorista_checkout_service as checkout_svc
from ecom.services.mayorista_checkout_service import CheckoutInput


def _session_bag(request: Request) -> dict:
    return (getattr(request, "session", None) or {}).get("mayoristapp") or {}


def _session_cod_viajante(request: Request):
    user = (getattr(request, "session", None) or {}).get("user") or {}
    return to_int_or_none(user.get("cod_viajante") or user.get("codViajante"))


def _session_pv(request: Request):
    sess = getattr(request, "session", None) or {}
    bag = _session_bag(request)
    return to_int_or_none(
        sess.get("id_punto_venta_activo")
        or bag.get("id_punto_venta_activo")
        or bag.get("id_punto_venta")
    )


def _session_agente_percep(request: Request):
    """Flag `agente_percep` ('Si'/'No') si la sesión lo trae (paridad legacy $_SESSION).

    Si no está en sesión, se devuelve None y el servicio lo resuelve desde la sucursal
    del usuario en MySQL.
    """
    sess = getattr(request, "session", None) or {}
    user = sess.get("user") or {}
    val = sess.get("agente_percep") or user.get("agente_percep") or _session_bag(request).get("agente_percep")
    return str(val) if val is not None else None


def _session_dias_no_laborables(request: Request) -> List[int]:
    sess = getattr(request, "session", None) or {}
    raw = sess.get("arr_dias_no_laborables") or _session_bag(request).get("arr_dias_no_laborables") or []
    out: List[int] = []
    if isinstance(raw, (list, tuple)):
        for d in raw:
            n = to_int_or_none(d)
            if n is not None:
                out.append(n)
    return out


class CheckoutConfirmarRelayAPIView(APIView):
    """
    POST /ecom/api/mayoristapp/checkout/confirmar/
    Body: {tipo?, id_punto_venta?, forma_entrega?, cond_venta?, id_cliente_domicilio?, id_ruta?, observaciones?}
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def post(self, request: Request) -> Response:
        ctx, err = _resolver_contexto(request)
        if err is not None:
            return err
        _base, id_usuario, cart, _desc = ctx

        if cart.estado == EcomCart.ESTADO_CONFIRMADO and cart.codigo_movimiento:
            return Response(checkout_svc._result_desde_cart(cart), status=200)

        body = request.data or {}
        tipo = str(body.get("tipo") or cart.tipo_comprobante or EcomCart.TIPO_PEDIDO).upper()
        pv = to_int_or_none(body.get("id_punto_venta")) or _session_pv(request)

        bag = _session_bag(request)
        datos = CheckoutInput(
            tipo=tipo,
            id_punto_venta=pv,
            forma_entrega=str(body.get("forma_entrega") or ""),
            id_cliente_domicilio=to_int_or_none(body.get("id_cliente_domicilio")),
            id_ruta=to_int_or_none(body.get("id_ruta")),
            observaciones=str(body.get("observaciones") or ""),
            es_cliente=bool(body.get("es_cliente", False)),
            dias_entrega=to_int_or_none(bag.get("cant_dias_entrega")) or 0,
            dias_no_laborables=_session_dias_no_laborables(request),
            agente_percep=_session_agente_percep(request),
        )

        try:
            ok, error, result = checkout_svc.confirmar(
                cart, datos, id_usuario=id_usuario, cod_viajante=_session_cod_viajante(request)
            )
        except Exception:
            return Response({"detail": "Error al confirmar el comprobante."}, status=500)

        if not ok:
            estado = 409 if error and "Stock insuficiente" in error else 400
            return Response({"detail": error}, status=estado)
        return Response(result, status=201)
