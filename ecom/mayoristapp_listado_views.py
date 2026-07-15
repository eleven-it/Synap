"""
Vista genérica de listados mayoristapp (F1/F2).
"""

from __future__ import annotations

import json

from django.http import Http404
from django.urls import reverse
from django.views.generic import TemplateView

from ecom.mayoristapp_listado_config import (
    MAYORISTAPP_LISTADOS,
    PORTAL_CLIENTE_LISTADOS,
)
from ecom.mayoristapp_web_views import MayoristappWebSessionMixin
from ecom.services.viajantes_opciones import opciones_viajantes_para_filtro


class ListadoMayoristappView(MayoristappWebSessionMixin, TemplateView):
    """Shell reutilizable para listados POST/GET sobre relays existentes."""

    template_name = "ecom/listado_mayoristapp.html"
    listado_slug: str = ""

    def _config(self) -> dict:
        cfg = MAYORISTAPP_LISTADOS.get(self.listado_slug)
        if not cfg:
            raise Http404("Listado no configurado.")
        return cfg

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cfg = self._config()
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

        api_path = reverse(cfg["api_url_name"])
        query = (cfg.get("api_query") or "").strip()
        api_url = f"{api_path}?{query}" if query else api_path

        sugerencias_url = ""
        sug_name = cfg.get("sugerencias_url_name")
        if sug_name:
            sug_path = reverse(sug_name)
            sug_query = (cfg.get("sugerencias_query") or "ajax=1").strip()
            sugerencias_url = f"{sug_path}?{sug_query}"

        context.update(
            {
                "page_title": cfg["title"],
                "listado_title": cfg["title"],
                "listado_subtitle": cfg.get("subtitle") or "",
                "listado_api_url": api_url,
                "listado_api_method": cfg.get("api_method") or "POST",
                "listado_payload_base": json.dumps(cfg.get("payload_base") or {}),
                "listado_results_key": cfg.get("results_key") or "filas",
                "listado_columns": json.dumps(cfg.get("columns") or []),
                "listado_slug": self.listado_slug,
                "show_vendedor_filter": cfg.get("filter_mode") != "promociones"
                and not cfg.get("portal_cliente"),
                "show_comprobante_filters": cfg.get("filter_mode") != "promociones",
                "filter_mode": cfg.get("filter_mode") or "comprobantes",
                "busca_tipo_label": cfg.get("busca_tipo_label") or "Tipo",
                "viajantes_opciones": viajantes.get("opciones") or [],
                "filtra_vendedor_default": viajantes.get("valor_por_defecto") or "todos",
                "usa_id_manual_cliente": usa_manual,
                "sugerencias_api_url": sugerencias_url,
                "sugerencias_results_key": cfg.get("sugerencias_results_key") or "sugerencias",
                "pedidos_acciones": bool(cfg.get("pedidos_acciones")),
                "pedidos_urls_json": json.dumps(
                    {
                        "detalle_tpl": reverse("ecom:mayoristapp_venta") + "?cod_mov=0",
                        "preview_tpl": reverse(
                            "ecom:mayoristapp_carrito_desde_pedido_preview", args=[0]
                        ),
                        "cargar_desde_pedido": reverse("ecom:mayoristapp_carrito_desde_pedido"),
                        "compra": reverse("ecom:mayoristapp_venta"),
                    }
                )
                if cfg.get("pedidos_acciones")
                else "",
                "es_cliente_portal": bool(cfg.get("portal_cliente")),
            }
        )
        return context


class PortalClienteListadoView(ListadoMayoristappView):
    """Listados F2 con scope idcliente en sesión."""

    listado_slug: str = ""

    def _config(self) -> dict:
        cfg = PORTAL_CLIENTE_LISTADOS.get(self.listado_slug)
        if not cfg:
            raise Http404("Listado portal no configurado.")
        return cfg

    def dispatch(self, request, *args, **kwargs):
        sess = request.session.get("user") or {}
        bag = request.session.get("mayoristapp") or {}
        idc = sess.get("idcliente") or bag.get("idcliente")
        if not idc:
            from django.contrib import messages
            from django.shortcuts import redirect

            messages.warning(
                request,
                "Seleccione un cliente en el portal para acceder a esta pantalla.",
            )
            return redirect("ecom:mayoristapp_clientes")
        return super().dispatch(request, *args, **kwargs)


class ClientesMayoristappView(MayoristappWebSessionMixin, TemplateView):
    """Paridad ``listado-clientes.php`` — búsqueda y selección de cliente."""

    template_name = "ecom/clientes_mayoristapp.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Listado de clientes",
                "clientes_buscar_api": reverse("ecom:mayoristapp_clientes_buscar"),
                "clientes_seleccionar_api": reverse("ecom:mayoristapp_clientes_seleccionar"),
                "clientes_seleccionado_api": reverse("ecom:mayoristapp_clientes_seleccionado"),
            }
        )
        return context


def listado_view_factory(slug: str, portal: bool = False):
    """Genera clase de vista para un slug de listado."""

    if portal:
        return type(
            f"Portal{slug.replace('-', '_').title()}View",
            (PortalClienteListadoView,),
            {"listado_slug": slug},
        )
    return type(
        f"Listado{slug.replace('-', '_').title()}View",
        (ListadoMayoristappView,),
        {"listado_slug": slug},
    )
