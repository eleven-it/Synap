"""Vista HTML + APIs — pedido masivo por sucursales (Phase 4)."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterator

from django.http import StreamingHttpResponse
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
    anular_borrador_masivo_usuario,
    buscar_articulos_filtrados_ternas,
    cod_viajante_sesion,
    eliminar_fila_articulo,
    guardar_celda,
    guardar_descuento_fila,
    guardar_descuento_pie,
    listar_clientes_con_ternas,
    listar_sucursales_cliente,
    obtener_o_crear_draft,
    serializar_matriz,
)
from ecom.services.batch_checkout_masivo import (
    calcular_totales_lote_masivo,
    confirmar_lote_masivo,
    confirmar_lote_masivo_stream,
)
from ecom.checkout_relay_views import (
    _session_agente_percep,
    _session_dias_no_laborables,
    _session_pv,
)
from ecom.services.pedido_cabecera_comercial import (
    cabecera_defaults_json,
    es_supervisor_desde_ctx,
    parsear_cabecera_desde_body,
    resolver_cabecera_comercial,
)
from ecom.services.vendedor_operativo import ctx_desde_request


def _sess_user(request) -> Dict[str, Any]:
    return (getattr(request, "session", None) or {}).get("user") or {}


def _err(msg: str, code: str = "error", status: int = 400) -> Response:
    return Response({"ok": False, "error": msg, "code": code}, status=status)


def _resolver_cabecera_masivo(
    request,
    draft: EcomPedidoMasivoDraft,
    data: Dict[str, Any],
) -> tuple:
    """Resuelve cabecera comercial del body para preview/confirmar masivo."""
    ctx = ctx_desde_request(request)
    es_sup = es_supervisor_desde_ctx(ctx)
    bag = (getattr(request, "session", None) or {}).get("mayoristapp") or {}
    dias_ent = to_int_or_none(data.get("dias_entrega")) or to_int_or_none(
        bag.get("cant_dias_entrega")
    ) or 0
    parsed = parsear_cabecera_desde_body(data)
    return resolver_cabecera_comercial(
        draft.base_empresa,
        draft.id_cliente,
        es_supervisor=es_sup,
        fecha_pedido=parsed.get("fecha_pedido"),
        fecha_entrega=parsed.get("fecha_entrega"),
        vencimiento=parsed.get("vencimiento"),
        id_condventa=parsed.get("id_condventa"),
        lista_id=parsed.get("lista_id"),
        dias_entrega=int(dias_ent),
        dias_no_laborables=_session_dias_no_laborables(request),
        tipo_comprobante="PED",
    )


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
                        "eliminar_fila": reverse("ecom:api_pedido_masivo_eliminar_fila"),
                        "articulos": reverse("ecom:api_pedido_masivo_articulos"),
                        "sucursales": reverse("ecom:api_pedido_masivo_sucursales"),
                        "preview": reverse("ecom:api_pedido_masivo_preview"),
                        "descuento_fila": reverse("ecom:api_pedido_masivo_descuento_fila"),
                        "descuento_pie": reverse("ecom:api_pedido_masivo_descuento_pie"),
                        "confirmar": reverse("ecom:api_pedido_masivo_confirmar"),
                        "anular": reverse("ecom:api_pedido_masivo_anular"),
                        "vendedores_cartera": reverse("ecom:mayoristapp_vendedores_cartera"),
                        "vendedor_operativo": reverse("ecom:mayoristapp_vendedor_operativo"),
                        "carrito_vaciar": reverse("ecom:mayoristapp_carrito_vaciar"),
                        "lista_precio": reverse("ecom:mayoristapp_precios_lista_precio"),
                        "condiciones_venta": reverse("ecom:mayoristapp_precios_condiciones_venta"),
                    },
                },
            }
        )
        return ctx


class PedidoMasivoConfirmarAPIView(APIView):
    """POST confirma el lote (1 PED por sucursal) con compensación ante fallo."""

    permission_classes = [EcomPedidoMasivoUsarPermission]

    def _params_confirmar(
        self, request: Request, draft: EcomPedidoMasivoDraft, data: Dict[str, Any]
    ) -> tuple:
        """Resuelve kwargs comunes para confirmación sync o stream."""
        sess = _sess_user(request)
        try:
            pv = to_int_or_none(data.get("id_punto_venta")) or _session_pv(request)
        except Exception:
            return None, _err(
                "No se pudo resolver el punto de venta para confirmar el pedido.",
                "error_resolucion_pv",
            )
        if pv is None:
            return None, _err(
                "No hay punto de venta configurado para la empresa o el usuario.",
                "sin_pv",
            )

        id_dep = to_int_or_none(data.get("id_deposito")) or to_int_or_none(
            sess.get("id_deposito")
        ) or 1
        cv = cod_viajante_sesion(sess)

        desc_pie = data.get("desc_pie_pct")
        if desc_pie is not None:
            guardar_descuento_pie(draft, desc_pie_pct=desc_pie)

        cabecera, err_cab = _resolver_cabecera_masivo(request, draft, data)
        if not cabecera:
            return None, _err(err_cab or "Cabecera comercial inválida.")

        ctx = ctx_desde_request(request)
        es_sup = es_supervisor_desde_ctx(ctx)
        bag = (getattr(request, "session", None) or {}).get("mayoristapp") or {}
        dias_ent = to_int_or_none(data.get("dias_entrega")) or to_int_or_none(
            bag.get("cant_dias_entrega")
        ) or 0

        kwargs = dict(
            id_usuario=to_int_or_none(sess.get("id_usuario")),
            id_punto_venta=int(pv),
            cod_viajante=cv,
            lista_id=int(cabecera.lista_id),
            id_deposito=int(id_dep),
            desc_pie_pct=desc_pie,
            forma_entrega=str(data.get("forma_entrega") or ""),
            observaciones=str(data.get("observaciones") or ""),
            agente_percep=_session_agente_percep(request),
            sess_user=sess,
            cabecera=cabecera,
            es_supervisor=es_sup,
            dias_entrega=int(dias_ent),
            dias_no_laborables=_session_dias_no_laborables(request),
        )
        return kwargs, None

    def _stream_ndjson(
        self,
        draft: EcomPedidoMasivoDraft,
        base: str,
        kwargs: Dict[str, Any],
    ) -> Iterator[str]:
        try:
            for ev in confirmar_lote_masivo_stream(draft, **kwargs):
                if ev.get("event") == "fin":
                    draft.refresh_from_db()
                    ev = dict(ev)
                    ev["matriz"] = serializar_matriz(draft, base)
                yield json.dumps(ev, ensure_ascii=False) + "\n"
        except Exception as exc:
            draft.refresh_from_db()
            fin = {
                "event": "fin",
                "ok": False,
                "message": str(exc),
                "errores": {"_lote": str(exc)},
                "codigos_movimiento": [],
                "compensacion": [],
                "matriz": serializar_matriz(draft, base),
            }
            yield json.dumps(fin, ensure_ascii=False) + "\n"

    def post(self, request: Request):
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

        kwargs, err_resp = self._params_confirmar(request, draft, data)
        if err_resp is not None:
            return err_resp

        if data.get("stream"):
            response = StreamingHttpResponse(
                self._stream_ndjson(draft, base, kwargs),
                content_type="application/x-ndjson; charset=utf-8",
            )
            response["Cache-Control"] = "no-cache"
            response["X-Accel-Buffering"] = "no"
            return response

        ok, msg, payload = confirmar_lote_masivo(draft, **kwargs)
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
        sess = _sess_user(request)
        if not base:
            return _err("Sin base_empresa.", "sin_base_empresa")
        idc = to_int_or_none(request.query_params.get("id_cliente"))
        if idc is None:
            return _err("Falta id_cliente.")
        cv = cod_viajante_sesion(sess)
        return Response(
            {
                "ok": True,
                "sucursales": listar_sucursales_cliente(base, idc, cod_viajante=cv),
            }
        )


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
        matriz = serializar_matriz(draft, base)
        ctx = ctx_desde_request(request)
        bag = (getattr(request, "session", None) or {}).get("mayoristapp") or {}
        dias_ent = to_int_or_none(bag.get("cant_dias_entrega")) or 0
        matriz["cabecera"] = cabecera_defaults_json(
            base,
            draft.id_cliente,
            es_supervisor=es_supervisor_desde_ctx(ctx),
            dias_entrega=int(dias_ent),
            dias_no_laborables=_session_dias_no_laborables(request),
        )
        return Response({"ok": True, "matriz": matriz})


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


class PedidoMasivoEliminarFilaAPIView(APIView):
    """POST quita un artículo (todas las celdas + desc. fila) del borrador."""

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
        ok, msg = eliminar_fila_articulo(
            draft, id_articulo=to_int_or_none(data.get("id_articulo"))
        )
        if not ok:
            return _err(msg)
        return Response(
            {
                "ok": True,
                "message": msg,
                "matriz": serializar_matriz(draft, base),
            }
        )


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
            id_cliente_domicilio=to_int_or_none(request.query_params.get("id_cliente_domicilio")),
            q=str(request.query_params.get("q") or ""),
            lista_id=lista_id,
            id_deposito=id_dep,
            pagina=to_int_or_none(request.query_params.get("pagina")) or 1,
            tam=to_int_or_none(request.query_params.get("tam")) or 20,
        )
        return Response({"ok": True, **result})


class PedidoMasivoPreviewAPIView(APIView):
    """POST preview agregado de totales del lote (REQ-MAS-10)."""

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

        desc_pie = data.get("desc_pie_pct")
        if desc_pie is not None:
            guardar_descuento_pie(draft, desc_pie_pct=desc_pie)

        cabecera, err_cab = _resolver_cabecera_masivo(request, draft, data)
        if not cabecera:
            return _err(err_cab or "Cabecera comercial inválida.")

        id_dep = to_int_or_none(data.get("id_deposito")) or to_int_or_none(
            sess.get("id_deposito")
        ) or 1

        preview = calcular_totales_lote_masivo(
            draft,
            id_usuario=id_u,
            desc_pie_pct=desc_pie,
            lista_id=cabecera.lista_id,
            id_deposito=int(id_dep),
            cabecera=cabecera,
        )
        body = {
            "ok": True,
            "matriz": serializar_matriz(draft, base),
            **preview,
        }
        if preview.get("warning"):
            body["warning"] = preview["warning"]
        return Response(body)


class PedidoMasivoDescuentoFilaAPIView(APIView):
    """POST persiste % descuento por fila (artículo) en el borrador."""

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
            pk=draft_id, base_empresa=base, id_usuario=id_u
        ).first()
        if not draft:
            return _err("Borrador no encontrado.", "no_encontrado", 404)
        ok, msg = guardar_descuento_fila(
            draft,
            id_articulo=to_int_or_none(data.get("id_articulo")),
            porcentaje_descuento=data.get("porcentaje_descuento"),
        )
        if not ok:
            return _err(msg)
        return Response(
            {
                "ok": True,
                "message": msg,
                "matriz": serializar_matriz(draft, base),
            }
        )


class PedidoMasivoDescuentoPieAPIView(APIView):
    """POST persiste descuento pie de lote en el borrador."""

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
            pk=draft_id, base_empresa=base, id_usuario=id_u
        ).first()
        if not draft:
            return _err("Borrador no encontrado.", "no_encontrado", 404)
        ok, msg = guardar_descuento_pie(
            draft,
            desc_pie_pct=data.get("desc_pie_pct"),
        )
        if not ok:
            return _err(msg)
        return Response(
            {
                "ok": True,
                "message": msg,
                "matriz": serializar_matriz(draft, base),
            }
        )


class PedidoMasivoAnularAPIView(APIView):
    """POST anula un borrador masivo en edición (recuperable desde hub)."""

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
        ok, msg = anular_borrador_masivo_usuario(draft_id, id_u, base)
        if not ok:
            return _err(msg)
        draft = EcomPedidoMasivoDraft.objects.filter(
            pk=draft_id, base_empresa=base, id_usuario=id_u
        ).first()
        body: Dict[str, Any] = {"ok": True, "message": msg}
        if draft:
            body["matriz"] = serializar_matriz(draft, base)
        return Response(body)
