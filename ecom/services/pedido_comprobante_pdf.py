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
    from datetime import datetime

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    empresa = get_empresa_para_reporte(base_empresa)
    page_size = A4
    ancho_util = page_size[0] - 24 * mm
    margin = 12 * mm

    estilo = ParagraphStyle("celda", fontName="Helvetica", fontSize=8, leading=10)
    estilo_head = ParagraphStyle("head", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.white)
    estilo_tot = ParagraphStyle("tot", fontName="Helvetica-Bold", fontSize=9, leading=11)

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
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))

    totales_txt = (
        f"Neto: {_fmt_money(cab.get('subtotal_desc'))} · "
        f"IVA: {_fmt_money((cab.get('iva_1') or 0) + (cab.get('iva_2') or 0))} · "
        f"Total: {_fmt_money(cab.get('total'))}"
    )
    pie = Paragraph(totales_txt, estilo_tot)

    buf = io.BytesIO()
    ctx = {"empresa": empresa, "cab": cab}
    doc = SimpleDocTemplate(
        buf,
        pagesize=page_size,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=40 * mm,
        bottomMargin=16 * mm,
        title=f"Pedido {cab.get('nro_comprobante') or ''}",
    )

    def _marco(canvas, doc_obj):
        w, h = doc_obj.pagesize
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawString(margin, h - 15 * mm, (empresa.get("razon_social") or "-")[:70])
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawRightString(w - margin, h - 15 * mm, f"Pedido {cab.get('nro_comprobante') or ''}")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColorRGB(0.3, 0.35, 0.4)
        canvas.drawString(
            margin,
            h - 21 * mm,
            f"Cliente: {cab.get('nombre_cliente') or '-'} · Fecha: {cab.get('fecha') or '-'} · Estado: {cab.get('estado') or '-'}",
        )
        canvas.drawString(
            margin,
            h - 26 * mm,
            f"Vendedor: {cab.get('nombre_viajante') or '-'} · Entrega: {cab.get('fecha_entrega') or '-'}",
        )
        canvas.setStrokeColorRGB(0.85, 0.85, 0.85)
        canvas.line(margin, h - 30 * mm, w - margin, h - 30 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColorRGB(0.45, 0.45, 0.45)
        canvas.drawString(margin, 10 * mm, f"Synap · Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        canvas.drawRightString(w - margin, 10 * mm, f"Página {canvas.getPageNumber()}")

    doc.build([tabla, Spacer(1, 8), pie], onFirstPage=_marco, onLaterPages=_marco)
    return buf.getvalue()
