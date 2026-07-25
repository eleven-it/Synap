"""
APIs y vistas HTML de gestión comercial de pedidos (PED).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.administranet_types import to_int_or_none
from ecom.carrito_relay_views import _resolver_contexto
from ecom.catalogo_producto_relay_views import _session_base_empresa
from ecom.mayoristapp_web_views import MayoristappWebSessionMixin
from ecom.permissions import (
    EcomComprobantesReadPermission,
    EcomMayoristappSessionPermission,
    EcomPedidosAprobarPermission,
    EcomPedidosVerPermission,
)
from ecom.services.aprobacion_pedidos import (
    listar_pendientes_comerciales,
    resolver,
    resolver_lote_masivo,
)
from ecom.services.lote_resumen import (
    LoteResumenError,
    cargar_draft_resumen,
    construir_resumen_lote,
    reverse_matriz_readonly,
)
from ecom.services.pedidos_hub_pipeline import (
    archivar_borrador_masivo,
    archivar_carrito_legacy,
    construir_hub_pedidos,
    eliminar_borrador_masivo_definitivo,
    migrar_carrito_legacy_a_draft,
    url_pedido_masivo_modo_simple,
)
from ecom.services.ecom_config_mysql import aprobacion_pedidos_activa, credito_pedidos_activo
from ecom.checkout_relay_views import _session_dias_no_laborables
from ecom.services.pedido_cabecera_comercial import (
    cabecera_defaults_json,
    puede_editar_cabecera_comercial,
)
from ecom.services.vendedor_operativo import ctx_desde_request
from ecom.services.mayoristapp_session import leer_cliente_seleccionado, leer_idcliente_mayoristapp
from ecom.services.pedido_cabecera_relay import (
    cabecera_comp_ped_relay,
    cabecera_pedido_relay,
    pedidos_kpis_relay,
    pedidos_recientes_relay,
    puede_anular_pedido_relay,
    stepper_estados_pedido,
    vinculos_pedido_relay,
)
from ecom.services.pedido_comprobante_pdf import generar_pedido_pdf
from ecom.services.pedido_plantilla_service import cargar_desde_pedido, preview_desde_pedido
from core.services.administranet_stock import get_config_unidad_bulto_display
from ecom.services.presentacion_articulo import _fetch_utiliza_embalaje
from ecom.services.presupuesto_a_pedido_service import convertir_presupuesto_a_pedido
from ecom.services.comprobantes_relay import detalle_pedido_relay
from ecom.services.recibo_catalogos_service import listar_puntos_venta_usuario


def _session_user(request: Request) -> Dict[str, Any]:
    return (getattr(request, "session", None) or {}).get("user") or {}


def _es_cliente_sesion(request: Request) -> bool:
    return (_session_user(request).get("tipousuario") or "").strip().lower() == "cliente"


def _error(message: str, code: str = "error", status: int = 400) -> Response:
    return Response({"ok": False, "error": message, "code": code}, status=status)


class PedidoCabeceraV1APIView(APIView):
    """GET ``/ecom/api/v1/mayoristapp/comprobantes/pedidos/<cod_mov>/`` — cabecera PED."""

    permission_classes = [EcomComprobantesReadPermission]

    def get(self, request: Request, cod_mov: int) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return _error("No se encontró base_empresa en la sesión.", "sin_base_empresa")
        cab = cabecera_pedido_relay(base, cod_mov)
        if not cab:
            return _error("Pedido no encontrado.", "no_encontrado", 404)
        ok_anular, motivo_anular = puede_anular_pedido_relay(base, cod_mov)
        vinculos = vinculos_pedido_relay(base, cod_mov)
        return Response(
            {
                "ok": True,
                "cabecera": cab,
                "vinculos": vinculos,
                "stepper": stepper_estados_pedido(str(cab.get("estado") or "")),
                "puede_anular": ok_anular,
                "motivo_no_anular": motivo_anular if not ok_anular else "",
            }
        )


class PedidosRecientesAPIView(APIView):
    """GET ``/ecom/api/mayoristapp/pedidos/recientes/`` — últimos PED del cliente en contexto."""

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return _error("No se encontró base_empresa en la sesión.", "sin_base_empresa")
        idc = leer_idcliente_mayoristapp(request)
        if idc is None:
            return _error("Seleccione un cliente para ver pedidos recientes.", "sin_cliente")
        lim = to_int_or_none(request.query_params.get("limit")) or 10
        es_cliente = _es_cliente_sesion(request)
        rows = pedidos_recientes_relay(
            base,
            int(idc),
            limit=lim,
            incluir_importe=not es_cliente,
        )
        return Response({"ok": True, "total": len(rows), "results": rows})


class PedidosKpisAPIView(APIView):
    """GET ``/ecom/api/mayoristapp/pedidos/kpis/`` — métricas del día para hub."""

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return _error("No se encontró base_empresa en la sesión.", "sin_base_empresa")
        idc = leer_idcliente_mayoristapp(request)
        kpis = pedidos_kpis_relay(base, _session_user(request), idcliente=idc)
        return Response({"ok": True, **kpis})


class CarritoDesdePedidoPreviewAPIView(APIView):
    """GET ``/ecom/api/mayoristapp/carrito/desde-pedido/<cod_mov>/preview/``"""

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request, cod_mov: int) -> Response:
        ctx, err = _resolver_contexto(request)
        if err is not None:
            return err
        base, _id_usuario, cart, _desc = ctx
        idc = leer_idcliente_mayoristapp(request)
        preview, perr = preview_desde_pedido(
            base,
            cod_mov,
            _session_user(request),
            idc,
            cart,
            es_cliente=_es_cliente_sesion(request),
        )
        if perr:
            return _error(perr)
        return Response({"ok": True, "preview": preview})


class CarritoDesdePedidoAPIView(APIView):
    """POST ``/ecom/api/mayoristapp/carrito/desde-pedido/`` — carga plantilla al carrito."""

    permission_classes = [EcomMayoristappSessionPermission]

    def post(self, request: Request) -> Response:
        ctx, err = _resolver_contexto(request)
        if err is not None:
            return err
        base, id_usuario, cart, _desc = ctx
        cod = to_int_or_none(request.data.get("codigo_movimiento"))
        if cod is None:
            return _error("codigo_movimiento inválido.")
        modo = str(request.data.get("modo") or "reemplazar").strip().lower()
        if modo not in ("reemplazar", "agregar"):
            return _error("modo debe ser reemplazar o agregar.")
        cantidades_raw = request.data.get("cantidades") or {}
        cantidades = {}
        if isinstance(cantidades_raw, dict):
            for k, v in cantidades_raw.items():
                ik = to_int_or_none(k)
                if ik is not None:
                    cantidades[ik] = v
        idc = leer_idcliente_mayoristapp(request)
        # Al abrir un PED concreto: alinear cliente de sesión al del pedido si hace falta.
        cab = None
        try:
            cab = cabecera_pedido_relay(base, int(cod))
        except Exception:
            cab = None
        id_ped = to_int_or_none((cab or {}).get("id_cliente")) if cab else None
        if id_ped is not None and (idc is None or int(idc) != int(id_ped)):
            idc = int(id_ped)
        raw_omit = request.data.get("omitir_validacion_stock")
        omitir_stock = str(raw_omit or "").strip().lower() in ("1", "true", "si", "sí")
        # Edición de PED Pendiente: el stock ya está reservado en saldo_pedido_cliente.
        if str(request.data.get("origen") or "").strip().lower() == "edicion":
            omitir_stock = True
        result, perr = cargar_desde_pedido(
            base,
            cod,
            _session_user(request),
            idc,
            cart,
            int(id_usuario),
            modo=modo,
            es_cliente=_es_cliente_sesion(request),
            cantidades=cantidades or None,
            omitir_validacion_stock=omitir_stock,
        )
        if perr:
            return _error(perr)
        return Response({"ok": True, **(result or {})})


class PedidoComprobantePDFAPIView(APIView):
    """GET ``/ecom/api/mayoristapp/comprobantes/pedidos/<cod_mov>/pdf/`` — PDF del PED."""

    permission_classes = [EcomComprobantesReadPermission]

    def get(self, request: Request, cod_mov: int) -> HttpResponse:
        base = _session_base_empresa(request)
        if not base:
            return HttpResponse("No se encontró base_empresa en la sesión.", status=400)
        sess = getattr(request, "session", None) or {}
        usa_manual = str(sess.get("usa_id_manual") or "").strip().lower() in (
            "si",
            "sí",
            "1",
            "true",
        )
        ok, err, pdf = generar_pedido_pdf(base, cod_mov, usa_id_manual=usa_manual)
        if not ok or not pdf:
            return HttpResponse(err or "No se pudo generar el PDF.", status=404)
        nro = str(cod_mov)
        cab = cabecera_pedido_relay(base, cod_mov)
        if cab and cab.get("nro_comprobante"):
            nro = str(cab.get("nro_comprobante")).replace("/", "-")
        resp = HttpResponse(pdf, content_type="application/pdf")
        resp["Content-Disposition"] = f'inline; filename="pedido-{nro}.pdf"'
        return resp


class CompraMayoristaContextoAPIView(APIView):
    """GET ``/ecom/api/mayoristapp/compra/contexto/`` — PV, cliente en sesión."""

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return _error("No se encontró base_empresa en la sesión.", "sin_base_empresa")
        sess_user = _session_user(request)
        bag = (getattr(request, "session", None) or {}).get("mayoristapp") or {}
        id_pv = to_int_or_none(
            (getattr(request, "session", None) or {}).get("id_punto_venta_activo")
            or bag.get("id_punto_venta_activo")
            or bag.get("id_punto_venta")
            or sess_user.get("id_punto_venta")
        )
        puntos = listar_puntos_venta_usuario(base, sess_user)
        if id_pv is None and puntos:
            id_pv = puntos[0].get("id_punto_venta")
        cliente_raw = leer_cliente_seleccionado(request)
        cliente = None
        autoriza_credito = {}
        if isinstance(cliente_raw, dict):
            cliente = cliente_raw
        elif isinstance(cliente_raw, list) and cliente_raw:
            cliente = cliente_raw[0] if isinstance(cliente_raw[0], dict) else None
            if len(cliente_raw) > 1 and isinstance(cliente_raw[1], dict):
                autoriza_credito = cliente_raw[1]
        embalaje_cfg = get_config_unidad_bulto_display(base)
        embalaje_cfg["utiliza_embalaje"] = "Si" if _fetch_utiliza_embalaje(base) else "No"
        from ecom.cliente_relay_views import (
            _payload_lista_precio_cliente,
            _url_pdf_lista_precio,
        )

        lista_payload = (
            _payload_lista_precio_cliente(base, cliente) if cliente else None
        )
        idcliente = leer_idcliente_mayoristapp(request)
        ctx = ctx_desde_request(request)
        puede_editar = puede_editar_cabecera_comercial(ctx)
        bag = (getattr(request, "session", None) or {}).get("mayoristapp") or {}
        dias_ent = to_int_or_none(bag.get("cant_dias_entrega")) or 0
        cabecera_payload = None
        if idcliente:
            cabecera_payload = cabecera_defaults_json(
                base,
                int(idcliente),
                es_supervisor=puede_editar,
                dias_entrega=int(dias_ent),
                dias_no_laborables=_session_dias_no_laborables(request),
            )
        return Response(
            {
                "ok": True,
                "es_cliente": _es_cliente_sesion(request),
                "id_punto_venta_default": id_pv,
                "puntos_venta": puntos,
                "idcliente": idcliente,
                "cliente": cliente,
                "autoriza_credito": autoriza_credito,
                "credito_pedidos_activo": credito_pedidos_activo(base),
                "credito_precheck_url": reverse("ecom:credito_precheck"),
                "embalaje": embalaje_cfg,
                "listaPrecio": lista_payload,
                "lista_precio_pdf_url": _url_pdf_lista_precio(request) if cliente else "",
                "puede_editar_cabecera": puede_editar,
                "es_supervisor": puede_editar,
                "cabecera": cabecera_payload,
            }
        )


class PresupuestoConvertirPedidoAPIView(APIView):
    """POST ``/ecom/api/mayoristapp/presupuestos/<cod_mov>/convertir-pedido/?ajax=1``"""

    permission_classes = [EcomMayoristappSessionPermission]

    def post(self, request: Request, cod_mov: int) -> Response:
        if "ajax" not in request.query_params:
            return _error("Parámetro ajax requerido.", "ajax_requerido", 400)
        base = _session_base_empresa(request)
        if not base:
            return _error("No se encontró base_empresa en la sesión.", "sin_base_empresa")
        sess_user = _session_user(request)
        body = request.data or {}
        id_pv = to_int_or_none(body.get("id_punto_venta"))
        if id_pv is None:
            puntos = listar_puntos_venta_usuario(base, sess_user)
            if puntos:
                id_pv = to_int_or_none(puntos[0].get("id_punto_venta"))
        if id_pv is None:
            return _error("Seleccione un punto de venta.", "sin_pv", 400)
        id_usuario = to_int_or_none(sess_user.get("id_usuario")) or 0
        cv = to_int_or_none(sess_user.get("cod_viajante") or sess_user.get("codViajante"))
        ok, err, result = convertir_presupuesto_a_pedido(
            base,
            int(cod_mov),
            id_usuario=id_usuario,
            id_punto_venta=int(id_pv),
            cod_viajante=cv,
            es_cliente=_es_cliente_sesion(request),
            forma_entrega=str(body.get("forma_entrega") or ""),
            observaciones=str(body.get("observaciones") or ""),
        )
        if not ok:
            return _error(err or "No se pudo convertir el presupuesto.", "conversion_fallida", 400)
        return Response({"ok": True, **(result or {})})


class LoteResumenView(MayoristappWebSessionMixin, TemplateView):
    """Resumen de lote masivo confirmado — ``/ecom/mayoristapp/pedidos/lote/<draft_id>/``."""

    template_name = "ecom/lote_resumen.html"

    def dispatch(self, request, *args, **kwargs):
        sess = _session_user(request)
        base = str(sess.get("base_empresa") or "").strip()
        draft_id = to_int_or_none(kwargs.get("draft_id"))
        try:
            if draft_id is None:
                raise LoteResumenError("Lote no encontrado.", status=404)
            cargar_draft_resumen(base, int(draft_id), sess)
        except LoteResumenError as exc:
            if exc.status == 403:
                from django.contrib import messages

                messages.error(request, exc.message)
                return redirect(reverse("ecom:mayoristapp_pedidos_hub"))
            from django.http import Http404

            raise Http404(exc.message) from exc
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sess = _session_user(self.request)
        base = str(sess.get("base_empresa") or "").strip()
        draft_id = to_int_or_none(kwargs.get("draft_id"))
        resumen = construir_resumen_lote(base, int(draft_id), sess)
        lote = resumen.get("lote") or {}
        context.update(
            {
                "page_title": "Resumen del lote",
                "resumen_bootstrap": {
                    "resumen": resumen,
                    "draft_id": draft_id,
                    "urls": {
                        "hub": reverse("ecom:mayoristapp_pedidos_hub"),
                        "api_resumen": reverse(
                            "ecom:api_lote_resumen", kwargs={"draft_id": draft_id or 0}
                        ),
                        "matriz_readonly": reverse_matriz_readonly(draft_id or 0),
                        "aprobacion_lote_aprobar": reverse(
                            "ecom:api_aprobacion_lote_aprobar",
                            kwargs={"draft_id": draft_id or 0},
                        ),
                        "aprobacion_lote_rechazar": reverse(
                            "ecom:api_aprobacion_lote_rechazar",
                            kwargs={"draft_id": draft_id or 0},
                        ),
                    },
                },
                "lote_cliente": lote.get("cliente") or "",
            }
        )
        return context


class LoteResumenAPIView(APIView):
    """GET ``/ecom/api/mayoristapp/pedidos/lote/<draft_id>/`` — JSON del resumen."""

    permission_classes = [EcomPedidosVerPermission]

    def get(self, request: Request, draft_id: int) -> Response:
        sess = _session_user(request)
        base = str(sess.get("base_empresa") or "").strip()
        if not base:
            return _error("Sin base_empresa.", "sin_base_empresa")
        try:
            payload = construir_resumen_lote(base, int(draft_id), sess)
        except LoteResumenError as exc:
            return _error(exc.message, "lote_resumen", exc.status)
        return Response(payload)


class AprobacionLoteAprobarAPIView(APIView):
    """POST ``/ecom/api/mayoristapp/aprobacion/lote/<draft_id>/aprobar/``"""

    permission_classes = [EcomPedidosAprobarPermission]

    def post(self, request: Request, draft_id: int) -> Response:
        sess = _session_user(request)
        base = str(sess.get("base_empresa") or "").strip()
        if not base:
            return _error("Sin base_empresa.", "sin_base_empresa")
        if not aprobacion_pedidos_activa(base):
            return _error(
                "La aprobación comercial no está activa para esta empresa.",
                "aprobacion_inactiva",
            )
        try:
            draft = cargar_draft_resumen(base, int(draft_id), sess)
        except LoteResumenError as exc:
            return _error(exc.message, "lote_resumen", exc.status)
        ctx = ctx_desde_request(request)
        aprobador = to_int_or_none(
            ctx.get("id_vendedor_usr") or ctx.get("CodViajante") or ctx.get("cod_viajante")
        )
        if aprobador is None:
            return _error("No se pudo resolver el vendedor aprobador.", "sin_vendedor")
        data = request.data if isinstance(request.data, dict) else {}
        motivo = str(data.get("motivo") or "").strip() or "Aprobado"
        ok, msg, payload = resolver_lote_masivo(
            base, draft, "aprobar", aprobador, motivo, sess_user=sess
        )
        if not ok:
            body = {"ok": False, "error": msg, **(payload or {})}
            return Response(body, status=400)
        return Response({"ok": True, "message": msg, **(payload or {})})


class AprobacionLoteRechazarAPIView(APIView):
    """POST ``/ecom/api/mayoristapp/aprobacion/lote/<draft_id>/rechazar/``"""

    permission_classes = [EcomPedidosAprobarPermission]

    def post(self, request: Request, draft_id: int) -> Response:
        sess = _session_user(request)
        base = str(sess.get("base_empresa") or "").strip()
        if not base:
            return _error("Sin base_empresa.", "sin_base_empresa")
        if not aprobacion_pedidos_activa(base):
            return _error(
                "La aprobación comercial no está activa para esta empresa.",
                "aprobacion_inactiva",
            )
        try:
            draft = cargar_draft_resumen(base, int(draft_id), sess)
        except LoteResumenError as exc:
            return _error(exc.message, "lote_resumen", exc.status)
        ctx = ctx_desde_request(request)
        aprobador = to_int_or_none(
            ctx.get("id_vendedor_usr") or ctx.get("CodViajante") or ctx.get("cod_viajante")
        )
        if aprobador is None:
            return _error("No se pudo resolver el vendedor aprobador.", "sin_vendedor")
        data = request.data if isinstance(request.data, dict) else {}
        motivo = str(data.get("motivo") or "").strip()
        if not motivo:
            return _error("Indique el motivo del rechazo.", "motivo_requerido")
        ok, msg, payload = resolver_lote_masivo(
            base, draft, "rechazar", aprobador, motivo, sess_user=sess
        )
        if not ok:
            body = {"ok": False, "error": msg, **(payload or {})}
            return Response(body, status=400)
        return Response({"ok": True, "message": msg, **(payload or {})})


class PedidosHubView(MayoristappWebSessionMixin, TemplateView):
    """Hub Lista|Kanban de pedidos — ``/ecom/mayoristapp/pedidos/``."""

    template_name = "ecom/pedidos_hub.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sess = self.request.session.get("user") or {}
        base = str(sess.get("base_empresa") or "").strip()
        vista = (self.request.GET.get("vista") or "kanban").strip().lower()
        hub = construir_hub_pedidos(base, sess, vista=vista)
        context.update(
            {
                "page_title": "Pedidos",
                "hub_bootstrap": {
                    "vista": hub.get("vista"),
                    "hub": hub,
                    "labels": hub.get("labels") or {},
                    "urls": {
                        "nuevo_simple": url_pedido_masivo_modo_simple(),
                        "nuevo_masivo": reverse("ecom:mayoristapp_pedido_masivo_sucursales"),
                        "kanban_deposito": reverse("ecom:mayoristapp_estado_pedidos_preparacion"),
                        "api": reverse("ecom:mayoristapp_pedidos_hub_api"),
                        "archivar_draft": reverse("ecom:mayoristapp_pedidos_hub_archivar_draft"),
                        "eliminar_draft": reverse("ecom:mayoristapp_pedidos_hub_eliminar_draft"),
                        "migrar_carrito": reverse("ecom:mayoristapp_pedidos_hub_migrar_carrito"),
                        "archivar_carrito": reverse("ecom:mayoristapp_pedidos_hub_archivar_carrito"),
                        "listado_legacy": reverse("ecom:mayoristapp_pedidos_vendedor"),
                        "aprobacion_pendientes": reverse("ecom:api_aprobacion_pendientes"),
                        "aprobacion_aprobar": reverse(
                            "ecom:api_aprobacion_pedido_aprobar", kwargs={"cod_mov": 0}
                        ).replace("/0/", "/{cod_mov}/"),
                        "aprobacion_rechazar": reverse(
                            "ecom:api_aprobacion_pedido_rechazar", kwargs={"cod_mov": 0}
                        ).replace("/0/", "/{cod_mov}/"),
                        "credito_aprobar": reverse(
                            "ecom:api_credito_aprobar", kwargs={"cod_mov": 0}
                        ).replace("/0/", "/{cod_mov}/"),
                        "credito_rechazar": reverse(
                            "ecom:api_credito_rechazar", kwargs={"cod_mov": 0}
                        ).replace("/0/", "/{cod_mov}/"),
                        "credito_cola": reverse("ecom:credito_cola"),
                        # Destino canónico del lote desde el hub (matriz readonly).
                        "lote_matriz_tpl": (
                            reverse("ecom:mayoristapp_pedido_masivo_sucursales")
                            + "?draft={draft_id}&readonly=1"
                        ),
                    },
                },
            }
        )
        return context


class PedidosHubAPIView(APIView):
    """GET JSON del tablero Lista|Kanban."""

    permission_classes = [EcomPedidosVerPermission]

    def get(self, request: Request) -> Response:
        sess = _session_user(request)
        base = str(sess.get("base_empresa") or "").strip()
        if not base:
            return _error("Sin base_empresa.", "sin_base_empresa")
        vista = str(request.query_params.get("vista") or "kanban").strip().lower()
        dias = to_int_or_none(request.query_params.get("dias"))
        hub = construir_hub_pedidos(base, sess, vista=vista, dias=dias)
        return Response({"ok": True, **hub})


class PedidosHubArchivarDraftAPIView(APIView):
    """POST archiva borrador masivo antes de crear uno nuevo."""

    permission_classes = [EcomPedidosVerPermission]

    def post(self, request: Request) -> Response:
        sess = _session_user(request)
        base = str(sess.get("base_empresa") or "").strip()
        id_u = to_int_or_none(sess.get("id_usuario"))
        data = request.data if isinstance(request.data, dict) else {}
        draft_id = to_int_or_none(data.get("draft_id"))
        if not base or id_u is None or draft_id is None:
            return _error("Parámetros inválidos.")
        ok = archivar_borrador_masivo(draft_id, id_u, base)
        if not ok:
            return _error("Borrador no encontrado.", "no_encontrado", 404)
        return Response({"ok": True})


class PedidosHubEliminarDraftAPIView(APIView):
    """POST elimina definitivamente un borrador masivo/simple anulado."""

    permission_classes = [EcomPedidosVerPermission]

    def post(self, request: Request) -> Response:
        sess = _session_user(request)
        base = str(sess.get("base_empresa") or "").strip()
        id_u = to_int_or_none(sess.get("id_usuario"))
        data = request.data if isinstance(request.data, dict) else {}
        draft_id = to_int_or_none(data.get("draft_id"))
        if not base or id_u is None or draft_id is None:
            return _error("Parámetros inválidos.")
        ok, msg = eliminar_borrador_masivo_definitivo(draft_id, id_u, base)
        if not ok:
            status = 404 if msg == "Borrador no encontrado." else 400
            code = "no_encontrado" if status == 404 else "no_permitido"
            return _error(msg, code, status)
        return Response({"ok": True, "message": msg})


class PedidosHubMigrarCarritoAPIView(APIView):
    """POST migra borrador legacy ``EcomCart`` a draft masivo modo simple."""

    permission_classes = [EcomPedidosVerPermission]

    def post(self, request: Request) -> Response:
        sess = _session_user(request)
        base = str(sess.get("base_empresa") or "").strip()
        id_u = to_int_or_none(sess.get("id_usuario"))
        data = request.data if isinstance(request.data, dict) else {}
        cart_id = to_int_or_none(data.get("cart_id"))
        if not base or id_u is None or cart_id is None:
            return _error("Parámetros inválidos.")
        cv = to_int_or_none(sess.get("cod_viajante") or sess.get("codViajante"))
        draft_id, err = migrar_carrito_legacy_a_draft(
            cart_id, id_u, base, cod_viajante=cv
        )
        if err or draft_id is None:
            return _error(err or "No se pudo migrar el carrito.", "migracion_fallida", 400)
        return Response(
            {
                "ok": True,
                "draft_id": draft_id,
                "url": url_pedido_masivo_modo_simple(draft=draft_id),
            }
        )


class PedidosHubArchivarCarritoAPIView(APIView):
    """POST descarta borrador legacy ``EcomCart``."""

    permission_classes = [EcomPedidosVerPermission]

    def post(self, request: Request) -> Response:
        sess = _session_user(request)
        base = str(sess.get("base_empresa") or "").strip()
        id_u = to_int_or_none(sess.get("id_usuario"))
        data = request.data if isinstance(request.data, dict) else {}
        cart_id = to_int_or_none(data.get("cart_id"))
        if not base or id_u is None or cart_id is None:
            return _error("Parámetros inválidos.")
        ok = archivar_carrito_legacy(cart_id, id_u, base)
        if not ok:
            return _error("Carrito no encontrado.", "no_encontrado", 404)
        return Response({"ok": True})


class AprobacionPendientesAPIView(APIView):
    """GET ``/ecom/api/mayoristapp/aprobacion/pendientes/`` — cola comercial scoped."""

    permission_classes = [EcomPedidosAprobarPermission]

    def get(self, request: Request) -> Response:
        sess = _session_user(request)
        base = str(sess.get("base_empresa") or "").strip()
        if not base:
            return _error("Sin base_empresa.", "sin_base_empresa")
        dias = to_int_or_none(request.query_params.get("dias")) or 60
        rows = listar_pendientes_comerciales(base, sess, dias=dias)
        return Response({"ok": True, "total": len(rows), "results": rows})


class AprobacionPedidoAprobarAPIView(APIView):
    """POST ``/ecom/api/mayoristapp/aprobacion/<cod_mov>/aprobar/``"""

    permission_classes = [EcomPedidosAprobarPermission]

    def post(self, request: Request, cod_mov: int) -> Response:
        sess = _session_user(request)
        base = str(sess.get("base_empresa") or "").strip()
        if not base:
            return _error("Sin base_empresa.", "sin_base_empresa")
        ctx = ctx_desde_request(request)
        aprobador = to_int_or_none(
            ctx.get("id_vendedor_usr") or ctx.get("CodViajante") or ctx.get("cod_viajante")
        )
        if aprobador is None:
            return _error("No se pudo resolver el vendedor aprobador.", "sin_vendedor")
        data = request.data if isinstance(request.data, dict) else {}
        motivo = str(data.get("motivo") or "").strip() or "Aprobado"
        ok, msg, payload = resolver(
            base, int(cod_mov), "aprobar", aprobador, motivo, sess_user=sess
        )
        if not ok:
            return _error(msg, "aprobacion_fallida", 400)
        return Response({"ok": True, "message": msg, **(payload or {})})


class AprobacionPedidoRechazarAPIView(APIView):
    """POST ``/ecom/api/mayoristapp/aprobacion/<cod_mov>/rechazar/``"""

    permission_classes = [EcomPedidosAprobarPermission]

    def post(self, request: Request, cod_mov: int) -> Response:
        sess = _session_user(request)
        base = str(sess.get("base_empresa") or "").strip()
        if not base:
            return _error("Sin base_empresa.", "sin_base_empresa")
        ctx = ctx_desde_request(request)
        aprobador = to_int_or_none(
            ctx.get("id_vendedor_usr") or ctx.get("CodViajante") or ctx.get("cod_viajante")
        )
        if aprobador is None:
            return _error("No se pudo resolver el vendedor aprobador.", "sin_vendedor")
        data = request.data if isinstance(request.data, dict) else {}
        motivo = str(data.get("motivo") or "").strip()
        if not motivo:
            return _error("Indique el motivo del rechazo.", "motivo_requerido")
        ok, msg, payload = resolver(
            base, int(cod_mov), "rechazar", aprobador, motivo, sess_user=sess
        )
        if not ok:
            return _error(msg, "aprobacion_fallida", 400)
        return Response({"ok": True, "message": msg, **(payload or {})})


class PedidoDetalleView(MayoristappWebSessionMixin, View):
    """Deprecated: ``/pedidos/<cod_mov>/`` → masivo ``?modo=simple&cod_mov=``."""

    def get(self, request, cod_mov, *args, **kwargs):
        return redirect(url_pedido_masivo_modo_simple(cod_mov=int(cod_mov)))


class ComprobanteComercialCabeceraAPIView(APIView):
    """GET cabecera PED/PRE/DEV por CodigoMovimiento."""

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request, cod_mov: int) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return _error("No se encontró base_empresa en la sesión.", "sin_base_empresa")
        cab = cabecera_comp_ped_relay(base, cod_mov)
        if not cab:
            return _error("Comprobante no encontrado.", "no_encontrado", 404)
        return Response({"ok": True, "cabecera": cab})


class ComprobanteComercialDetalleAPIView(APIView):
    """GET renglones stockp de un comprobante comercial."""

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request, cod_mov: int) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return _error("No se encontró base_empresa en la sesión.", "sin_base_empresa")
        usa_manual = str(request.session.get("usa_id_manual") or "").strip().lower() in (
            "si",
            "sí",
            "1",
            "true",
        )
        rows = detalle_pedido_relay(base, cod_mov, usa_id_manual=usa_manual)
        if not rows:
            cab = cabecera_comp_ped_relay(base, cod_mov)
            if not cab:
                return _error("Comprobante no encontrado.", "no_encontrado", 404)
        return Response({"ok": True, "results": rows})


class ComprobanteComercialDetalleView(MayoristappWebSessionMixin, TemplateView):
    """Detalle read-only de PED/PRE/DEV — ``/ecom/mayoristapp/comprobantes/<cod_mov>/``."""

    template_name = "ecom/comprobante_comercial_detalle.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cod_mov = to_int_or_none(kwargs.get("cod_mov"))
        context.update(
            {
                "page_title": "Detalle de comprobante",
                "cod_mov": cod_mov,
                "urls": {
                    "cabecera": reverse("ecom:mayoristapp_comprobante_cabecera", args=[cod_mov or 0]),
                    "detalle": reverse("ecom:mayoristapp_comprobante_detalle_api", args=[cod_mov or 0]),
                    "compra": reverse("ecom:mayoristapp_venta"),
                    "hub": reverse("ecom:mayoristapp_pedidos_hub"),
                    "listado_pedidos": reverse("ecom:mayoristapp_pedidos_vendedor"),
                    "listado_presupuestos": reverse("ecom:mayoristapp_presupuestos_vendedor"),
                    "detalle_pedido_tpl": reverse("ecom:mayoristapp_venta") + "?cod_mov=0",
                },
            }
        )
        return context
