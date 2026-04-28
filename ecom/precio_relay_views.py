"""
Relays precios mayoristapp (lista de precios, promociones).
"""

from __future__ import annotations

from typing import Optional

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ecom.permissions import EcomMayoristappSessionPermission
from ecom.services.precio_relays import (
    lista_precio_relay_json,
    parse_query_promociones,
    promociones_relay_payload,
)
from core.utils.administranet_types import to_int_or_none


def _session_base_empresa(request: Request) -> str | None:
    data = (getattr(request, "session", None) or {}).get("user") or {}
    be = data.get("base_empresa")
    return str(be).strip() if be else None


def _cod_lista_precio_cliente_desde_sesion(request: Request) -> Optional[int]:
    """Paridad ``$objCliente->codListaPrecio`` / sesión PHP."""
    sess = getattr(request, "session", None) or {}
    user = sess.get("user") or {}
    ma = sess.get("mayoristapp") or {}
    cliente = ma.get("cliente") if isinstance(ma.get("cliente"), dict) else {}
    return to_int_or_none(
        user.get("cliente_cod_lista_precio")
        or ma.get("cliente_cod_lista_precio")
        or cliente.get("codListaPrecio")
    )


def _lista_precio_texto_cliente_desde_sesion(request: Request) -> Optional[str]:
    """Texto tipo ``Lista 1`` para filtro ``promocion_lista*`` (``$objCliente->listaPrecio``)."""
    sess = getattr(request, "session", None) or {}
    user = sess.get("user") or {}
    ma = sess.get("mayoristapp") or {}
    cliente = ma.get("cliente") if isinstance(ma.get("cliente"), dict) else {}
    for v in (
        user.get("lista_precio_cliente"),
        user.get("listaPrecioCliente"),
        ma.get("lista_precio_cliente"),
        cliente.get("listaPrecio"),
    ):
        if v is not None and str(v).strip():
            return str(v).strip()
    return None


class ListaPrecioRelayAPIView(APIView):
    """
    GET /ecom/api/mayoristapp/precios/lista-precio/

    Paridad ``relay-lista-precio.php`` (JSON; el PHP no exige ``ajax``).
    ``selected`` usa ``cliente_cod_lista_precio`` / ``mayoristapp.cliente.codListaPrecio`` o lista por defecto desde ``configuracion``.
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)

        cod_cli = to_int_or_none(request.query_params.get("cod_lista_cliente"))
        if cod_cli is None:
            cod_cli = _cod_lista_precio_cliente_desde_sesion(request)

        try:
            data = lista_precio_relay_json(base, cod_lista_precio_cliente=cod_cli)
        except Exception:
            return Response({"detail": "Error al armar listas de precio."}, status=500)

        return Response(data)


class PromocionesRelayAPIView(APIView):
    """
    GET /ecom/api/mayoristapp/precios/promociones/?ajax=1

    Paridad ``relay-promociones.php`` (JSON: ``articulos`` + ``intervalos_por_articulo``).

    Filtros: ``categoria``, ``rubro``, ``subrubro``, ``marca``, ``modelo``.
    Opcional: ``listaPrecio`` (texto) para filtrar por lista del cliente; si no, se usa sesión o sin filtro de lista.
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)

        if "ajax" not in request.query_params:
            return Response(
                {"detail": "Parámetro ajax requerido (paridad relay-promociones.php)."},
                status=400,
            )

        filtros, lista_q = parse_query_promociones(request.query_params)
        lista_cli: Optional[str] = lista_q or _lista_precio_texto_cliente_desde_sesion(request)

        try:
            payload = promociones_relay_payload(
                base,
                lista_precio_cliente=lista_cli,
                id_categoria=filtros["id_categoria"],
                id_rubro=filtros["id_rubro"],
                id_subrubro=filtros["id_subrubro"],
                id_marca=filtros["id_marca"],
                id_modelo=filtros["id_modelo"],
            )
        except Exception:
            return Response({"detail": "Error al consultar promociones."}, status=500)

        return Response(payload)
