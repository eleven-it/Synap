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
    buscar_usuarios_jerarquia,
    desactivar_vinculo_gerente_supervisor,
    desactivar_vinculo_supervisor_vendedor,
    listar_arbol_jerarquia,
    vincular_gerente_supervisor,
    vincular_supervisor_vendedor,
    vincular_supervisor_vendedores_batch,
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

        mover = bool(data.get("mover"))
        if accion == "vincular_gerente_supervisor":
            ok, msg = vincular_gerente_supervisor(
                base,
                to_int_or_none(data.get("cod_gerente")),
                to_int_or_none(data.get("cod_supervisor")),
                mover=mover,
                id_usuario_gerente=to_int_or_none(data.get("id_usuario_gerente")),
                id_usuario_supervisor=to_int_or_none(data.get("id_usuario_supervisor")),
            )
        elif accion == "vincular_supervisor_vendedor":
            vendedores = data.get("cod_vendedores")
            if isinstance(vendedores, list):
                ok, msg = vincular_supervisor_vendedores_batch(
                    base,
                    to_int_or_none(data.get("cod_supervisor")),
                    vendedores,
                    id_usuario_supervisor=to_int_or_none(data.get("id_usuario_supervisor")),
                )
            else:
                ok, msg = vincular_supervisor_vendedor(
                    base,
                    to_int_or_none(data.get("cod_supervisor")),
                    to_int_or_none(data.get("cod_vendedor")),
                    mover=mover,
                    id_usuario_supervisor=to_int_or_none(data.get("id_usuario_supervisor")),
                )
        elif accion == "desactivar_gerente_supervisor":
            ok, msg = desactivar_vinculo_gerente_supervisor(
                base,
                to_int_or_none(data.get("cod_supervisor")),
                id_usuario_supervisor=to_int_or_none(data.get("id_usuario_supervisor")),
            )
        elif accion == "desactivar_supervisor_vendedor":
            ok, msg = desactivar_vinculo_supervisor_vendedor(
                base,
                to_int_or_none(data.get("cod_vendedor")),
                to_int_or_none(data.get("cod_supervisor")),
                id_usuario_supervisor=to_int_or_none(data.get("id_usuario_supervisor")),
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


class JerarquiaUsuariosAPIView(APIView):
    """GET ``/ecom/api/mayoristapp/jerarquia/usuarios/?q=`` — búsqueda predictiva."""

    permission_classes = [EcomJerarquiaEditarPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"ok": False, "error": "Sin base_empresa."}, status=400)
        q = str(request.query_params.get("q") or "").strip()
        limit = to_int_or_none(request.query_params.get("limit")) or 20
        rol = str(
            request.query_params.get("rol")
            or request.query_params.get("campo")
            or "gerente"
        ).strip()
        resultados = buscar_usuarios_jerarquia(base, q, rol=rol, limit=limit)
        return Response(
            {
                "ok": True,
                "results": resultados,
                "total": len(resultados),
                "rol": rol,
            }
        )