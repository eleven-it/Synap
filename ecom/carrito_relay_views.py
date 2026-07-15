"""
Vistas API del carrito mayorista (Fase P1).

Persistencia en Postgres `synap`; precio vía motor único; stock vía StockService.
Sin escritura a MySQL legacy.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.administranet_types import to_int_or_none
from ecom.catalogo_producto_relay_views import (
    _leer_desc_pie_cliente,
    _obtener_id_deposito,
    _obtener_lista_id_y_cliente,
    _session_base_empresa,
)
from ecom.models import EcomCart
from ecom.permissions import EcomMayoristappSessionPermission
from ecom.services import mayorista_cart_service as cart_svc
from ecom.services.vendedor_operativo import resolver_viajante_operativo


def _session_id_usuario(request: Request) -> Optional[int]:
    data = (getattr(request, "session", None) or {}).get("user") or {}
    uid = to_int_or_none(data.get("id_usuario"))
    if uid is not None:
        return uid
    u = getattr(request, "user", None)
    return getattr(u, "id", None)


def _tipo_comprobante_sesion(request: Request) -> str:
    ma = (getattr(request, "session", None) or {}).get("mayoristapp") or {}
    val = str(ma.get("formulario") or "").strip().upper()
    return val if val in (EcomCart.TIPO_PEDIDO, EcomCart.TIPO_PRESUPUESTO) else EcomCart.TIPO_PEDIDO


def _id_cliente_domicilio_sesion(request: Request) -> Optional[int]:
    sess = getattr(request, "session", None) or {}
    ma = sess.get("mayoristapp") or {}
    for fuente in (ma.get("id_cliente_domicilio"), sess.get("id_cliente_domicilio")):
        idd = to_int_or_none(fuente)
        if idd is not None and idd > 0:
            return idd
    body = request.data if isinstance(request.data, dict) else {}
    return to_int_or_none(body.get("id_cliente_domicilio"))


def _resolver_contexto(request: Request):
    """
    Devuelve (base, id_usuario, cart, descuento_cliente) o (None, None, None, None) + Response de error.
    """
    base = _session_base_empresa(request)
    if not base:
        return None, Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)

    id_usuario = _session_id_usuario(request)
    if id_usuario is None:
        return None, Response({"detail": "No se encontró el usuario en la sesión."}, status=400)

    lista_id, codigo_cliente, descuento_cliente, iva_incluido = _obtener_lista_id_y_cliente(request, base)
    id_deposito = _obtener_id_deposito(request)
    desc_pie_cliente = _leer_desc_pie_cliente(request) if codigo_cliente is not None else None

    cart = cart_svc.obtener_o_crear_carrito(
        base,
        id_usuario,
        idcliente=codigo_cliente,
        lista_id=lista_id or 1,
        id_deposito=id_deposito,
        iva_incluido=iva_incluido,
        tipo_comprobante=_tipo_comprobante_sesion(request),
        desc_pie_cliente=desc_pie_cliente,
    )
    return (base, id_usuario, cart, descuento_cliente), None


class CarritoRelayAPIView(APIView):
    """
    GET  /ecom/api/mayoristapp/carrito/ — obtiene (o crea) el carrito activo del vendedor.
    POST /ecom/api/mayoristapp/carrito/ — agrega un ítem. Body: {id_articulo, cantidad}.
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> Response:
        ctx, err = _resolver_contexto(request)
        if err is not None:
            return err
        _base, _uid, cart, _desc = ctx
        return Response(cart_svc.serializar_carrito(cart))

    def post(self, request: Request) -> Response:
        ctx, err = _resolver_contexto(request)
        if err is not None:
            return err
        _base, _uid, cart, descuento_cliente = ctx

        body = request.data or {}
        id_articulo = to_int_or_none(body.get("id_articulo"))
        cantidad = body.get("cantidad")
        if id_articulo is None:
            return Response({"detail": "id_articulo es obligatorio."}, status=400)

        try:
            sess_user = (getattr(request, "session", None) or {}).get("user") or {}
            item, error = cart_svc.agregar_item(
                cart,
                id_articulo,
                cantidad,
                descuento_cliente=descuento_cliente,
                tipo_unidad=str(body.get("tipo_unidad") or "Unidad"),
                multiplicador=body.get("multiplicador"),
                cod_viajante=resolver_viajante_operativo(sess_user),
                id_cliente_domicilio=_id_cliente_domicilio_sesion(request),
            )
        except Exception:
            return Response({"detail": "Error al agregar el artículo al carrito."}, status=500)

        if error:
            return Response({"detail": error, "carrito": cart_svc.serializar_carrito(cart)}, status=409)
        return Response(cart_svc.serializar_carrito(cart), status=201)


class CarritoTipoComprobanteRelayAPIView(APIView):
    """PATCH /ecom/api/mayoristapp/carrito/tipo-comprobante/ — Body: {tipo: PED|PRE|DEV}."""

    permission_classes = [EcomMayoristappSessionPermission]

    def patch(self, request: Request) -> Response:
        ctx, err = _resolver_contexto(request)
        if err is not None:
            return err
        _base, _uid, cart, _desc = ctx
        tipo = str((request.data or {}).get("tipo") or "").strip().upper()
        ok, error = cart_svc.actualizar_tipo_comprobante(cart, tipo)
        if not ok:
            return Response({"detail": error}, status=400)
        return Response(cart_svc.serializar_carrito(cart))


class CarritoItemRelayAPIView(APIView):
    """
    PATCH  /ecom/api/mayoristapp/carrito/items/<item_id>/ — actualiza cantidad y/o descuento de renglón.
    DELETE /ecom/api/mayoristapp/carrito/items/<item_id>/ — quita el renglón.
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def patch(self, request: Request, item_id: int) -> Response:
        ctx, err = _resolver_contexto(request)
        if err is not None:
            return err
        _base, _uid, cart, _desc = ctx

        body = request.data or {}
        aplicado = False
        try:
            if body.get("cantidad") is not None:
                ok, error = cart_svc.actualizar_cantidad(cart, item_id, body.get("cantidad"))
                if not ok:
                    return Response(
                        {"detail": error, "carrito": cart_svc.serializar_carrito(cart)}, status=409
                    )
                aplicado = True
            if body.get("porcentaje_descuento") is not None:
                ok, error = cart_svc.actualizar_descuento_item(cart, item_id, body.get("porcentaje_descuento"))
                if not ok:
                    return Response({"detail": error}, status=400)
                aplicado = True
        except Exception:
            return Response({"detail": "Error al actualizar el renglón."}, status=500)

        if not aplicado:
            return Response({"detail": "Nada para actualizar (cantidad o porcentaje_descuento)."}, status=400)
        return Response(cart_svc.serializar_carrito(cart))

    def delete(self, request: Request, item_id: int) -> Response:
        ctx, err = _resolver_contexto(request)
        if err is not None:
            return err
        _base, _uid, cart, _desc = ctx

        if not cart_svc.quitar_item(cart, item_id):
            return Response({"detail": "Renglón no encontrado."}, status=404)
        return Response(cart_svc.serializar_carrito(cart))


class CarritoVaciarRelayAPIView(APIView):
    """POST /ecom/api/mayoristapp/carrito/vaciar/ — vacía el carrito."""

    permission_classes = [EcomMayoristappSessionPermission]

    def post(self, request: Request) -> Response:
        ctx, err = _resolver_contexto(request)
        if err is not None:
            return err
        _base, _uid, cart, _desc = ctx
        cart_svc.limpiar(cart)
        return Response(cart_svc.serializar_carrito(cart))


class CarritoListaPrecioRelayAPIView(APIView):
    """PATCH /ecom/api/mayoristapp/carrito/lista-precio/ — Body: {lista_id}."""

    permission_classes = [EcomMayoristappSessionPermission]

    def patch(self, request: Request) -> Response:
        ctx, err = _resolver_contexto(request)
        if err is not None:
            return err
        _base, _uid, cart, descuento_cliente = ctx
        lista_id = to_int_or_none((request.data or {}).get("lista_id"))
        if lista_id is None:
            return Response({"detail": "lista_id es obligatorio."}, status=400)
        try:
            ok, error = cart_svc.actualizar_lista_precio(
                cart, int(lista_id), descuento_cliente=descuento_cliente or Decimal("0")
            )
        except Exception:
            return Response({"detail": "Error al actualizar la lista de precios."}, status=500)
        if not ok:
            return Response({"detail": error}, status=400)
        return Response(cart_svc.serializar_carrito(cart))


class CarritoDescuentoPieRelayAPIView(APIView):
    """POST /ecom/api/mayoristapp/carrito/descuento-pie/ — aplica descuento al pie. Body: {porcentaje}."""

    permission_classes = [EcomMayoristappSessionPermission]

    def post(self, request: Request) -> Response:
        ctx, err = _resolver_contexto(request)
        if err is not None:
            return err
        _base, _uid, cart, _desc = ctx

        ok, error = cart_svc.aplicar_descuento_pie(cart, (request.data or {}).get("porcentaje"))
        if not ok:
            return Response({"detail": error}, status=400)
        return Response(cart_svc.serializar_carrito(cart))
