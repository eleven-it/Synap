"""
API JSON — Logística · Entregas (misma lógica que informe ``comprobantes-rutas``).
Permiso: ``logistica_editar_entregas`` (no exige permisos de Reports).
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.administranet_types import str_or_default, to_int_or_none
from logistica.permissions import LogisticaEntregasPermission
from logistica.services.lista_comprobantes_rutas import (
    autocomplete_clientes,
    detalle_no_entrega_cumple,
    ejecutar_listado,
    guardar_entrega,
    ids_chofer_vinculados_a_usuario,
    listar_choferes_catalogo_entregas,
    listar_motivos_no_entrega_catalogo,
    listar_motivos_no_entrega_descripciones,
    listar_rutas_catalogo_entregas,
    motivo_no_entrega_es_valido,
    obtener_detalle_remito,
    usuario_tiene_vinculo_chofer_abm,
    usuario_puede_filtrar_por_chofer_en_catalogo,
)
from reports.services.connection_pool import get_mysql_pool

logger = logging.getLogger(__name__)

# Sesión Django: ruta elegida por defecto para filtros de Entregas (hasta cerrar sesión).
SESSION_ENTREGAS_ID_RUTA = "logistica_entregas_id_ruta"

# Claves de importe devueltas por el listado/detalle MySQL (no exponer al chofer en Entregas).
_IMPORTE_KEYS_LOWER = frozenset(
    {
        "total_remito",
        "totalremito",
        "total_pedido",
        "totalpedido",
        "total_factura",
        "totalfactura",
    }
)


def _dict_sin_importes(d: Dict[str, Any]) -> Dict[str, Any]:
    """Quita montos del payload (pantalla Entregas: el chofer no debe ver el valor de la carga)."""
    if not d:
        return d
    return {k: v for k, v in d.items() if str(k).lower() not in _IMPORTE_KEYS_LOWER}


def _base_empresa_session(request) -> str | None:
    u = request.session.get("user") or {}
    be = (u.get("base_empresa") or "").strip()
    return be or None


def _id_usuario_session(request) -> int | None:
    u = request.session.get("user") or {}
    return to_int_or_none(u.get("id_usuario"))


def _filtros_lista_desde_request(request) -> Dict[str, Any]:
    """Construye ``filters`` para ``ejecutar_listado`` (modo Hoy / Mi ruta + opcionales)."""
    modo = str_or_default(request.query_params.get("modo"), "hoy").strip().lower()
    if modo not in ("hoy", "mi_ruta"):
        modo = "hoy"

    filters: Dict[str, Any] = {"logistica_modo": modo}

    if modo == "hoy":
        today = timezone.localdate().isoformat()
        filters["fecha_inicio"] = today
        filters["fecha_fin"] = today

    est = str_or_default(request.query_params.get("estado"), "").strip()
    if est in ("Si", "No"):
        filters["logistica_estado_entrega"] = [est]

    cli = str_or_default(request.query_params.get("cliente"), "").strip()
    if cli:
        filters["logistica_id_cliente"] = [cli]

    return filters


class LogisticaEntregasCatalogosAPIView(APIView):
    """GET ``…/catalogos/`` — rutas; combo de chofer solo si aplica (supervisor sin alta en ABM chofer)."""

    permission_classes = [LogisticaEntregasPermission]

    def get(self, request, *args, **kwargs):
        base = _base_empresa_session(request)
        id_u = _id_usuario_session(request)
        if not base:
            return Response(
                {"detail": "Falta base_empresa en la sesión."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            pool = get_mysql_pool()
            with pool.get_connection(base) as conn:
                puede_supervisor = (
                    usuario_puede_filtrar_por_chofer_en_catalogo(conn, id_u)
                    if id_u is not None
                    else False
                )
                ids_v = ids_chofer_vinculados_a_usuario(conn, id_u) if id_u is not None else []
                tiene_vinculo_chofer = len(ids_v) > 0
                puede_mostrar_combo_chofer = puede_supervisor and not tiene_vinculo_chofer

                if tiene_vinculo_chofer:
                    ids_ch = ids_v
                elif puede_supervisor:
                    id_ch_param = to_int_or_none(
                        str_or_default(request.query_params.get("id_chofer"), "").strip()
                    )
                    ids_ch = [id_ch_param] if id_ch_param is not None else []
                else:
                    ids_ch = []

                rutas = listar_rutas_catalogo_entregas(conn, ids_ch)
                choferes = (
                    listar_choferes_catalogo_entregas(conn) if puede_mostrar_combo_chofer else []
                )

                ids_validos = {to_int_or_none(r.get("id")) for r in rutas}
                id_sess = to_int_or_none(request.session.get(SESSION_ENTREGAS_ID_RUTA))
                if id_sess is not None and id_sess not in ids_validos:
                    request.session.pop(SESSION_ENTREGAS_ID_RUTA, None)
                    request.session.modified = True

            id_ruta_sesion = to_int_or_none(request.session.get(SESSION_ENTREGAS_ID_RUTA))
            return Response(
                {
                    "rutas": rutas,
                    "choferes": choferes,
                    "puede_filtrar_chofer": puede_mostrar_combo_chofer,
                    "id_ruta_sesion": id_ruta_sesion,
                }
            )
        except Exception as exc:
            logger.exception("catalogos entregas logística: %s", exc)
            return Response(
                {"detail": "Error al cargar catálogos."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LogisticaEntregasListaAPIView(APIView):
    """GET ``…/lista/?modo=hoy|mi_ruta`` — filas del listado operativo."""

    permission_classes = [LogisticaEntregasPermission]

    def get(self, request, *args, **kwargs):
        base = _base_empresa_session(request)
        id_u = _id_usuario_session(request)
        if not base:
            return Response(
                {"detail": "Falta base_empresa en la sesión."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        filters = _filtros_lista_desde_request(request)
        filters["logistica_contexto_entregas"] = True

        qp_ruta = request.query_params.get("id_ruta")
        if qp_ruta is not None:
            raw = str_or_default(qp_ruta, "").strip()
            if raw == "":
                request.session.pop(SESSION_ENTREGAS_ID_RUTA, None)
            else:
                rid = to_int_or_none(raw)
                if rid is not None:
                    request.session[SESSION_ENTREGAS_ID_RUTA] = rid
            request.session.modified = True

        id_ruta_filtr: int | None
        if qp_ruta is not None:
            id_ruta_filtr = to_int_or_none(str_or_default(qp_ruta, "").strip())
        else:
            id_ruta_filtr = to_int_or_none(request.session.get(SESSION_ENTREGAS_ID_RUTA))

        if id_ruta_filtr is not None:
            filters["logistica_id_ruta"] = id_ruta_filtr

        puede_supervisor = False
        puede_mostrar_combo_chofer = False
        try:
            pool = get_mysql_pool()
            with pool.get_connection(base) as conn:
                if id_u is not None:
                    puede_supervisor = usuario_puede_filtrar_por_chofer_en_catalogo(conn, id_u)
                    tiene_vinculo_chofer = usuario_tiene_vinculo_chofer_abm(conn, id_u)
                    puede_mostrar_combo_chofer = puede_supervisor and not tiene_vinculo_chofer
                id_ch = to_int_or_none(str_or_default(request.query_params.get("id_chofer"), "").strip())
                if puede_mostrar_combo_chofer and id_ch is not None:
                    filters["logistica_aplicar_filtro_chofer_id"] = True
                    filters["logistica_id_chofer"] = id_ch

                data, notas = ejecutar_listado(conn, filters, id_u)
            filas = [_dict_sin_importes(row) for row in data]
            id_ruta_sesion = to_int_or_none(request.session.get(SESSION_ENTREGAS_ID_RUTA))
            return Response(
                {
                    "ok": True,
                    "modo": filters.get("logistica_modo"),
                    "filas": filas,
                    "notas": notas,
                    "total": len(filas),
                    "id_ruta_sesion": id_ruta_sesion,
                    "puede_filtrar_chofer": puede_mostrar_combo_chofer,
                }
            )
        except Exception as exc:
            logger.exception("lista entregas logística: %s", exc)
            return Response(
                {"ok": False, "detail": "Error al cargar el listado."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LogisticaEntregasRemitoDetalleAPIView(APIView):
    """
    GET ``…/remito/<cod_mov>/`` — compatibilidad (redirecciones legacy /ecom/…).
    No se usa desde la pantalla Entregas.
    """

    permission_classes = [LogisticaEntregasPermission]

    def get(self, request, cod_mov, *args, **kwargs):
        base = _base_empresa_session(request)
        if not base:
            return Response(
                {"detail": "Falta base_empresa en la sesión."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        cod = to_int_or_none(cod_mov)
        if cod is None:
            return Response(
                {"detail": "Código de movimiento inválido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            pool = get_mysql_pool()
            with pool.get_connection(base) as conn:
                data = obtener_detalle_remito(conn, cod)
            if not data:
                return Response(
                    {"msg": "error", "detail": "Remito no encontrado."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response({"msg": "ok", "data": _dict_sin_importes(data)})
        except Exception as exc:
            logger.exception("detalle remito entregas: %s", exc)
            return Response(
                {"msg": "error", "detail": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LogisticaEntregasEntregaAPIView(APIView):
    """POST ``…/entrega/`` — persistir entrega (misma carga útil que Reports)."""

    permission_classes = [LogisticaEntregasPermission]

    def post(self, request, *args, **kwargs):
        base = _base_empresa_session(request)
        id_u = _id_usuario_session(request)
        if not base:
            return Response(
                {"detail": "Falta base_empresa en la sesión."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if id_u is None:
            return Response(
                {"detail": "Falta id_usuario en la sesión."},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
            logger.exception("guardar entrega (logistica): %s", exc)
            return Response(
                {"msg": "error", "detail": "Error al guardar. Intente nuevamente."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LogisticaEntregasMotivosAPIView(APIView):
    permission_classes = [LogisticaEntregasPermission]

    def get(self, request, *args, **kwargs):
        base = _base_empresa_session(request)
        if not base:
            return Response(
                {"detail": "Falta base_empresa en la sesión."},
                status=status.HTTP_400_BAD_REQUEST,
            )
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
            logger.exception("motivos entregas logística: %s", exc)
            return Response(
                {"detail": "Error al cargar motivos."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LogisticaEntregasClientesAutocompleteAPIView(APIView):
    permission_classes = [LogisticaEntregasPermission]

    def get(self, request, *args, **kwargs):
        base = _base_empresa_session(request)
        if not base:
            return Response(
                {"detail": "Falta base_empresa en la sesión."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        q = str_or_default(request.query_params.get("q"), "")
        if len(q) < 2:
            return Response({"results": []})
        try:
            pool = get_mysql_pool()
            with pool.get_connection(base) as conn:
                results = autocomplete_clientes(conn, q)
            return Response({"results": results})
        except Exception as exc:
            logger.exception("autocomplete clientes entregas: %s", exc)
            return Response(
                {"detail": "Error al buscar clientes."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
