"""API ABM jerarquía comercial Gerente→Supervisor→Vendedor."""

from __future__ import annotations

from typing import Any, Dict

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.administranet_types import to_int_or_none
from ecom.catalogo_producto_relay_views import _session_base_empresa
from ecom.permissions import EcomJerarquiaEditarPermission
from ecom.services.jerarquia_comercial import (
    desactivar_vinculo_gerente_supervisor,
    desactivar_vinculo_supervisor_vendedor,
    listar_arbol_jerarquia,
    vincular_gerente_supervisor,
    vincular_supervisor_vendedor,
)


class JerarquiaNodosAPIView(APIView):
    """GET/POST ``/ecom/api/mayoristapp/jerarquia/nodos/`` — ABM árbol org."""

    permission_classes = [EcomJerarquiaEditarPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"ok": False, "error": "Sin base_empresa."}, status=400)
        arbol = listar_arbol_jerarquia(base)
        return Response({"ok": True, "arbol": arbol})

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"ok": False, "error": "Sin base_empresa."}, status=400)
        data: Dict[str, Any] = request.data if isinstance(request.data, dict) else {}
        accion = str(data.get("accion") or "").strip().lower()

        if accion == "vincular_gerente_supervisor":
            ok, msg = vincular_gerente_supervisor(
                base,
                to_int_or_none(data.get("cod_gerente")),
                to_int_or_none(data.get("cod_supervisor")),
            )
        elif accion == "vincular_supervisor_vendedor":
            ok, msg = vincular_supervisor_vendedor(
                base,
                to_int_or_none(data.get("cod_supervisor")),
                to_int_or_none(data.get("cod_vendedor")),
            )
        elif accion == "desactivar_gerente_supervisor":
            ok, msg = desactivar_vinculo_gerente_supervisor(
                base, to_int_or_none(data.get("cod_supervisor"))
            )
        elif accion == "desactivar_supervisor_vendedor":
            ok, msg = desactivar_vinculo_supervisor_vendedor(
                base, to_int_or_none(data.get("cod_vendedor"))
            )
        else:
            return Response(
                {
                    "ok": False,
                    "error": (
                        "Acción inválida. Use: vincular_gerente_supervisor, "
                        "vincular_supervisor_vendedor, desactivar_gerente_supervisor, "
                        "desactivar_supervisor_vendedor."
                    ),
                },
                status=400,
            )

        if not ok:
            return Response({"ok": False, "error": msg}, status=400)
        return Response({"ok": True, "message": msg, "arbol": listar_arbol_jerarquia(base)})
