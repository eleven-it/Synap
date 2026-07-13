"""Vista HTML + APIs — pedido masivo por sucursales (Phase 4)."""

from __future__ import annotations

from typing import Any, Dict

from django.urls import reverse
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.administranet_types import to_int_or_none
from ecom.catalogo_producto_relay_views import _session_base_empresa
from ecom.models import EcomPedidoMasivoDraft
from ecom.pedido_masivo_stub_views import _StubMayoristappPermisoView
from ecom.permissions import EcomPedidoMasivoUsarPermission
from ecom.services.pedido_masivo_matriz import (
    buscar_articulos_filtrados_ternas,
    cod_viajante_sesion,
    guardar_celda,
    listar_clientes_con_ternas,
    listar_sucursales_cliente,
    obtener_o_crear_draft,
    serializar_matriz,
)
from ecom.services.batch_checkout_masivo import confirmar_lote_masivo
from ecom.checkout_relay_views import (
    _session_agente_percep,
    _session_pv,
)


def _sess_user(request) -> Dict[str, Any]:
    return (getattr(request, "session", None) or {}).get("user") or {}


def _err(msg: str, code: str = "error", status: int = 400) -> Response:
    return Response({"ok": False, "error": msg, "code": code}, status=status)


class PedidoMasivoSucursalesView(_StubMayoristappPermisoView):
    """Matriz packs × sucursales — ``/ecom/mayoristapp/pedido-masivo-sucursales/``."""

    template_name = "ecom/pedido_masivo_sucursales.html"
    permiso_requerido = "ecom.pedido_masivo.usar"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        draft_q = to_int_or_none(self.request.GET.get("draft"))
        ctx.update(
            {
                "draft_id_inicial": draft_q,
                "bootstrap": {
                    "draft_id": draft_q,
                    "urls": {
                        "hub": reverse("ecom:mayoristapp_pedidos_hub"),
                        "clientes": reverse("ecom:api_pedido_masivo_clientes"),
                        "abrir": reverse("ecom:api_pedido_masivo_abrir"),
                        "matriz": reverse("ecom:api_pedido_masivo_matriz"),
                        "celda": reverse("ecom:api_pedido_masivo_celda"),
                        "articulos": reverse("ecom:api_pedido_masivo_articulos"),
                        "sucursales": reverse("ecom:api_pedido_masivo_sucursales"),
                        "confirmar": reverse("ecom:api_pedido_masivo_confirmar"),
                    },
                },
            }
        )
        return ctx


class PedidoMasivoConfirmarAPIView(APIView):
    """POST confirma el lote (1 PED por sucursal) con compensación ante fallo."""

    permission_classes = [EcomPedidoMasivoUsarPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        sess = _sess_user(request)
        if not base:
            return _err("Sin base_empresa.", "sin_base_empresa")
        data = request.data if isinstance(request.data, dict) else {}
        draft_id = to_int_or_none(data.get("draft_id"))
        id_u = to_int_or_none(sess.get("id_usuario"))
        if draft_id is None or id_u is None:
            return _err("Falta draft_id o usuario.")
        draft = EcomPedidoMasivoDraft.objects.filter(
            pk=draft_id, base_empresa=base, id_usuario=id_u
        ).first()
        if not draft:
            return _err("Borrador no encontrado.", "no_encontrado", 404)

        pv = to_int_or_none(data.get("id_punto_venta")) or _session_pv(request)
        if pv is None:
            return _err("Falta punto de venta.", "sin_pv")

        lista_id = to_int_or_none(data.get("lista_id")) or to_int_or_none(
            sess.get("lista_id")
        ) or 1
        id_dep = to_int_or_none(data.get("id_deposito")) or to_int_or_none(
            sess.get("id_deposito")
        ) or 1
        cv = cod_viajante_sesion(sess)

        ok, msg, payload = confirmar_lote_masivo(
            draft,
            id_usuario=id_u,
            id_punto_venta=int(pv),
            cod_viajante=cv,
            lista_id=int(lista_id),
            id_deposito=int(id_dep),
            forma_entrega=str(data.get("forma_entrega") or ""),
            observaciones=str(data.get("observaciones") or ""),
            agente_percep=_session_agente_percep(request),
        )
        draft.refresh_from_db()
        body = {
            "ok": ok,
            "message": msg,
            "matriz": serializar_matriz(draft, base),
            **(payload or {}),
        }
        if not ok:
            return Response(body, status=409)
        return Response(body)


class PedidoMasivoClientesAPIView(APIView):
    permission_classes = [EcomPedidoMasivoUsarPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        sess = _sess_user(request)
        if not base:
            return _err("Sin base_empresa.", "sin_base_empresa")
        cv = cod_viajante_sesion(sess)
        if cv is None:
            return _err("No se resolvió el viajante de sesión.", "sin_viajante")
        rows = listar_clientes_con_ternas(
            base,
            cv,
            q=str(request.query_params.get("q") or ""),
            limit=to_int_or_none(request.query_params.get("limit")) or 40,
        )
        return Response({"ok": True, "items": rows, "CodViajante": cv})


class PedidoMasivoSucursalesAPIView(APIView):
    permission_classes = [EcomPedidoMasivoUsarPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return _err("Sin base_empresa.", "sin_base_empresa")
        idc = to_int_or_none(request.query_params.get("id_cliente"))
        if idc is None:
            return _err("Falta id_cliente.")
        return Response({"ok": True, "sucursales": listar_sucursales_cliente(base, idc)})


class PedidoMasivoAbrirAPIView(APIView):
    """POST crea/recupera borrador y devuelve matriz serializada."""

    permission_classes = [EcomPedidoMasivoUsarPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        sess = _sess_user(request)
        if not base:
            return _err("Sin base_empresa.", "sin_base_empresa")
        id_u = to_int_or_none(sess.get("id_usuario"))
        data = request.data if isinstance(request.data, dict) else {}
        idc = to_int_or_none(data.get("id_cliente"))
        draft_id = to_int_or_none(data.get("draft_id"))
        cv = cod_viajante_sesion(sess)
        if id_u is None:
            return _err("Sin usuario en sesión.")
        if draft_id is None and idc is None:
            return _err("Indicá id_cliente o draft_id.")

        if draft_id is not None and idc is None:
            d0 = EcomPedidoMasivoDraft.objects.filter(
                pk=draft_id, base_empresa=base, id_usuario=id_u
            ).first()
            if not d0:
                return _err("Borrador no encontrado.", "no_encontrado", 404)
            idc = d0.id_cliente

        draft, err = obtener_o_crear_draft(
            base_empresa=base,
            id_usuario=id_u,
            id_cliente=idc,
            cod_viajante=cv,
            draft_id=draft_id,
        )
        if not draft:
            return _err(err or "No se pudo abrir el borrador.")
        return Response({"ok": True, "matriz": serializar_matriz(draft, base)})


class PedidoMasivoMatrizAPIView(APIView):
    permission_classes = [EcomPedidoMasivoUsarPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        sess = _sess_user(request)
        if not base:
            return _err("Sin base_empresa.", "sin_base_empresa")
        draft_id = to_int_or_none(request.query_params.get("draft_id"))
        id_u = to_int_or_none(sess.get("id_usuario"))
        if draft_id is None or id_u is None:
            return _err("Falta draft_id.")
        draft = EcomPedidoMasivoDraft.objects.filter(
            pk=draft_id, base_empresa=base, id_usuario=id_u
        ).first()
        if not draft:
            return _err("Borrador no encontrado.", "no_encontrado", 404)
        return Response({"ok": True, "matriz": serializar_matriz(draft, base)})


class PedidoMasivoCeldaAPIView(APIView):
    """POST autoguardado de una celda."""

    permission_classes = [EcomPedidoMasivoUsarPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        sess = _sess_user(request)
        if not base:
            return _err("Sin base_empresa.", "sin_base_empresa")
        data = request.data if isinstance(request.data, dict) else {}
        draft_id = to_int_or_none(data.get("draft_id"))
        id_u = to_int_or_none(sess.get("id_usuario"))
        if draft_id is None or id_u is None:
            return _err("Falta draft_id.")
        draft = EcomPedidoMasivoDraft.objects.filter(
            pk=draft_id,
            base_empresa=base,
            id_usuario=id_u,
        ).first()
        if not draft:
            return _err("Borrador no encontrado.", "no_encontrado", 404)
        ok, msg, payload = guardar_celda(
            draft,
            id_articulo=to_int_or_none(data.get("id_articulo")),
            id_cliente_domicilio=to_int_or_none(data.get("id_cliente_domicilio")),
            cantidad_packs=data.get("cantidad_packs"),
        )
        if not ok:
            return _err(msg)
        return Response({"ok": True, "message": msg, "celda": payload})


class PedidoMasivoArticulosAPIView(APIView):
    permission_classes = [EcomPedidoMasivoUsarPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        sess = _sess_user(request)
        if not base:
            return _err("Sin base_empresa.", "sin_base_empresa")
        cv = cod_viajante_sesion(sess)
        idc = to_int_or_none(request.query_params.get("id_cliente"))
        if cv is None or idc is None:
            return _err("Se requieren viajante e id_cliente.")
        lista_id = to_int_or_none(request.query_params.get("lista_id")) or 1
        id_dep = to_int_or_none(request.query_params.get("id_deposito")) or 1
        result = buscar_articulos_filtrados_ternas(
            base,
            cod_viajante=cv,
            id_cliente=idc,
            q=str(request.query_params.get("q") or ""),
            lista_id=lista_id,
            id_deposito=id_dep,
            pagina=to_int_or_none(request.query_params.get("pagina")) or 1,
            tam=to_int_or_none(request.query_params.get("tam")) or 30,
        )
        return Response({"ok": True, **result})
