"""
Vista genérica de listados mayoristapp (F1/F2).
"""

from __future__ import annotations

import json

from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView
from core.report_pdf import get_empresa_para_reporte

from ecom.mayoristapp_listado_config import (
    MAYORISTAPP_LISTADOS,
    PORTAL_CLIENTE_LISTADOS,
)
from ecom.mayoristapp_web_views import MayoristappWebSessionMixin
from ecom.services.cliente_relay import cliente_accesible_por_sesion
from ecom.services.mayoristapp_session import leer_cliente_seleccionado, leer_idcliente_mayoristapp
from ecom.services.viajantes_opciones import opciones_viajantes_para_filtro
from ecom.services.cartera_reportes_pdf import generar_pdf_cartera
from ecom.services.comprobantes_no_cancelados_relay import listar_no_cancelados_relay
from ecom.services.ctacte_relay import listar_movimientos_ctacte_relay


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
                "listado_pdf_url": reverse("ecom:mayoristapp_cartera_pdf", args=[self.listado_slug])
                if cfg.get("portal_cliente") and self.listado_slug in ("cuenta-corriente", "no-cancelados") else "",
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
                "detalle_comprobante": bool(
                    cfg.get("portal_cliente") and self.listado_slug in ("cuenta-corriente", "no-cancelados")
                ),
            }
        )
        if cfg.get("portal_cliente") and self.listado_slug in ("cuenta-corriente", "no-cancelados"):
            try:
                empresa_reporte = get_empresa_para_reporte(base)
            except Exception:
                empresa_reporte = {}
            cliente_guardado = leer_cliente_seleccionado(self.request)
            cliente = cliente_guardado[0] if isinstance(cliente_guardado, list) and cliente_guardado else cliente_guardado
            cliente = cliente if isinstance(cliente, dict) else {}
            codigo = cliente.get("Codigo") or leer_idcliente_mayoristapp(self.request)
            nombre = cliente.get("cliente") or cliente.get("nombre_cliente") or "Cliente seleccionado"
            domicilios = (self.request.session.get("mayoristapp") or {}).get("domicilios_cliente") or []
            primer_domicilio = domicilios[0] if domicilios and isinstance(domicilios[0], dict) else {}
            domicilio_texto = " ".join(str(primer_domicilio.get(campo) or "") for campo in (
                "Calle", "NroCalle", "Dpto", "NombreDistrito", "Provincia"
            )).strip()
            reporte = "cobrar" if self.listado_slug == "no-cancelados" else "ctacte"
            context.update({
                "cliente_reporte_nombre": nombre,
                "cliente_reporte_codigo": codigo,
                "cliente_reporte_cuit": cliente.get("CUIT") or "",
                "cliente_reporte_domicilio": domicilio_texto,
                "empresa_reporte_nombre": empresa_reporte.get("razon_social") or "",
                "empresa_reporte_cuit": empresa_reporte.get("cuit_formateado") or "",
                "cliente_reporte_cambiar_url": f"{reverse('ecom:mayoristapp_cobranzas_cartera')}?reporte={reporte}",
                "cliente_reporte_buscar_api": f"{reverse('ecom:mayoristapp_clientes_buscar')}?cartera=1",
                "cliente_reporte_seleccionar_api": reverse('ecom:mayoristapp_clientes_seleccionar'),
                "cliente_reporte_seleccionado_api": reverse('ecom:mayoristapp_clientes_seleccionado'),
                "cliente_reporte_url": self.request.path,
                "listado_empty_message": (
                    "Este cliente no tiene comprobantes pendientes de cobro."
                    if reporte == "cobrar" else "Este cliente no tiene movimientos en cuenta corriente."
                ),
            })
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
        base = str(sess.get("base_empresa") or "").strip()
        if base and not cliente_accesible_por_sesion(base, idc, sess, solo_cartera=True):
            from django.contrib import messages
            from django.shortcuts import redirect
            from ecom.services.mayoristapp_session import limpiar_cliente_seleccion_mayoristapp

            limpiar_cliente_seleccion_mayoristapp(request)
            messages.warning(request, "El cliente ya no pertenece a tu cartera.")
            return redirect("ecom:mayoristapp_cobranzas_cartera")
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


class CobranzasCarteraMayoristappView(ClientesMayoristappView):
    """Selección de un cliente de la cartera para consultar saldos y comprobantes."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reporte = self.request.GET.get("reporte", "")
        destinos = {
            "cobrar": ("Comprobantes a cobrar por cliente", "ecom:mayoristapp_portal_no_cancelados"),
            "ctacte": ("Cuenta corriente por cliente", "ecom:mayoristapp_portal_cuenta_corriente"),
        }
        context["page_title"] = destinos.get(reporte, ("Cobranzas de cartera", ""))[0]
        context["page_intro"] = "Elegí un cliente de tu cartera para consultar el reporte."
        context["reporte_destino"] = reporte if reporte in destinos else ""
        context["reporte_url"] = reverse(destinos[reporte][1]) if reporte in destinos else ""
        context["clientes_buscar_api"] = f"{context['clientes_buscar_api']}?cartera=1"
        return context


class CarteraReportePDFView(MayoristappWebSessionMixin, View):
    """Entrega un PDF real limitado al cliente seleccionado y a la cartera del vendedor."""

    def get(self, request, slug):
        if slug not in ("cuenta-corriente", "no-cancelados"):
            raise Http404("Reporte no disponible.")
        sess = request.session.get("user") or {}
        base = str(sess.get("base_empresa") or "").strip()
        idc = leer_idcliente_mayoristapp(request)
        if not idc or not cliente_accesible_por_sesion(base, idc, sess, solo_cartera=True):
            return HttpResponseForbidden("Cliente fuera de tu cartera.")
        filtros = {clave: request.GET.get(clave, "") for clave in
                   ("campoBusca", "fechaDesde", "fechaHasta", "numeroComp")}
        if slug == "no-cancelados":
            filtros["solo_cobranzas"] = True
            resultado = listar_no_cancelados_relay(base, filtros, idc, limit=5000)
            filas = resultado["filas"]
            saldo = resultado["saldo_al_dia"]
        else:
            filtros["limit"] = 2000
            filas = listar_movimientos_ctacte_relay(base, filtros, idc, limit=2000)
            saldo = filas[0].get("saldo") if filas else 0
        cliente_guardado = leer_cliente_seleccionado(request)
        cliente_raw = cliente_guardado[0] if isinstance(cliente_guardado, list) and cliente_guardado else cliente_guardado
        cliente_raw = cliente_raw if isinstance(cliente_raw, dict) else {}
        domicilios = (request.session.get("mayoristapp") or {}).get("domicilios_cliente") or []
        domicilio = domicilios[0] if domicilios and isinstance(domicilios[0], dict) else {}
        cliente = {
            "nombre": cliente_raw.get("cliente") or cliente_raw.get("nombre_cliente") or "Cliente seleccionado",
            "codigo": cliente_raw.get("Codigo") or idc,
            "cuit": cliente_raw.get("CUIT") or "",
            "domicilio": " ".join(str(domicilio.get(c) or "") for c in
                                   ("Calle", "NroCalle", "Dpto", "NombreDistrito", "Provincia")).strip(),
        }
        pdf = generar_pdf_cartera(slug, filas, get_empresa_para_reporte(base), cliente, filtros, saldo)
        respuesta = HttpResponse(pdf, content_type="application/pdf")
        respuesta["Content-Disposition"] = f'inline; filename="{slug}-{idc}.pdf"'
        return respuesta


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
