"""
APIs y vistas HTML de gestión comercial de pedidos (PED).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from django.http import HttpResponse
from django.urls import reverse
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
    EcomPedidosVerPermission,
)
from ecom.services.pedidos_hub_pipeline import (
    archivar_borrador_masivo,
    construir_hub_pedidos,
)
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
        return Response(
            {
                "ok": True,
                "es_cliente": _es_cliente_sesion(request),
                "id_punto_venta_default": id_pv,
                "puntos_venta": puntos,
                "idcliente": leer_idcliente_mayoristapp(request),
                "cliente": cliente,
                "autoriza_credito": autoriza_credito,
                "embalaje": embalaje_cfg,
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
                        "nuevo_simple": reverse("ecom:mayoristapp_compra"),
                        "nuevo_masivo": reverse("ecom:mayoristapp_pedido_masivo_sucursales"),
                        "kanban_deposito": reverse("ecom:mayoristapp_estado_pedidos_preparacion"),
                        "api": reverse("ecom:mayoristapp_pedidos_hub_api"),
                        "archivar_draft": reverse("ecom:mayoristapp_pedidos_hub_archivar_draft"),
                        "listado_legacy": reverse("ecom:mayoristapp_pedidos_vendedor"),
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
        dias = to_int_or_none(request.query_params.get("dias")) or 60
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


class PedidoDetalleView(MayoristappWebSessionMixin, TemplateView):
    """Detalle de pedido — ``/ecom/mayoristapp/pedidos/<cod_mov>/``."""

    template_name = "ecom/pedido_detalle.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cod_mov = to_int_or_none(kwargs.get("cod_mov"))
        sess = self.request.session.get("user") or {}
        usa_manual = str(self.request.session.get("usa_id_manual") or "").strip().lower() in (
            "si",
            "sí",
            "1",
            "true",
        )
        context.update(
            {
                "page_title": "Detalle de pedido",
                "cod_mov": cod_mov,
                "es_cliente": (sess.get("tipousuario") or "").strip().lower() == "cliente",
                "usa_id_manual": usa_manual,
                "urls": {
                    "cabecera": reverse("ecom:v1_comprobantes_pedidos_cabecera", args=[cod_mov or 0]),
                    "detalle": reverse("ecom:v1_comprobantes_pedidos_detalle", args=[cod_mov or 0]),
                    "anular": reverse("ecom:mayoristapp_comprobantes_anular_pedido") + "?ajax=1",
                    "mail_enqueue": reverse("ecom:mayoristapp_comprobantes_comprobante_a_mail_enqueue")
                    + "?ajax=1",
                    "compra": reverse("ecom:mayoristapp_compra"),
                    "listado": reverse("ecom:mayoristapp_pedidos_vendedor"),
                    "hub": reverse("ecom:mayoristapp_pedidos_hub"),
                    "kanban": reverse("ecom:mayoristapp_estado_pedidos_preparacion"),
                    "preview_tpl": reverse(
                        "ecom:mayoristapp_carrito_desde_pedido_preview", args=[cod_mov or 0]
                    ),
                    "cargar_desde_pedido": reverse("ecom:mayoristapp_carrito_desde_pedido"),
                    "pdf": reverse("ecom:mayoristapp_pedido_pdf", args=[cod_mov or 0]),
                },
            }
        )
        return context


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
                    "compra": reverse("ecom:mayoristapp_compra"),
                    "hub": reverse("ecom:mayoristapp_pedidos_hub"),
                    "listado_pedidos": reverse("ecom:mayoristapp_pedidos_vendedor"),
                    "listado_presupuestos": reverse("ecom:mayoristapp_presupuestos_vendedor"),
                    "detalle_pedido_tpl": reverse("ecom:mayoristapp_pedido_detalle", args=[0]),
                },
            }
        )
        return context
