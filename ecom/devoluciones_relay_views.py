"""
API relay-devoluciones.php (solo lectura por plan).
"""

from __future__ import annotations

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ecom.permissions import EcomMayoristappSessionPermission
from ecom.services.devoluciones_relay import (
    listar_devoluciones_relay,
    sugerencias_nro_devoluciones_relay,
)
from ecom.services.filtros_estadisticas_relay import listado_filtros_estadisticas
from ecom.services.mayoristapp_session import leer_idcliente_mayoristapp
from ecom.services.cliente_relay import cod_viajante_desde_sesion_usuario
from core.utils.administranet_types import to_int_or_none


def _session_base_empresa(request: Request) -> str | None:
    data = (getattr(request, "session", None) or {}).get("user") or {}
    be = data.get("base_empresa")
    return str(be).strip() if be else None


def _session_user(request: Request) -> dict:
    return (getattr(request, "session", None) or {}).get("user") or {}


class DevolucionesRelayAPIView(APIView):
    """
    POST ``/ecom/api/mayoristapp/estadisticas/devoluciones/?ajax=1``
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        if "ajax" not in request.query_params:
            return Response({"detail": "Parámetro ajax requerido."}, status=400)

        body = dict(request.data)
        accion = str(body.get("queAccion") or "").strip().lower()
        sess = getattr(request, "session", None) or {}
        usa = str(sess.get("usa_id_manual") or "").strip().lower() == "si"
        vend_cargo = sess.get("vendedor_a_cargo") or []
        try:
            arr_v = [int(x) for x in vend_cargo if str(x).strip() != ""]
        except Exception:
            arr_v = []

        if accion == "seleccion":
            tabla = str(body.get("tabla") or "").strip()
            if not tabla:
                return Response({"detail": "Parámetro tabla requerido para selección."}, status=400)
            opciones = listado_filtros_estadisticas(
                base_empresa=base,
                tabla=tabla,
                usa_id_manual=usa,
                arr_vend_cargo=arr_v,
            )
            return Response({"total": len(opciones), "opciones": opciones})

        if accion == "listar":
            lim = to_int_or_none(body.get("limit")) or 500
            rows = listar_devoluciones_relay(
                base_empresa=base,
                body=body,
                usa_id_manual=usa,
                limit=lim,
            )
            return Response({"total": len(rows), "filas": rows})

        if accion == "procesar":
            return Response(
                {"msg": "error", "error": "Acción procesar bloqueada por plan (solo lectura)."},
                status=409,
            )

        return Response({"detail": "queAccion inválido. Use seleccion|listar."}, status=400)


class DevolucionesSugerenciasNroRelayAPIView(APIView):
    """
    GET ``/ecom/api/mayoristapp/estadisticas/devoluciones/sugerencias-nro/?ajax=1&q=...``
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        if "ajax" not in request.query_params:
            return Response({"detail": "Parámetro ajax requerido."}, status=400)
        q = request.query_params.get("q") or request.query_params.get("queryString") or ""
        su = _session_user(request)
        tipousuario = str(su.get("tipousuario") or "")
        nums = sugerencias_nro_devoluciones_relay(
            base_empresa=base,
            query_string=q,
            tipousuario=tipousuario,
            cod_viajante=cod_viajante_desde_sesion_usuario(su),
            idcliente=leer_idcliente_mayoristapp(request),
        )
        return Response({"sugerencias": nums, "total": len(nums)})

