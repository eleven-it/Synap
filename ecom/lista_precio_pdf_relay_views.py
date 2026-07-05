"""
Vista del export de lista de precios mayorista a PDF (Fase P3).

GET /ecom/api/mayoristapp/catalogo/lista-precios.pdf → descarga el PDF, o una página
HTML amigable (español) si se supera el límite de volumen/tiempo (paridad runbook).
"""

from __future__ import annotations

from django.http import HttpResponse
from rest_framework.request import Request
from rest_framework.views import APIView

from core.utils.administranet_types import to_int_or_none
from ecom.catalogo_producto_relay_views import (
    _obtener_id_deposito,
    _obtener_lista_id_y_cliente,
    _session_base_empresa,
    _session_pv_activo,
)
from ecom.permissions import EcomMayoristappSessionPermission
from ecom.services import lista_precio_pdf as svc
from ecom.services.catalogo_restricciones import aplicar_restricciones_a_filtros


def _filtros_desde_get(request: Request) -> dict:
    g = request.query_params
    filtros = {}
    for clave, campo in (("rubro", "rubro"), ("subrubro", "subrubro"), ("marca", "marca"),
                         ("laboratorio", "laboratorio"), ("proveedor", "proveedor")):
        val = to_int_or_none(g.get(campo))
        if val is not None:
            filtros[clave] = val
    q = (g.get("q") or g.get("queArticulo") or "").strip()
    if q:
        filtros["q"] = q
    if (g.get("promo") or "").strip().lower() in ("si", "sí", "1", "true"):
        filtros["solo_promocion"] = True
    return filtros


def _encabezado_desde_get(request: Request) -> dict:
    g = request.query_params
    partes = [g.get(k) for k in ("categoriaText", "rubroText", "subrubroText", "marcaText") if g.get(k)]
    return {
        "filtros_texto": " > ".join(p for p in partes if p) or "TODOS LOS PRODUCTOS",
        "cliente_texto": (g.get("clienteTexto") or "").strip() or "GENERAL / CONSUMIDOR FINAL",
    }


class ExportarListaPreciosPDFRelayAPIView(APIView):
    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> HttpResponse:
        base = _session_base_empresa(request)
        if not base:
            return HttpResponse("No se encontró la empresa en la sesión.", status=400)

        try:
            lista_id, codigo_cliente, descuento_cliente, iva_incluido = _obtener_lista_id_y_cliente(request, base)
        except Exception:
            return HttpResponse("No se pudo resolver la lista de precio o el cliente.", status=500)

        id_deposito = _obtener_id_deposito(request)
        con_imagenes = (request.query_params.get("imagenProducto") or "").strip().lower() in ("si", "sí", "1", "true")

        try:
            ok, error, pdf = svc.exportar_lista_precios_pdf(
                base,
                filtros=aplicar_restricciones_a_filtros(
                    _filtros_desde_get(request), base, _session_pv_activo(request)
                ),
                lista_id=lista_id,
                codigo_cliente=codigo_cliente,
                descuento_cliente=descuento_cliente,
                iva_incluido=iva_incluido,
                id_deposito=id_deposito,
                con_imagenes=con_imagenes,
                encabezado=_encabezado_desde_get(request),
            )
        except Exception:
            return HttpResponse("No se pudo generar la lista de precios.", status=500)

        if not ok:
            return HttpResponse(_pagina_limite_html(error or {}), content_type="text/html; charset=utf-8", status=200)

        resp = HttpResponse(pdf, content_type="application/pdf")
        resp["Content-Disposition"] = 'inline; filename="lista-precios.pdf"'
        return resp


def _pagina_limite_html(error: dict) -> str:
    cantidad = error.get("cantidad", 0)
    con_img = error.get("con_imagenes", False)
    detalle = (error.get("detalle") or "").strip()
    detalle_html = f'<p class="det">Búsqueda: <strong>{detalle}</strong></p>' if detalle else ""
    if error.get("tipo") == svc.ERROR_VOLUMEN:
        limite = error.get("limite", 0)
        titulo = "La lista tiene demasiados productos"
        cuerpo = (
            f"Se encontraron <strong>{cantidad}</strong> productos y el máximo permitido "
            f"{'con imágenes ' if con_img else ''}es <strong>{limite}</strong>. "
            "Aplicá más filtros (rubro, marca, búsqueda) para reducir el listado"
            f"{' o exportá sin imágenes' if con_img else ''}."
        )
    else:
        segundos = error.get("segundos", 0)
        titulo = "La lista está tardando demasiado"
        cuerpo = (
            f"La generación superó el tiempo máximo de <strong>{segundos} s</strong> "
            f"para <strong>{cantidad}</strong> productos"
            f"{' con imágenes' if con_img else ''}. "
            "Reducí los filtros"
            f"{' o exportá sin imágenes' if con_img else ''} e intentá de nuevo."
        )
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lista de precios</title>
<style>
  body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:#f1f5f9;color:#1e293b;margin:0;padding:2rem}}
  .card{{max-width:640px;margin:3rem auto;background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:2rem;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
  h1{{font-size:1.25rem;margin:0 0 .75rem;color:#1a2a3a}}
  p{{line-height:1.5}} .det{{color:#475569;font-size:.9rem}}
  .btn{{display:inline-block;margin-top:1rem;background:#1a2a3a;color:#fff;padding:.6rem 1.2rem;border-radius:8px;text-decoration:none;border:0;cursor:pointer}}
</style></head>
<body><div class="card">
  <h1>{titulo}</h1>
  <p>{cuerpo}</p>
  {detalle_html}
  <button class="btn" onclick="history.back()">Volver</button>
</div></body></html>"""
