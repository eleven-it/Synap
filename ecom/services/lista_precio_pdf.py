"""
Export de la lista de precios mayorista a PDF (Fase P3).

Migra `administraNET-ecom/mayoristapp/exporta_lista_pdf.php` a Synap con reportlab.
Reutiliza el catálogo P0 (mismos filtros y motor de precios) sin paginar, y aplica los
guardrails del runbook (`docs/general/RUNBOOK_EXPORTACION_PDF.md`):

- Corte por VOLUMEN antes de renderizar (LP_PDF_MAX_ITEMS[_CON_IMAGEN]).
- Corte por TIEMPO durante el armado (LP_PDF_MAX_SECONDS[_CON_IMAGEN]), revisado cada 50 filas.
- Página amigable en español cuando se supera un límite (la arma la vista).

El costo real en Synap está en el cálculo de precio por fila (reglas/promos con consultas),
por eso el presupuesto de tiempo envuelve el armado de datos (no el render de reportlab).
"""

from __future__ import annotations

import io
import logging
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings

from core.mysql_pool import get_mysql_pool
from core.report_pdf import get_empresa_para_reporte
from core.utils.administranet_types import str_or_default
from ecom.services.catalogo_producto import contar_articulos_catalogo, obtener_filas_catalogo
from ecom.services.price_rules_engine import calcular_precio_articulo_row

logger = logging.getLogger(__name__)

_NOMBRE_LISTA = {1: "Lista 1", 2: "Lista 2", 3: "Lista 3", 4: "Lista 4", 5: "Lista 5", 6: "Lista Oficial"}

# Errores de guardrail (la vista los traduce a una página HTML amigable)
ERROR_VOLUMEN = "volumen"
ERROR_TIEMPO = "tiempo"


def _lp_int(name: str, default: int) -> int:
    try:
        return int(getattr(settings, name, default) or default)
    except (TypeError, ValueError):
        return default


def _fmt_money(v: Decimal) -> str:
    """Formato es-AR: separador de miles '.' y decimales ','."""
    q = (v if isinstance(v, Decimal) else Decimal(str(v or 0))).quantize(Decimal("0.01"))
    entero, dec = f"{abs(q):.2f}".split(".")
    grupos = []
    while len(entero) > 3:
        grupos.insert(0, entero[-3:])
        entero = entero[:-3]
    grupos.insert(0, entero)
    signo = "-" if q < 0 else ""
    return f"{signo}${'.'.join(grupos)},{dec}"


def exportar_lista_precios_pdf(
    base_empresa: str,
    *,
    filtros: Optional[Dict[str, Any]] = None,
    lista_id: int,
    codigo_cliente: Optional[int],
    descuento_cliente: Decimal,
    iva_incluido: bool,
    id_deposito: int,
    con_imagenes: bool = False,
    encabezado: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[bytes]]:
    """
    Genera el PDF de lista de precios. Devuelve (ok, error_info, pdf_bytes).

    error_info (cuando ok=False):
        {"tipo": ERROR_VOLUMEN|ERROR_TIEMPO, "cantidad": int, "limite"/"segundos": int,
         "con_imagenes": bool, "detalle": str}
    """
    filtros = filtros or {}
    max_items = _lp_int("LP_PDF_MAX_ITEMS_CON_IMAGEN", 1800) if con_imagenes else _lp_int("LP_PDF_MAX_ITEMS", 2500)
    max_seconds = _lp_int("LP_PDF_MAX_SECONDS_CON_IMAGEN", 180) if con_imagenes else _lp_int("LP_PDF_MAX_SECONDS", 90)
    detalle = str_or_default((filtros or {}).get("q"), "")

    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        total = contar_articulos_catalogo(base_empresa, filtros=filtros, conn=conn)
        if total > max_items:
            return False, {
                "tipo": ERROR_VOLUMEN, "cantidad": total, "limite": max_items,
                "con_imagenes": con_imagenes, "detalle": detalle,
            }, None

        filas = obtener_filas_catalogo(base_empresa, filtros=filtros, conn=conn)
        t0 = time.monotonic()
        data_rows: List[List[str]] = []
        for idx, art in enumerate(filas):
            if idx and idx % 50 == 0 and (time.monotonic() - t0) > max_seconds:
                return False, {
                    "tipo": ERROR_TIEMPO, "cantidad": total, "segundos": max_seconds,
                    "con_imagenes": con_imagenes, "detalle": detalle,
                }, None
            precio = calcular_precio_articulo_row(
                art,
                lista_id=lista_id,
                codigo_cliente=codigo_cliente,
                descuento_cliente=descuento_cliente,
                iva_incluido=iva_incluido,
                conn=conn,
            )
            data_rows.append([
                str_or_default(art.get("NombreRubro"), ""),
                str_or_default(art.get("NombreSubRubro"), ""),
                str_or_default(art.get("id_manual") or art.get("CodigoArticuloT"), ""),
                str_or_default(art.get("NombreArticulo"), ""),
                _fmt_money(precio),
                "Sí" if str_or_default(art.get("promocion"), "No").strip().lower() == "si" else "",
            ])

    empresa = get_empresa_para_reporte(base_empresa)
    pdf = _render_pdf(
        data_rows,
        empresa=empresa,
        iva_incluido=iva_incluido,
        lista_nombre=_NOMBRE_LISTA.get(lista_id, f"Lista {lista_id}"),
        encabezado=encabezado or {},
        total=total,
    )
    return True, None, pdf


def _render_pdf(
    data_rows: List[List[str]],
    *,
    empresa: Dict[str, Any],
    iva_incluido: bool,
    lista_nombre: str,
    encabezado: Dict[str, Any],
    total: int,
) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A3, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

    page_size = landscape(A3)
    ancho_util = page_size[0] - 24 * mm
    precio_label = "Precio final" if iva_incluido else "Precio neto"

    estilo_celda = ParagraphStyle("celda", fontName="Helvetica", fontSize=7, leading=8)
    estilo_head = ParagraphStyle("head", fontName="Helvetica-Bold", fontSize=7, leading=8, textColor=colors.white)

    encabezados = ["Rubro", "Sub Rubro", "Cód", "Artículo", precio_label, "Promo"]
    tabla_data: List[List[Any]] = [[Paragraph(h, estilo_head) for h in encabezados]]
    for r in data_rows:
        tabla_data.append([
            Paragraph(_esc(r[0]), estilo_celda),
            Paragraph(_esc(r[1]), estilo_celda),
            Paragraph(_esc(r[2]), estilo_celda),
            Paragraph(_esc(r[3]), estilo_celda),
            Paragraph(r[4], ParagraphStyle("precio", parent=estilo_celda, alignment=2)),
            Paragraph(r[5], ParagraphStyle("promo", parent=estilo_celda, alignment=1)),
        ])

    pesos = [0.15, 0.15, 0.10, 0.40, 0.12, 0.08]
    col_widths = [ancho_util * p for p in pesos]

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=page_size,
        leftMargin=12 * mm, rightMargin=12 * mm, topMargin=40 * mm, bottomMargin=16 * mm,
        title="Lista de Precios",
    )

    tabla = Table(tabla_data, colWidths=col_widths, repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a2a3a")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))

    ctx = {
        "empresa": empresa,
        "lista_nombre": lista_nombre,
        "encabezado": encabezado,
        "total": total,
    }
    doc.build([tabla], onFirstPage=lambda c, d: _dibujar_marco(c, d, ctx),
              onLaterPages=lambda c, d: _dibujar_marco(c, d, ctx))
    return buf.getvalue()


def _dibujar_marco(canvas: Any, doc: Any, ctx: Dict[str, Any]) -> None:
    from datetime import datetime

    from reportlab.lib import colors
    from reportlab.lib.units import mm

    w, h = doc.pagesize
    margin = 12 * mm
    empresa = ctx["empresa"]

    logo_path = empresa.get("logo_path")
    text_x = margin
    if logo_path:
        try:
            from reportlab.lib.utils import ImageReader

            img = ImageReader(logo_path)
            iw, ih = img.getSize()
            lh = 16 * mm
            lw = (iw / ih) * lh if ih else lh
            canvas.drawImage(logo_path, margin, h - 10 * mm - lh, width=lw, height=lh, mask="auto")
            text_x = margin + lw + 4 * mm
        except Exception:
            text_x = margin

    canvas.setFillColorRGB(0, 0, 0)
    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawString(text_x, h - 15 * mm, (empresa.get("razon_social") or "-")[:80])
    canvas.setFont("Helvetica", 8)
    canvas.setFillColorRGB(0.28, 0.33, 0.4)
    canvas.drawString(text_x, h - 20 * mm, f"CUIT {empresa.get('cuit_formateado') or '-'}")

    canvas.setFont("Helvetica-Bold", 12)
    canvas.setFillColorRGB(0.1, 0.16, 0.23)
    canvas.drawRightString(w - margin, h - 15 * mm, f"Lista de Precios · {ctx['lista_nombre']}")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColorRGB(0.28, 0.33, 0.4)
    canvas.drawRightString(w - margin, h - 20 * mm, f"Emisión: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    enc = ctx.get("encabezado") or {}
    filtros_txt = str(enc.get("filtros_texto") or "TODOS LOS PRODUCTOS")
    cliente_txt = str(enc.get("cliente_texto") or "GENERAL / CONSUMIDOR FINAL")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColorRGB(0.2, 0.25, 0.33)
    canvas.drawString(margin, h - 27 * mm, f"FILTROS: {filtros_txt[:90]}   ·   CLIENTE: {cliente_txt[:50]}   ·   ÍTEMS: {ctx.get('total', 0)}")

    canvas.setStrokeColorRGB(0.85, 0.85, 0.85)
    canvas.setLineWidth(0.5)
    canvas.line(margin, h - 30 * mm, w - margin, h - 30 * mm)

    canvas.setFont("Helvetica", 7)
    canvas.setFillColorRGB(0.4, 0.4, 0.4)
    canvas.drawString(margin, 10 * mm, "Lista exclusiva para clientes mayoristas · Generada por Synap")
    canvas.drawRightString(w - margin, 10 * mm, f"Página {canvas.getPageNumber()}")


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
