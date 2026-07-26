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


class EcomCreditoConsultarPermission(BasePermission):
    """Permite consultar datos de crédito del cliente (configurar o aprobar)."""

    message = "Se requiere permiso finance.credito.configurar o finance.credito.aprobar."

    def has_permission(self, request, view):
        if not EcomMayoristappSessionPermission().has_permission(request, view):
            return False
        user = getattr(request, "user", None)
        if getattr(user, "is_superuser", False):
            return True
        sess = (getattr(request, "session", None) or {}).get("user") or {}
        return puede_configurar_credito(sess) or puede_aprobar_credito(sess)


def _session_user(request: Request) -> Dict[str, Any]:
    return (getattr(request, "session", None) or {}).get("user") or {}


def _bool_a_si_no_capa(raw: Any, default: bool = True) -> str:
    if raw is None:
        return "Si" if default else "No"
    if raw in (True, "true", "True", 1, "1", "Si", "si", "Sí", "sí"):
        return "Si"
    if raw in (False, "false", "False", 0, "0", "No", "no"):
        return "No"
    return "Si" if default else "No"


def _fetch_cliente_credito(base_empresa: str, id_cliente: int) -> Optional[Dict[str, Any]]:
    sql = """
        SELECT
            cliente.Codigo AS Codigo,
            cliente.Credito AS Credito,
            COALESCE(cliente.saldo, 0) AS saldo,
            cliente.credito_limite_dias AS credito_limite_dias,
            COALESCE(cliente.nombre_cliente, '') AS nombre_cliente,
            COALESCE(cliente.CUIT, '') AS cuit
        FROM cliente
        WHERE cliente.Codigo = %s
        LIMIT 1
    """
    with get_connection(base_empresa) as conn:
        cur = conn.cursor(MySQLdb.cursors.DictCursor)
        cur.execute(sql, [id_cliente])
        return cur.fetchone()


def _cliente_credito_resumen(cli: Dict[str, Any]) -> Dict[str, Any]:
    cupo = to_decimal_or_none(cli.get("Credito")) or Decimal("0")
    saldo = to_decimal_or_none(cli.get("saldo")) or Decimal("0")
    sin_tope = cupo == Decimal("0")
    disponible = None
    if not sin_tope:
        disponible = float(max(Decimal("0"), cupo - saldo))
    return {
        "id_cliente": int(to_int_or_none(cli.get("Codigo")) or 0),
        "nombre_cliente": str_or_default(cli.get("nombre_cliente"), ""),
        "cuit": str_or_default(cli.get("cuit"), ""),
        "credito_cupo": float(cupo),
        "saldo": float(saldo),
        "credito_limite_dias": to_int_or_none(cli.get("credito_limite_dias")) or 0,
        "sin_tope_monetario": sin_tope,
        "disponible_aprox": disponible,
    }


def _normalizar_politica_row(row: Dict[str, Any]) -> Dict[str, Any]:
    item = dict(row)
    id_cliente = to_int_or_none(item.get("id_cliente"))
    if id_cliente is None or id_cliente == 0:
        item["id_cliente"] = 0
        item["es_default"] = True
    else:
        item["id_cliente"] = id_cliente
        item["es_default"] = False
    for key in ("credito_cupo", "saldo"):
        if key in item and item[key] is not None:
            item[key] = float(to_decimal_or_none(item[key]) or Decimal("0"))
        elif key in item:
            item[key] = None
    limite_dias_cli = item.get("credito_limite_dias")
    if limite_dias_cli is not None:
        item["credito_limite_dias"] = to_int_or_none(limite_dias_cli)
    return item


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
        urls = {
            "api_pendientes": reverse("ecom:api_credito_pendientes"),
            "aprobar_tpl": reverse(
                "ecom:api_credito_aprobar", kwargs={"cod_mov": 0}
            ).replace("/0/", "/{cod_mov}/"),
            "rechazar_tpl": reverse(
                "ecom:api_credito_rechazar", kwargs={"cod_mov": 0}
            ).replace("/0/", "/{cod_mov}/"),
            "hub": reverse("ecom:mayoristapp_pedidos_hub"),
            "buscar_clientes": reverse("ecom:mayoristapp_clientes_buscar"),
            "cliente_resumen": reverse("ecom:api_credito_cliente_resumen"),
        }
        # El atajo a Políticas solo se ofrece a quien puede configurarlas.
        sess = _session_user(self.request)
        if getattr(getattr(self.request, "user", None), "is_superuser", False) or puede_configurar_credito(sess):
            urls["politicas"] = reverse("ecom:credito_politicas")
        ctx["bootstrap"] = {
            "urls": urls,
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
                "buscar_clientes": reverse("ecom:mayoristapp_clientes_buscar"),
                "cliente_resumen": reverse("ecom:api_credito_cliente_resumen"),
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
                "buscar_clientes": reverse("ecom:mayoristapp_clientes_buscar"),
                "cliente_resumen": reverse("ecom:api_credito_cliente_resumen"),
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
                "buscar_clientes": reverse("ecom:mayoristapp_clientes_buscar"),
            }
        }
        return ctx


class CreditoClienteResumenAPIView(APIView):
    """GET ``/ecom/api/credito/cliente-resumen/?id_cliente=N`` — cupo Adminet del cliente."""

    permission_classes = [EcomCreditoConsultarPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"ok": False, "error": "Sin base_empresa."}, status=400)
        id_cliente = to_int_or_none(request.query_params.get("id_cliente"))
        if id_cliente is None:
            return Response({"ok": False, "error": "Falta id_cliente."}, status=400)
        cli = _fetch_cliente_credito(base, int(id_cliente))
        if not cli:
            return Response({"ok": False, "error": "Cliente no encontrado."}, status=404)
        return Response({"ok": True, "cliente": _cliente_credito_resumen(cli)})


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
            SELECT
                p.id, p.id_cliente, p.canal, p.limite_dias, p.activo,
                p.capa_cxc, p.capa_ped_abiertos, p.capa_remitos_nf, p.capa_cheques,
                p.capa_doc_actual, p.incluir_mora,
                COALESCE(c.nombre_cliente, '') AS nombre_cliente,
                c.Credito AS credito_cupo,
                COALESCE(c.saldo, 0) AS saldo,
                c.credito_limite_dias AS credito_limite_dias
            FROM ecom_credito_politica p
            LEFT JOIN cliente c ON c.Codigo = p.id_cliente AND COALESCE(p.id_cliente, 0) > 0
            ORDER BY p.id_cliente IS NULL, p.id_cliente, p.canal
            LIMIT 500
        """
        try:
            with mysql_cursor(base, dict_cursor=True) as cur:
                cur.execute(sql)
                rows = [_normalizar_politica_row(dict(r)) for r in cur.fetchall() or []]
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
        capa_cxc = _bool_a_si_no_capa(data.get("capa_cxc"), default=True)
        capa_ped_abiertos = _bool_a_si_no_capa(data.get("capa_ped_abiertos"), default=True)
        capa_remitos_nf = _bool_a_si_no_capa(data.get("capa_remitos_nf"), default=False)
        capa_cheques = _bool_a_si_no_capa(data.get("capa_cheques"), default=False)
        capa_doc_actual = _bool_a_si_no_capa(data.get("capa_doc_actual"), default=True)
        incluir_mora = _bool_a_si_no_capa(data.get("incluir_mora"), default=True)
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
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    """,
                    (
                        id_cliente,
                        canal,
                        limite_dias,
                        activo,
                        capa_cxc,
                        capa_ped_abiertos,
                        capa_remitos_nf,
                        capa_cheques,
                        capa_doc_actual,
                        incluir_mora,
                    ),
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
