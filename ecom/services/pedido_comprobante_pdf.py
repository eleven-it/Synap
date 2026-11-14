"""
PDF de comprobante PED para consulta / impresión desde Synap.
"""

from __future__ import annotations

import io
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from core.report_pdf import get_empresa_para_reporte
from core.utils.administranet_types import to_decimal_or_none
from ecom.services.comprobantes_relay import detalle_pedido_relay
from ecom.services.pedido_cabecera_relay import cabecera_pedido_relay
from ecom.services.pdf_branding import INK, MUTED, NAVY, PALE, RULE, cell, draw_page


def _fmt_money(v: Any) -> str:
    q = (to_decimal_or_none(v) or Decimal("0")).quantize(Decimal("0.01"))
    entero, dec = f"{abs(q):.2f}".split(".")
    grupos = []
    while len(entero) > 3:
        grupos.insert(0, entero[-3:])
        entero = entero[:-3]
    grupos.insert(0, entero)
    signo = "-" if q < 0 else ""
    return f"{signo}${'.'.join(grupos)},{dec}"


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def generar_pedido_pdf(
    base_empresa: str,
    cod_mov: int,
    *,
    usa_id_manual: bool = False,
) -> Tuple[bool, Optional[str], Optional[bytes]]:
    """Genera PDF del pedido. Devuelve (ok, error, bytes)."""
    cab = cabecera_pedido_relay(base_empresa, cod_mov)
    if not cab:
        return False, "Pedido no encontrado.", None
    renglones = detalle_pedido_relay(base_empresa, cod_mov, usa_id_manual=usa_id_manual)
    try:
        pdf = _render_pdf(cab, renglones, base_empresa=base_empresa)
    except Exception as exc:  # pragma: no cover
        return False, f"No se pudo generar el PDF: {exc}", None
    return True, None, pdf


def _render_pdf(cab: Dict[str, Any], renglones: List[Dict[str, Any]], *, base_empresa: str) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    empresa = get_empresa_para_reporte(base_empresa)
    page_size = A4
    ancho_util = page_size[0] - 24 * mm
    margin = 12 * mm

    estilo = ParagraphStyle("celda", fontName="Helvetica", fontSize=8, leading=10, textColor=INK)
    estilo_head = ParagraphStyle("head", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.white)

    headers = ["Cód.", "Descripción", "Cant.", "P. neto", "Total"]
    data: List[List[Any]] = [[Paragraph(h, estilo_head) for h in headers]]
    for r in renglones:
        cod = r.get("CodigoArticulo") or r.get("IDArt")
        neto_u = to_decimal_or_none(r.get("PrecioNetoxU")) or Decimal("0")
        cant = to_decimal_or_none(r.get("Salida")) or Decimal("0")
        total_r = to_decimal_or_none(r.get("PrecioNetoxR")) or (neto_u * cant)
        data.append([
            Paragraph(_esc(str(cod or "")), estilo),
            Paragraph(_esc(str(r.get("Descripcion") or "")), estilo),
            Paragraph(str(cant), ParagraphStyle("c", parent=estilo, alignment=2)),
            Paragraph(_fmt_money(neto_u), ParagraphStyle("p", parent=estilo, alignment=2)),
            Paragraph(_fmt_money(total_r), ParagraphStyle("t", parent=estilo, alignment=2)),
        ])

    col_widths = [ancho_util * p for p in (0.10, 0.46, 0.10, 0.17, 0.17)]
    tabla = Table(data, colWidths=col_widths, repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, RULE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
    ]))

    iva = (to_decimal_or_none(cab.get("iva_1")) or Decimal(0)) + (to_decimal_or_none(cab.get("iva_2")) or Decimal(0))
    summary = Table([
        [cell("Subtotal neto", bold=True), cell(_fmt_money(cab.get("subtotal_desc")), align=2)],
        [cell("IVA", bold=True), cell(_fmt_money(iva), align=2)],
        [cell("Total del pedido", bold=True, color=colors.white), cell(_fmt_money(cab.get("total")), bold=True, align=2, color=colors.white)],
    ], colWidths=[42 * mm, 35 * mm], hAlign="RIGHT")
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 1), PALE),
        ("BACKGROUND", (0, 2), (-1, 2), NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    details = Table([
        [cell("CLIENTE", bold=True, size=7, color=MUTED), cell("FECHA", bold=True, size=7, color=MUTED), cell("ESTADO", bold=True, size=7, color=MUTED)],
        [cell(cab.get("nombre_cliente") or "-", bold=True, size=10), cell(cab.get("fecha") or "-"), cell(cab.get("estado") or "-")],
        [cell(f"Vendedor: {cab.get('nombre_viajante') or '-'}"), cell(f"Entrega: {cab.get('fecha_entrega') or '-'}"), cell(f"Condición: {cab.get('cond_venta') or '-'}")],
    ], colWidths=[ancho_util * .48, ancho_util * .26, ancho_util * .26])
    details.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=page_size,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=43 * mm,
        bottomMargin=24 * mm,
        title=f"Pedido {cab.get('nro_comprobante') or ''}",
    )

    contents = [details, Spacer(1, 5 * mm), tabla, Spacer(1, 5 * mm), summary]
    if cab.get("observaciones"):
        contents.extend([Spacer(1, 5 * mm), cell("Detalle del comprobante", bold=True),
                         cell(cab["observaciones"])])
    title = f"Pedido {cab.get('nro_comprobante') or ''}"
    doc.build(contents,
              onFirstPage=lambda c, d: draw_page(c, d, empresa=empresa, title=title, subtitle="Comprobante de pedido"),
              onLaterPages=lambda c, d: draw_page(c, d, empresa=empresa, title=title, subtitle="Continuación"))
    return buf.getvalue()
