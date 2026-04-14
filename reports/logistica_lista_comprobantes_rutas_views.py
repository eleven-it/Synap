"""
APIs auxiliares — Lista comprobantes en rutas (informe legacy Reports).
"""
from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from reports.permissions import ManagerialReportsPermission, OperationalReportsPermission
from reports.services.connection_pool import get_mysql_pool
from reports.services.logistica_lista_comprobantes_rutas import (
    autocomplete_clientes,
    detalle_no_entrega_cumple,
    guardar_entrega,
    listar_motivos_no_entrega_catalogo,
    listar_motivos_no_entrega_descripciones,
    motivo_no_entrega_es_valido,
    obtener_detalle_remito,
)
from core.utils.administranet_types import str_or_default, to_int_or_none

logger = logging.getLogger(__name__)


def _base_empresa_request(request) -> str | None:
    u = request.session.get("user") or {}
    be = (u.get("base_empresa") or "").strip()
    return be or None


def _id_usuario_request(request) -> int | None:
    u = request.session.get("user") or {}
    return to_int_or_none(u.get("id_usuario"))


class _LogisticaListaComprobantesBaseAPIView(APIView):
    permission_classes = [OperationalReportsPermission | ManagerialReportsPermission]


class LogisticaListaComprobantesClientesAutocompleteAPIView(_LogisticaListaComprobantesBaseAPIView):
    """GET …/clientes/autocomplete/?q="""

    def get(self, request, *args, **kwargs):
        base = _base_empresa_request(request)
        if not base:
            return Response({"detail": "Falta base_empresa en la sesión."}, status=status.HTTP_400_BAD_REQUEST)
        q = str_or_default(request.query_params.get("q"), "")
        if len(q) < 2:
            return Response({"results": []})
        try:
            pool = get_mysql_pool()
            with pool.get_connection(base) as conn:
                results = autocomplete_clientes(conn, q)
            return Response({"results": results})
        except Exception as exc:
            logger.exception("autocomplete clientes logística: %s", exc)
            return Response(
                {"detail": "Error al buscar clientes."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LogisticaListaComprobantesRemitoDetalleAPIView(_LogisticaListaComprobantesBaseAPIView):
    """GET …/remito/<cod_mov>/"""

    def get(self, request, cod_mov, *args, **kwargs):
        base = _base_empresa_request(request)
        if not base:
            return Response({"detail": "Falta base_empresa en la sesión."}, status=status.HTTP_400_BAD_REQUEST)
        cod = to_int_or_none(cod_mov)
        if cod is None:
            return Response({"detail": "Código de movimiento inválido."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            pool = get_mysql_pool()
            with pool.get_connection(base) as conn:
                data = obtener_detalle_remito(conn, cod)
            if not data:
                return Response({"msg": "error", "detail": "Remito no encontrado."}, status=status.HTTP_404_NOT_FOUND)
            return Response({"msg": "ok", "data": data})
        except Exception as exc:
            logger.exception("detalle remito logística: %s", exc)
            return Response(
                {"msg": "error", "detail": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LogisticaListaComprobantesEntregaAPIView(_LogisticaListaComprobantesBaseAPIView):
    """
    POST …/entrega/
    Body JSON: cod_mov_remito, cod_mov_pedido, entregado (Si|No), motivo_no_entrega?, detalle_no_entrega?
    """

    def post(self, request, *args, **kwargs):
        base = _base_empresa_request(request)
        id_u = _id_usuario_request(request)
        if not base:
            return Response({"detail": "Falta base_empresa en la sesión."}, status=status.HTTP_400_BAD_REQUEST)
        if id_u is None:
            return Response({"detail": "Falta id_usuario en la sesión."}, status=status.HTTP_400_BAD_REQUEST)

        body = request.data if isinstance(request.data, dict) else {}
        cod_r = to_int_or_none(body.get("cod_mov_remito"))
        cod_p = to_int_or_none(body.get("cod_mov_pedido"))
        ent = str_or_default(body.get("entregado"), "").strip()
        motivo = str_or_default(body.get("motivo_no_entrega"), "")
        detalle = str_or_default(body.get("detalle_no_entrega"), "")

        if cod_r is None or cod_p is None:
            return Response(
                {"msg": "error", "detail": "cod_mov_remito y cod_mov_pedido son obligatorios."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if ent not in ("Si", "No"):
            return Response(
                {"msg": "error", "detail": "entregado debe ser Si o No."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if ent == "No" and not motivo.strip():
            return Response(
                {"msg": "error", "detail": "Si no está entregado, debe indicar el motivo."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            pool = get_mysql_pool()
            with pool.get_connection(base) as conn:
                if ent == "No" and not motivo_no_entrega_es_valido(conn, motivo):
                    return Response(
                        {"msg": "error", "detail": "Motivo de no entrega no válido."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if ent == "No" and not detalle_no_entrega_cumple(conn, motivo, detalle):
                    return Response(
                        {
                            "msg": "error",
                            "detail": "Este motivo requiere un comentario en el detalle.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                guardar_entrega(
                    conn,
                    cod_mov_remito=cod_r,
                    cod_mov_pedido=cod_p,
                    entregado=ent,
                    id_usuario_sesion=id_u,
                    motivo_no_entrega=motivo,
                    detalle_no_entrega=detalle,
                )
            return Response({"msg": "ok", "mensaje": "Datos guardados correctamente."})
        except ValueError as ve:
            return Response({"msg": "error", "detail": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception("guardar entrega logística: %s", exc)
            return Response(
                {"msg": "error", "detail": "Error al guardar. Intente nuevamente."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LogisticaListaComprobantesMotivosAPIView(_LogisticaListaComprobantesBaseAPIView):
    """GET …/motivos-no-entrega/ — catálogo MySQL ``logi_motivo_no_entrega`` o respaldo legado."""

    def get(self, request, *args, **kwargs):
        base = _base_empresa_request(request)
        if not base:
            return Response({"detail": "Falta base_empresa en la sesión."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            pool = get_mysql_pool()
            with pool.get_connection(base) as conn:
                catalogo = listar_motivos_no_entrega_catalogo(conn)
                textos = listar_motivos_no_entrega_descripciones(conn)
            out = [
                {
                    "id": x.get("id"),
                    "descripcion": x["descripcion"],
                    "requiere_detalle": x.get("requiere_detalle", False),
                    "visible_portal": x.get("visible_portal", False),
                }
                for x in catalogo
            ]
            return Response({"motivos": textos, "motivos_catalogo": out})
        except Exception as exc:
            logger.exception("motivos no entrega logística: %s", exc)
            return Response(
                {"detail": "Error al cargar motivos."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
