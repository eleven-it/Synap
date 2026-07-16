"""
Vistas HTML mayoristapp (UX migrada desde PHP), sesión administraNET.
"""

from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView
from urllib.parse import parse_qs, urlencode

from core.utils.administranet_types import to_int_or_none
from ecom.mayoristapp_listado_config import HUB_LISTADO_URLS
from ecom.services.ecom_module_settings import ecom_cobranzas_write_enabled
from ecom.services.mayorista_cart_service import reiniciar_borrador_compra_vendedor
from ecom.services.mayoristapp_session import (
    leer_cliente_seleccionado,
    leer_idcliente_mayoristapp,
    limpiar_cliente_seleccion_mayoristapp,
)
from ecom.services.mayoristapp_sesion_contexto import asegurar_contexto_mayoristapp
from ecom.services.pedido_cabecera_relay import (
    cabecera_pedido_relay,
    puede_anular_pedido_relay,
    stepper_estados_pedido,
    vinculos_pedido_relay,
)
from ecom.services.comprobantes_relay import detalle_pedido_relay
from ecom.services.viajantes_opciones import opciones_viajantes_para_filtro


class MayoristappWebSessionMixin:
    """Sesión con ``user`` + ``base_empresa`` (legacy MySQL)."""

    def dispatch(self, request, *args, **kwargs):
        if "user" not in request.session:
            return redirect("login:login")
        if not getattr(request.user, "is_authenticated", False):
            return redirect("login:login")
        data = request.session.get("user") or {}
        if not data.get("base_empresa"):
            messages.warning(request, "Seleccione una empresa con base de datos para usar el portal mayorista.")
            return redirect("core:dashboard")
        asegurar_contexto_mayoristapp(request)
        return super().dispatch(request, *args, **kwargs)


def _hub_link(label: str, *, enabled: bool = True, note: str = "", **kwargs):
    """Arma entrada de card hub; activa URL desde HUB_LISTADO_URLS si existe."""
    entry = {"label": label, "enabled": enabled, **kwargs}
    if note:
        entry["note"] = note
    url_name = HUB_LISTADO_URLS.get(label)
    if url_name and enabled and "url_name" not in entry:
        entry["url_name"] = url_name
    return entry


def _hub_cards():
    """Cards 1:1 con ``componente-menu-card-dashboard.php`` (rutas Synap)."""
    return [
        {
            "title": "Ventas",
            "icon": "shopping_cart",
            "links": [
                {"label": "Nuevo pedido", "url_name": "ecom:mayoristapp_venta", "enabled": True},
                {"label": "Pedidos", "url_name": "ecom:mayoristapp_pedidos_hub", "enabled": True},
                {
                    "label": "Lista de precios PDF",
                    "url_name": "ecom:mayoristapp_lista_precios_pdf",
                    "enabled": True,
                    "external": True,
                },
                _hub_link("Promociones"),
            ],
        },
        {
            "title": "Logística",
            "icon": "local_shipping",
            "links": [
                {
                    "label": "Preparación de pedidos",
                    "url_name": "ecom:mayoristapp_estado_pedidos_preparacion",
                    "enabled": True,
                },
                {
                    "label": "Comprobantes en ruta",
                    "url_name": "reports:dashboard_detail",
                    "url_kwargs": {"slug": "comprobantes-rutas"},
                    "enabled": True,
                },
                _hub_link("Devoluciones"),
            ],
        },
        {
            "title": "Clientes",
            "icon": "groups",
            "links": [
                _hub_link("Listado de clientes"),
                _hub_link("Consumos cliente"),
                _hub_link("Cuenta corriente"),
                _hub_link("Comprobantes no cancelados"),
            ],
        },
        {
            "title": "Stock",
            "icon": "inventory_2",
            "links": [
                {"label": "Inventario", "enabled": False, "note": "Fase 3"},
                {
                    "label": "Stock y existencias",
                    "url_name": "reports:dashboard_detail",
                    "url_kwargs": {"slug": "stock-existencias"},
                    "enabled": True,
                },
                _hub_link("Artículos remitados"),
            ],
        },
        {
            "title": "Comprobantes emitidos",
            "icon": "description",
            "links": [
                {
                    "label": "Presupuestos",
                    "url_name": "ecom:mayoristapp_presupuestos_vendedor",
                    "enabled": True,
                },
                _hub_link("Facturas"),
                _hub_link("Recibos web"),
                {
                    "label": "Alta recibo",
                    "url_name": "ecom:mayoristapp_alta_recibo",
                    "enabled": True,
                },
                _hub_link("Nota de crédito"),
                _hub_link("Remitos"),
            ],
        },
        {
            "title": "Estadísticas",
            "icon": "insights",
            "links": [
                {
                    "label": "Clientes sin ventas",
                    "url_name": "reports:dashboard_detail",
                    "url_kwargs": {"slug": "clientes-sin-ventas-vendedor"},
                    "enabled": True,
                },
                {
                    "label": "Rentabilidad",
                    "url_name": "reports:dashboard_detail",
                    "url_kwargs": {"slug": "utilidad-gerencial"},
                    "enabled": True,
                },
                {
                    "label": "Cobranzas",
                    "url_name": "reports:dashboard_detail",
                    "url_kwargs": {"slug": "cobranzas-por-vendedor"},
                    "enabled": True,
                },
            ],
        },
        {
            "title": "Premios",
            "icon": "card_giftcard",
            "links": [
                {"label": "Módulo premios", "enabled": False, "note": "Fase 3"},
            ],
        },
    ]


class HubMayoristappView(MayoristappWebSessionMixin, TemplateView):
    """Paridad ``dashboard-modulos.php``: hub de navegación del portal mayorista."""

    template_name = "ecom/hub_mayoristapp.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cards = []
        for card in _hub_cards():
            links = []
            for link in card["links"]:
                item = dict(link)
                if item.get("enabled") and item.get("url_name"):
                    kwargs_url = item.pop("url_kwargs", None) or {}
                    item["href"] = reverse(item.pop("url_name"), kwargs=kwargs_url)
                else:
                    item["href"] = None
                links.append(item)
            cards.append({**card, "links": links})
        context.update(
            {
                "page_title": "Portal mayorista",
                "hub_cards": cards,
            }
        )
        return context


class PresupuestosVendedorView(MayoristappWebSessionMixin, TemplateView):
    """
    Paridad ``lista-presupuestos-vendedor.php``: filtros + listado de presupuestos (PRE).
    Los datos se cargan vía POST JSON a la API ``relay-presupuestos`` ya migrada.
    """

    template_name = "ecom/presupuestos_vendedor.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sess_user = self.request.session.get("user") or {}
        base = str(sess_user.get("base_empresa") or "").strip()

        viajantes = {"opciones": [], "valor_por_defecto": "todos", "mostrar_opcion_todos": True}
        try:
            viajantes = opciones_viajantes_para_filtro(base, sess_user)
        except Exception:
            pass

        usa_manual = str(self.request.session.get("usa_id_manual") or "").strip().lower() in (
            "si",
            "sí",
            "1",
            "true",
        )

        context.update(
            {
                "page_title": "Presupuestos del vendedor",
                "presupuestos_api_url": reverse("ecom:mayoristapp_comprobantes_presupuestos"),
                "presupuestos_sugerencias_api_url": (
                    reverse("ecom:mayoristapp_comprobantes_sugerencias_nro") + "?ajax=1&tipo=PRE"
                ),
                "viajantes_opciones": viajantes.get("opciones") or [],
                "filtra_vendedor_default": viajantes.get("valor_por_defecto") or "todos",
                "usa_id_manual_cliente": usa_manual,
                "urls": {
                    "hub": reverse("ecom:mayoristapp_pedidos_hub"),
                    "convertir_tpl": reverse("ecom:mayoristapp_presupuesto_convertir_pedido", args=[0]),
                },
            }
        )
        return context


class PedidosVendedorView(MayoristappWebSessionMixin, TemplateView):
    """
    Paridad ``lista-pedidos-vendedor.php``: filtros + listado de pedidos (PED).
    Datos vía API REST v1 ``POST …/comprobantes/pedidos/``.
    """

    template_name = "ecom/pedidos_vendedor.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sess_user = self.request.session.get("user") or {}
        base = str(sess_user.get("base_empresa") or "").strip()

        viajantes = {"opciones": [], "valor_por_defecto": "todos", "mostrar_opcion_todos": True}
        try:
            viajantes = opciones_viajantes_para_filtro(base, sess_user)
        except Exception:
            pass

        usa_manual = str(self.request.session.get("usa_id_manual") or "").strip().lower() in (
            "si",
            "sí",
            "1",
            "true",
        )

        context.update(
            {
                "page_title": "Pedidos del vendedor",
                "pedidos_api_url": reverse("ecom:v1_comprobantes_pedidos"),
                "pedidos_sugerencias_api_url": reverse("ecom:v1_comprobantes_pedidos_sugerencias"),
                "viajantes_opciones": viajantes.get("opciones") or [],
                "filtra_vendedor_default": viajantes.get("valor_por_defecto") or "todos",
                "usa_id_manual_cliente": usa_manual,
                "urls": {
                    "nuevo_pedido": reverse("ecom:mayoristapp_venta"),
                    "hub": reverse("ecom:mayoristapp_pedidos_hub"),
                    "detalle_tpl": reverse("ecom:mayoristapp_venta") + "?cod_mov=0",
                    "pdf_tpl": reverse("ecom:mayoristapp_pedido_pdf", args=[0]),
                    "anular": reverse("ecom:mayoristapp_comprobantes_anular_pedido") + "?ajax=1",
                    "mail_enqueue": reverse("ecom:mayoristapp_comprobantes_comprobante_a_mail_enqueue")
                    + "?ajax=1",
                    "preview_tpl": reverse("ecom:mayoristapp_carrito_desde_pedido_preview", args=[0]),
                    "cargar_desde_pedido": reverse("ecom:mayoristapp_carrito_desde_pedido"),
                    "compra": reverse("ecom:mayoristapp_venta"),
                },
            }
        )
        return context


class CompraMayoristaView(MayoristappWebSessionMixin, View):
    """
    Deprecated: OrderShell ya no se sirve activamente.
    Redirect 302 a pedido masivo ``?modo=simple`` preservando query string.
    """

    def get(self, request, *args, **kwargs):
        destino = reverse("ecom:mayoristapp_pedido_masivo_sucursales")
        params = parse_qs(request.META.get("QUERY_STRING", ""))
        params["modo"] = ["simple"]
        qs = urlencode(params, doseq=True)
        return redirect(f"{destino}?{qs}")


class AltaReciboMayoristappView(MayoristappWebSessionMixin, TemplateView):
    """
    Paridad ``recibo/alta_recibo.php``: wizard por pasos (inicio → imputación → medios → guardar).
    Requiere cliente seleccionado en sesión.
    """

    template_name = "ecom/alta_recibo_mayoristapp.html"

    def dispatch(self, request, *args, **kwargs):
        if leer_idcliente_mayoristapp(request) is None:
            messages.info(request, "Seleccione un cliente para registrar un recibo.")
            return redirect("ecom:mayoristapp_clientes")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sess_user = self.request.session.get("user") or {}
        cliente = leer_cliente_seleccionado(self.request)
        cliente_datos = {}
        if isinstance(cliente, (list, tuple)) and cliente:
            cliente_datos = cliente[0] if isinstance(cliente[0], dict) else {}
        elif isinstance(cliente, dict):
            cliente_datos = cliente

        nombre = (
            cliente_datos.get("nombre_cliente")
            or cliente_datos.get("Nombre")
            or cliente_datos.get("nombre")
            or "Cliente"
        )
        context.update(
            {
                "page_title": "Alta de recibo",
                "cliente_nombre": nombre,
                "cliente_codigo": leer_idcliente_mayoristapp(self.request),
                "cliente_saldo": cliente_datos.get("saldo") or cliente_datos.get("Saldo") or 0,
                "id_caja_usuario": sess_user.get("id_caja") or sess_user.get("id_caja_usr"),
                "cobranzas_write_enabled": ecom_cobranzas_write_enabled(),
                "api_alta_accion": reverse("ecom:mayoristapp_recibos_alta_accion"),
                "api_alta_catalogos": reverse("ecom:mayoristapp_recibos_alta_catalogos"),
                "api_imputar_listado": reverse("ecom:mayoristapp_fe_facturas_imputar_listado"),
                "api_imputar_accion": reverse("ecom:mayoristapp_fe_facturas_imputar_accion"),
                "url_clientes": reverse("ecom:mayoristapp_clientes"),
                "url_recibos": reverse("ecom:mayoristapp_listado_recibos"),
            }
        )
        return context
