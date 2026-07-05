"""
Catálogos GET para alta de recibo mayoristapp.
"""

from __future__ import annotations

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ecom.permissions import EcomMayoristappSessionPermission
from ecom.services.mayoristapp_session import leer_idcliente_mayoristapp
from ecom.services.recibo_catalogos_service import (
    listar_cuentas_bancarias,
    listar_planes_tarjeta,
    listar_puntos_venta_usuario,
    listar_tarjetas,
    listar_tipos_retencion,
    traer_caja_efectivo_usuario,
    traer_cotizacion_dolar,
    traer_saldo_a_cuenta_cliente,
)
from ecom.services.recibo_saldo_favor_service import listar_lineas_saldo_favor


def _session_base_empresa(request: Request) -> str | None:
    data = (getattr(request, "session", None) or {}).get("user") or {}
    be = data.get("base_empresa")
    return str(be).strip() if be else None


class ReciboAltaCatalogosRelayAPIView(APIView):
    """
    GET ``/ecom/api/mayoristapp/recibos/alta/catalogos/?ajax=1&tipo=...``
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> Response:
        if "ajax" not in request.query_params:
            return Response({"detail": "Parámetro ajax requerido."}, status=400)
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)

        session_user = dict(request.session.get("user") or {})
        tipo = (request.query_params.get("tipo") or "").strip().lower()

        if tipo in ("", "puntos-venta"):
            return Response({"msg": "ok", "puntos_venta": listar_puntos_venta_usuario(base, session_user)})
        if tipo == "cotizacion-dolar":
            return Response({"msg": "ok", "valor": traer_cotizacion_dolar(base)})
        if tipo == "caja-efectivo":
            return Response({"msg": "ok", "caja": traer_caja_efectivo_usuario(base, session_user)})
        if tipo == "saldo-a-cuenta":
            idc = leer_idcliente_mayoristapp(request)
            if idc is None:
                return Response({"detail": "No hay idcliente en sesión."}, status=400)
            return Response(traer_saldo_a_cuenta_cliente(base, idc))
        if tipo == "lineas-saldo-a-cuenta":
            idc = leer_idcliente_mayoristapp(request)
            if idc is None:
                return Response({"detail": "No hay idcliente en sesión."}, status=400)
            return Response({"msg": "ok", "lineas": listar_lineas_saldo_favor(base, idc)})
        if tipo == "retenciones":
            return Response({"msg": "ok", "retenciones": listar_tipos_retencion(base)})
        if tipo == "cuentas-bancarias":
            return Response({"msg": "ok", "cuentas": listar_cuentas_bancarias(base)})
        if tipo.startswith("tarjetas"):
            sub = request.query_params.get("subtipo") or "Credito"
            return Response({"msg": "ok", "tarjetas": listar_tarjetas(base, sub)})
        if tipo == "planes-tarjeta":
            id_tc = request.query_params.get("idTC")
            if not id_tc:
                return Response({"detail": "idTC requerido."}, status=400)
            return Response({"msg": "ok", "planes": listar_planes_tarjeta(base, int(id_tc))})

        return Response({"detail": "Catálogo no soportado."}, status=400)
