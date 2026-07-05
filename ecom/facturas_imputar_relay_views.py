"""
APIs facturas para imputar mayoristapp (``relay_facturas_imputar.php``).
"""

from __future__ import annotations

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.administranet_types import to_int_or_none
from ecom.permissions import EcomCobranzasWritePermission, EcomMayoristappSessionPermission
from ecom.services.ecom_module_settings import (
    ecom_cobranzas_write_enabled,
    ecom_imputacion_write_enabled,
)
from ecom.services.facturas_imputar_relay import (
    listar_facturas_imputar_relay,
    sugerencias_nro_facturas_imputar_relay,
)
from ecom.services.mayoristapp_session import leer_idcliente_mayoristapp
from ecom.services.recibo_alta_service import guardar_recibo_mayoristapp
from fe_afip.services.recibo_imputacion_service import (
    desimputar_factura_en_sesion,
    fin_imputacion_sesion,
    imputar_factura_en_sesion,
)


def _session_base_empresa(request: Request) -> str | None:
    data = (getattr(request, "session", None) or {}).get("user") or {}
    be = data.get("base_empresa")
    return str(be).strip() if be else None


class FacturasImputarListadoRelayAPIView(APIView):
    """
    POST ``/ecom/api/mayoristapp/fe/facturas-imputar/listado/?ajax=1``
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
            return Response({"detail": "No hay idcliente en sesión."}, status=400)
        lim = to_int_or_none(request.data.get("limit")) or 60
        rows = listar_facturas_imputar_relay(base, dict(request.data), idc, limit=lim)
        return Response({"total": len(rows), "filas": rows})


class FacturasImputarSugerenciasNroRelayAPIView(APIView):
    """
    GET ``/ecom/api/mayoristapp/fe/facturas-imputar/sugerencias-nro/?ajax=1&q=...``
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
        q = request.query_params.get("q") or request.query_params.get("queryString") or ""
        nums = sugerencias_nro_facturas_imputar_relay(base, q, idc)
        return Response({"sugerencias": nums, "total": len(nums)})


class FacturasImputarAccionRelayAPIView(APIView):
    """
    POST ``/ecom/api/mayoristapp/fe/facturas-imputar/accion/?ajax=1``

    Paridad de acciones de json_recibo.php:
    - imputarFactura=1
    - desimputarFactura=1
    - finImputacion=1
    - guardarRecibo=1 (delegado a guardar_recibo_mayoristapp)
    """

    permission_classes = [EcomMayoristappSessionPermission, EcomCobranzasWritePermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        if "ajax" not in request.query_params:
            return Response({"detail": "Parámetro ajax requerido."}, status=400)
        if not ecom_imputacion_write_enabled():
            return Response(
                {
                    "msg": "error",
                    "error": "Acciones de escritura FE/imputación deshabilitadas (módulo ecom).",
                },
                status=409,
            )
        idc = leer_idcliente_mayoristapp(request)
        if idc is None:
            return Response({"detail": "No hay idcliente en sesión."}, status=400)

        body = dict(request.data)
        if str(body.get("imputarFactura") or "") == "1":
            data = imputar_factura_en_sesion(
                request.session,
                idcliente=idc,
                payload=body,
            )
            request.session.modified = True
            return Response(data, status=200 if data.get("msg") == "ok" else 400)

        if str(body.get("desimputarFactura") or "") == "1":
            data = desimputar_factura_en_sesion(
                request.session,
                idrecibofactura=body.get("idrecibofactura"),
            )
            request.session.modified = True
            return Response(data, status=200 if data.get("msg") == "ok" else 400)

        if str(body.get("finImputacion") or "") == "1":
            data = fin_imputacion_sesion(request.session)
            request.session.modified = True
            return Response(data)

        if str(body.get("guardarRecibo") or "") == "1":
            if not ecom_cobranzas_write_enabled():
                return Response(
                    {
                        "msg": "error",
                        "error": "Escritura de recibo deshabilitada por configuración.",
                    },
                    status=409,
                )
            try:
                data = guardar_recibo_mayoristapp(
                    base_empresa=base,
                    session_user=(request.session.get("user") or {}),
                    session=request.session,
                )
            except Exception as exc:
                return Response({"msg": "error", "desc": str(exc)}, status=400)
            request.session.modified = True
            return Response(data)

        return Response({"detail": "Acción no soportada."}, status=400)
