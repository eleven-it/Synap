"""
APIs cuenta corriente mayoristapp (``relay-ctacte.php``).
"""

from __future__ import annotations

from decimal import Decimal

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ecom.permissions import EcomMayoristappSessionPermission
from ecom.services.cliente_relay import cliente_accesible_por_sesion
from ecom.services.consumos_resumen_relay import listar_consumos_resumen_relay
from ecom.services.cuenta_corriente_pedidos_relay import (
    listar_pedidos_cuenta_corriente_relay,
    sugerencias_nro_pedido_cuenta_corriente_relay,
)
from ecom.services.ctacte_relay import listar_movimientos_ctacte_relay, sugerencias_nro_ctacte_relay
from ecom.services.mayoristapp_session import leer_cliente_seleccionado, leer_idcliente_mayoristapp
from core.utils.administranet_types import to_decimal_or_none, to_int_or_none


def _session_base_empresa(request: Request) -> str | None:
    data = (getattr(request, "session", None) or {}).get("user") or {}
    be = data.get("base_empresa")
    return str(be).strip() if be else None


def _session_user(request: Request) -> dict:
    return (getattr(request, "session", None) or {}).get("user") or {}


class CtacteMovimientosRelayAPIView(APIView):
    """
    POST ``/ecom/api/mayoristapp/ctacte/movimientos/?ajax=1``

    Paridad listado JSON (PHP HTML). Requiere ``idcliente`` en sesión.
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        if "ajax" not in request.query_params:
            return Response({"detail": "Parámetro ajax requerido."}, status=400)
        idc = leer_idcliente_mayoristapp(request)
        if idc is None:
            return Response({"detail": "No hay idcliente en sesión (seleccione un cliente)."}, status=400)
        sess_user = _session_user(request)
        if not cliente_accesible_por_sesion(base, idc, sess_user):
            return Response({"detail": "Cliente no disponible para esta sesión."}, status=403)
        lim = to_int_or_none(request.data.get("limit")) or 500
        rows = listar_movimientos_ctacte_relay(base, dict(request.data), idc, limit=lim)
        return Response({"total": len(rows), "filas": rows})


class CtacteSugerenciasNroRelayAPIView(APIView):
    """
    GET ``/ecom/api/mayoristapp/ctacte/sugerencias-nro/?ajax=1&q=…``

    Paridad ``queryString`` en ``relay-ctacte.php``.
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        if "ajax" not in request.query_params:
            return Response({"detail": "Parámetro ajax requerido."}, status=400)
        idc = leer_idcliente_mayoristapp(request)
        if idc is None:
            return Response({"detail": "No hay idcliente en sesión."}, status=400)
        sess_user = _session_user(request)
        if not cliente_accesible_por_sesion(base, idc, sess_user):
            return Response({"detail": "Cliente no disponible."}, status=403)
        q = request.query_params.get("q") or request.query_params.get("queryString") or ""
        nums = sugerencias_nro_ctacte_relay(base, q, idc)
        return Response({"sugerencias": nums, "total": len(nums)})


class CuentaCorrientePedidosRelayAPIView(APIView):
    """
    POST ``/ecom/api/mayoristapp/ctacte/pedidos/?ajax=1``

    Paridad ``relay-cuenta-corriente.php`` (listado PED del cliente en sesión).
    El cuerpo no puede forzar modo vendedor: se ignora ``vendedor``.
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        if "ajax" not in request.query_params:
            return Response({"detail": "Parámetro ajax requerido."}, status=400)
        idc = leer_idcliente_mayoristapp(request)
        if idc is None:
            return Response({"detail": "No hay idcliente en sesión (seleccione un cliente)."}, status=400)
        sess_user = _session_user(request)
        if not cliente_accesible_por_sesion(base, idc, sess_user):
            return Response({"detail": "Cliente no disponible para esta sesión."}, status=403)
        lim = to_int_or_none(request.data.get("limit")) or 500
        rows = listar_pedidos_cuenta_corriente_relay(
            base,
            dict(request.data),
            sess_user,
            idc,
            limit=lim,
        )
        return Response({"total": len(rows), "filas": rows})


class CuentaCorrientePedidosSugerenciasNroRelayAPIView(APIView):
    """
    GET ``/ecom/api/mayoristapp/ctacte/pedidos/sugerencias-nro/?ajax=1&q=…``

    Paridad ``queryString`` en ``relay-cuenta-corriente.php`` (solo PED del cliente).
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        if "ajax" not in request.query_params:
            return Response({"detail": "Parámetro ajax requerido."}, status=400)
        idc = leer_idcliente_mayoristapp(request)
        if idc is None:
            return Response({"detail": "No hay idcliente en sesión."}, status=400)
        sess_user = _session_user(request)
        if not cliente_accesible_por_sesion(base, idc, sess_user):
            return Response({"detail": "Cliente no disponible."}, status=403)
        q = request.query_params.get("q") or request.query_params.get("queryString") or ""
        nums = sugerencias_nro_pedido_cuenta_corriente_relay(base, q, idc)
        return Response({"sugerencias": nums, "total": len(nums)})


class ConsumosResumenRelayAPIView(APIView):
    """
    POST ``/ecom/api/mayoristapp/ctacte/consumos-resumen/?ajax=1``

    Paridad ``relay-consumos-resumen.php`` (top consumos por cantidad + precio v1).
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        if "ajax" not in request.query_params:
            return Response({"detail": "Parámetro ajax requerido."}, status=400)
        idc = leer_idcliente_mayoristapp(request)
        if idc is None:
            return Response({"detail": "No hay idcliente en sesión (seleccione un cliente)."}, status=400)
        sess_user = _session_user(request)
        if not cliente_accesible_por_sesion(base, idc, sess_user):
            return Response({"detail": "Cliente no disponible para esta sesión."}, status=403)

        bag = (getattr(request, "session", None) or {}).get("mayoristapp") or {}
        iva_raw = bag.get("iva_incluido")
        if iva_raw is None:
            iva_raw = (getattr(request, "session", None) or {}).get("ivaIncluido")
        if iva_raw is None:
            iva_raw = "no"

        kwargs_precio: dict = {}
        cli = leer_cliente_seleccionado(request)
        if isinstance(cli, list) and len(cli) >= 1 and isinstance(cli[0], dict):
            d = cli[0]
            lp = d.get("listaPrecio")
            if lp is not None and str(lp).strip():
                kwargs_precio["lista_precio_cliente"] = lp
            if "descRenglon" in d:
                kwargs_precio["descuento_renglon"] = to_decimal_or_none(d.get("descRenglon")) or Decimal("0")
            if "TipoCliente" in d:
                kwargs_precio["tipo_cliente"] = d.get("TipoCliente")

        lim = to_int_or_none(request.data.get("limit")) or 20
        rows, adv = listar_consumos_resumen_relay(
            base,
            idc,
            iva_incluido_sesion=str(iva_raw),
            fecha_desde=request.data.get("fechaDesde"),
            fecha_hasta=request.data.get("fechaHasta"),
            limit=lim,
            **kwargs_precio,
        )
        return Response({"total": len(rows), "filas": rows, "advertencia_precios": adv})
