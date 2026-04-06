"""
API relay-filtros-estadisticas.php (modo solo lectura).
"""

from __future__ import annotations

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ecom.permissions import EcomMayoristappSessionPermission
from ecom.services.filtros_estadisticas_relay import listado_filtros_estadisticas


def _session_base_empresa(request: Request) -> str | None:
    data = (getattr(request, "session", None) or {}).get("user") or {}
    be = data.get("base_empresa")
    return str(be).strip() if be else None


class FiltrosEstadisticasRelayAPIView(APIView):
    """
    GET/POST ``/ecom/api/mayoristapp/estadisticas/filtros/?ajax=1&tabla=...``
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> Response:
        return self._run(request)

    def post(self, request: Request) -> Response:
        return self._run(request)

    def _run(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        tabla = (request.query_params.get("tabla") or request.data.get("tabla") or "").strip()
        if not tabla:
            return Response({"detail": "Parámetro tabla requerido."}, status=400)
        sess = getattr(request, "session", None) or {}
        usa = str(sess.get("usa_id_manual") or "").strip().lower() == "si"
        vend_cargo = sess.get("vendedor_a_cargo") or []
        try:
            arr_v = [int(x) for x in vend_cargo if str(x).strip() != ""]
        except Exception:
            arr_v = []
        opciones = listado_filtros_estadisticas(
            base_empresa=base,
            tabla=tabla,
            usa_id_manual=usa,
            arr_vend_cargo=arr_v,
        )
        return Response({"total": len(opciones), "opciones": opciones})

