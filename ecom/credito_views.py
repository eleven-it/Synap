"""Vistas y APIs del workflow de crédito en pedidos."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional

import MySQLdb
from django.urls import reverse
from django.views.generic import TemplateView
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.mysql_pool import get_connection, mysql_cursor
from core.utils.administranet_types import str_or_default, to_decimal_or_none, to_int_or_none
from ecom.catalogo_producto_relay_views import _session_base_empresa
from ecom.permissions import (
    EcomMayoristappSessionPermission,
    puede_aprobar_credito,
    puede_configurar_credito,
)
from ecom.pedido_masivo_stub_views import _StubMayoristappPermisoView
from ecom.services.credito_pedidos.aprobacion import listar_pendientes_finanzas, resolver_finanzas
from ecom.services.credito_pedidos.evaluacion import evaluar_pedido, resultado_credito_a_dict
from ecom.services.ecom_config_mysql import credito_pedidos_activo


CANALES_CREDITO_ADMITIDOS = {"PED", "PRE"}


def _validar_canal_credito(canal: str) -> Optional[Response]:
    """V1 solo opera políticas y avisos para pedidos y presupuestos."""
    if canal not in CANALES_CREDITO_ADMITIDOS:
        return Response(
            {
                "ok": False,
                "error": "El canal de crédito debe ser PED o PRE.",
            },
            status=400,
        )
    return None


class EcomCreditoAprobarPermission(BasePermission):
    message = "Se requiere permiso finance.credito.aprobar."

    def has_permission(self, request, view):
        if not EcomMayoristappSessionPermission().has_permission(request, view):
            return False
        user = getattr(request, "user", None)
        if getattr(user, "is_superuser", False):
            return True
        sess = (getattr(request, "session", None) or {}).get("user") or {}
        return puede_aprobar_credito(sess)


class EcomCreditoConfigurarPermission(BasePermission):
    message = "Se requiere permiso finance.credito.configurar."

    def has_permission(self, request, view):
        if not EcomMayoristappSessionPermission().has_permission(request, view):
            return False
        user = getattr(request, "user", None)
        if getattr(user, "is_superuser", False):
            return True
        sess = (getattr(request, "session", None) or {}).get("user") or {}
        return puede_configurar_credito(sess)


def _session_user(request: Request) -> Dict[str, Any]:
    return (getattr(request, "session", None) or {}).get("user") or {}


def _fetch_cliente_credito(base_empresa: str, id_cliente: int) -> Optional[Dict[str, Any]]:
    sql = """
        SELECT
            cliente.Credito AS Credito,
            cliente.credito_limite_dias AS credito_limite_dias,
            COALESCE(cliente.nombre_cliente, '') AS nombre_cliente
        FROM cliente
        WHERE cliente.Codigo = %s
        LIMIT 1
    """
    with get_connection(base_empresa) as conn:
        cur = conn.cursor(MySQLdb.cursors.DictCursor)
        cur.execute(sql, [id_cliente])
        return cur.fetchone()


class CreditoPreCheckAPIView(APIView):
    """POST ``/ecom/api/credito/pre-check/`` — semáforo en toma (REQ-VTA-10/11)."""

    permission_classes = [EcomMayoristappSessionPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response(
                {"ok": False, "error": "No se encontró base_empresa en la sesión."},
                status=400,
            )

        if not credito_pedidos_activo(base):
            return Response({"ok": True, "activo": False})

        data = request.data if isinstance(request.data, dict) else {}
        id_cliente = to_int_or_none(data.get("id_cliente"))
        if id_cliente is None:
            return Response({"ok": False, "error": "Falta id_cliente."}, status=400)

        canal = str(data.get("canal") or "PED").upper()
        total = to_decimal_or_none(data.get("total_pedido")) or Decimal("0")
        es_cliente = bool(data.get("es_cliente"))

        cli = _fetch_cliente_credito(base, int(id_cliente))
        if not cli:
            return Response({"ok": False, "error": "Cliente no encontrado."}, status=404)

        with get_connection(base) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            resultado = evaluar_pedido(
                cur,
                id_cliente=int(id_cliente),
                canal=canal,
                total_pedido=total,
                credito_cliente=to_decimal_or_none(cli.get("Credito")) or Decimal("0"),
                credito_limite_dias=to_int_or_none(cli.get("credito_limite_dias")) or 0,
                es_cliente=es_cliente,
                persistir=False,
            )

        return Response(
            {
                "ok": True,
                "activo": True,
                "credito": resultado_credito_a_dict(resultado),
            }
        )


class CreditoColaFinanzasView(_StubMayoristappPermisoView):
    """Cola Finanzas — ``/ecom/credito/cola/``."""

    template_name = "ecom/credito/cola_finanzas.html"
    permiso_requerido = "finance.credito.aprobar"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        base = _session_base_empresa(self.request)
        ctx["bootstrap"] = {
            "urls": {
                "api_pendientes": reverse("ecom:api_credito_pendientes"),
                "aprobar_tpl": reverse(
                    "ecom:api_credito_aprobar", kwargs={"cod_mov": 0}
                ).replace("/0/", "/{cod_mov}/"),
                "rechazar_tpl": reverse(
                    "ecom:api_credito_rechazar", kwargs={"cod_mov": 0}
                ).replace("/0/", "/{cod_mov}/"),
                "hub": reverse("ecom:mayoristapp_pedidos_hub"),
            },
            "activo": credito_pedidos_activo(base) if base else False,
        }
        return ctx


class CreditoPoliticaListView(_StubMayoristappPermisoView):
    template_name = "ecom/credito/politica_list.html"
    permiso_requerido = "finance.credito.configurar"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["bootstrap"] = {
            "urls": {
                "nueva": reverse("ecom:credito_politica_nueva"),
                "api": reverse("ecom:api_credito_politicas"),
                "cola": reverse("ecom:credito_cola"),
            }
        }
        return ctx


class CreditoPoliticaFormView(_StubMayoristappPermisoView):
    template_name = "ecom/credito/politica_form.html"
    permiso_requerido = "finance.credito.configurar"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        politica_id = kwargs.get("politica_id")
        ctx["bootstrap"] = {
            "politica_id": politica_id,
            "urls": {
                "api": reverse("ecom:api_credito_politicas"),
                "lista": reverse("ecom:credito_politicas"),
            },
        }
        return ctx


class CreditoPlantillasView(_StubMayoristappPermisoView):
    template_name = "ecom/credito/plantillas.html"
    permiso_requerido = "finance.credito.configurar"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["bootstrap"] = {
            "urls": {
                "api": reverse("ecom:api_credito_plantillas"),
                "politicas": reverse("ecom:credito_politicas"),
            }
        }
        return ctx


class CreditoPendientesAPIView(APIView):
    permission_classes = [EcomCreditoAprobarPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"ok": False, "error": "Sin base_empresa."}, status=400)
        dias = to_int_or_none(request.query_params.get("dias")) or 60
        rows = listar_pendientes_finanzas(base, dias=dias)
        return Response({"ok": True, "total": len(rows), "results": rows})


class CreditoAprobarAPIView(APIView):
    permission_classes = [EcomCreditoAprobarPermission]

    def post(self, request: Request, cod_mov: int) -> Response:
        base = _session_base_empresa(request)
        sess = _session_user(request)
        if not base:
            return Response({"ok": False, "error": "Sin base_empresa."}, status=400)
        data = request.data if isinstance(request.data, dict) else {}
        motivo = str(data.get("motivo") or "").strip() or "Aprobado Finanzas"
        resuelve = to_int_or_none(sess.get("id_usuario")) or to_int_or_none(
            sess.get("CodViajante")
        )
        if resuelve is None:
            return Response({"ok": False, "error": "Usuario resolutor inválido."}, status=400)
        ok, msg, payload = resolver_finanzas(
            base, int(cod_mov), "aprobar", int(resuelve), motivo, sess_user=sess
        )
        if not ok:
            return Response({"ok": False, "error": msg}, status=400)
        return Response({"ok": True, "message": msg, **(payload or {})})


class CreditoRechazarAPIView(APIView):
    permission_classes = [EcomCreditoAprobarPermission]

    def post(self, request: Request, cod_mov: int) -> Response:
        base = _session_base_empresa(request)
        sess = _session_user(request)
        if not base:
            return Response({"ok": False, "error": "Sin base_empresa."}, status=400)
        data = request.data if isinstance(request.data, dict) else {}
        motivo = str(data.get("motivo") or "").strip()
        if not motivo:
            return Response({"ok": False, "error": "Indique el motivo del rechazo."}, status=400)
        resuelve = to_int_or_none(sess.get("id_usuario")) or to_int_or_none(
            sess.get("CodViajante")
        )
        if resuelve is None:
            return Response({"ok": False, "error": "Usuario resolutor inválido."}, status=400)
        ok, msg, payload = resolver_finanzas(
            base, int(cod_mov), "rechazar", int(resuelve), motivo, sess_user=sess
        )
        if not ok:
            return Response({"ok": False, "error": msg}, status=400)
        return Response({"ok": True, "message": msg, **(payload or {})})


class CreditoPoliticasAPIView(APIView):
    permission_classes = [EcomCreditoConfigurarPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"ok": False, "error": "Sin base_empresa."}, status=400)
        sql = """
            SELECT id, id_cliente, canal, limite_dias, activo,
                   capa_cxc, capa_ped_abiertos, capa_remitos_nf, capa_cheques, capa_doc_actual
            FROM ecom_credito_politica
            ORDER BY id_cliente IS NULL, id_cliente, canal
            LIMIT 500
        """
        try:
            with mysql_cursor(base, dict_cursor=True) as cur:
                cur.execute(sql)
                rows = [dict(r) for r in cur.fetchall() or []]
        except Exception as exc:
            return Response({"ok": False, "error": str(exc)}, status=500)
        return Response({"ok": True, "results": rows})

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"ok": False, "error": "Sin base_empresa."}, status=400)
        data = request.data if isinstance(request.data, dict) else {}
        id_cliente = to_int_or_none(data.get("id_cliente"))
        canal = str_or_default(data.get("canal"), "PED").upper()
        limite_dias = to_int_or_none(data.get("limite_dias"))
        activo = "Si" if data.get("activo", True) else "No"
        error_canal = _validar_canal_credito(canal)
        if error_canal:
            return error_canal
        try:
            with mysql_cursor(base) as cur:
                cur.execute(
                    """
                    INSERT INTO ecom_credito_politica
                        (id_cliente, canal, limite_dias, activo,
                         capa_cxc, capa_ped_abiertos, capa_remitos_nf, capa_cheques, capa_doc_actual,
                         incluir_mora, creado_en, actualizado_en)
                    VALUES (%s, %s, %s, %s, 'Si', 'Si', 'No', 'No', 'Si', 'Si', NOW(), NOW())
                    """,
                    (id_cliente, canal, limite_dias, activo),
                )
        except Exception as exc:
            return Response({"ok": False, "error": str(exc)}, status=500)
        return Response({"ok": True, "message": "Política creada."})


class CreditoPlantillasAPIView(APIView):
    permission_classes = [EcomCreditoConfigurarPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"ok": False, "error": "Sin base_empresa."}, status=400)
        sql = """
            SELECT id, id_cliente, canal, tipo_aviso, asunto, activo
            FROM ecom_credito_plantilla_aviso
            ORDER BY tipo_aviso, canal
            LIMIT 200
        """
        try:
            with mysql_cursor(base, dict_cursor=True) as cur:
                cur.execute(sql)
                rows = [dict(r) for r in cur.fetchall() or []]
        except Exception as exc:
            return Response({"ok": False, "error": str(exc)}, status=500)
        return Response({"ok": True, "results": rows})

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"ok": False, "error": "Sin base_empresa."}, status=400)
        data = request.data if isinstance(request.data, dict) else {}
        tipo = str_or_default(data.get("tipo_aviso"), "pedido_bloqueado")
        canal = str_or_default(data.get("canal"), "PED").upper()
        asunto = str_or_default(data.get("asunto"), "Aviso crédito")
        cuerpo = str_or_default(data.get("cuerpo"), "")
        id_cliente = to_int_or_none(data.get("id_cliente"))
        error_canal = _validar_canal_credito(canal)
        if error_canal:
            return error_canal
        try:
            with mysql_cursor(base) as cur:
                cur.execute(
                    """
                    INSERT INTO ecom_credito_plantilla_aviso
                        (id_cliente, canal, tipo_aviso, asunto, cuerpo, activo, creado_en, actualizado_en)
                    VALUES (%s, %s, %s, %s, %s, 'Si', NOW(), NOW())
                    """,
                    (id_cliente, canal, tipo, asunto, cuerpo),
                )
        except Exception as exc:
            return Response({"ok": False, "error": str(exc)}, status=500)
        return Response({"ok": True, "message": "Plantilla guardada."})
