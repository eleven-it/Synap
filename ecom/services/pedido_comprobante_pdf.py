"""
PDF de comprobante PED para consulta / impresión desde Synap.
"""

from __future__ import annotations

import io
import os
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from core.report_pdf import get_empresa_para_reporte
from django.conf import settings
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
    domicilio = None
    if cab.get("id_cliente_domicilio"):
        from ecom.services.cliente_domicilio_relay import trae_domicilio_completo
        try:
            domicilio, _ = trae_domicilio_completo(base_empresa, int(cab["id_cliente_domicilio"]))
        except Exception:
            domicilio = None
    try:
        pdf = _render_pdf(cab, renglones, base_empresa=base_empresa, domicilio=domicilio)
    except Exception as exc:  # pragma: no cover
        return False, f"No se pudo generar el PDF: {exc}", None
    return True, None, pdf


def _render_pdf(cab: Dict[str, Any], renglones: List[Dict[str, Any]], *, base_empresa: str,
                domicilio: Optional[Dict[str, Any]] = None) -> bytes:
    from datetime import datetime

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    empresa = get_empresa_para_reporte(base_empresa)
    page_size = A4
    ancho_util = page_size[0] - 20 * mm
    margin = 10 * mm
    azul = colors.HexColor("#08336D")

    estilo = ParagraphStyle("celda", fontName="Helvetica", fontSize=8, leading=10)
    estilo_head = ParagraphStyle("head", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.white)
    estilo_tot = ParagraphStyle("tot", fontName="Helvetica-Bold", fontSize=9, leading=11)

    headers = ["Cód.", "Descripción", "Cant.", "IVA %", "Neto x U", "Precio total"]
    data: List[List[Any]] = [[Paragraph(h, estilo_head) for h in headers]]
    for r in renglones:
        cod = r.get("CodigoArticulo") or r.get("IDArt")
        neto_u = to_decimal_or_none(r.get("PrecioNetoxU")) or Decimal("0")
        cant = to_decimal_or_none(r.get("Salida")) or Decimal("0")
        neto_r = to_decimal_or_none(r.get("PrecioNetoxR")) or (neto_u * cant)
        total_r = neto_r + (to_decimal_or_none(r.get("PrecioIVAxR")) or Decimal("0"))
        iva = to_decimal_or_none(r.get("TipoIVA"))
        data.append([
            Paragraph(_esc(str(cod or "")), estilo),
            Paragraph(_esc(str(r.get("Descripcion") or "")), estilo),
            Paragraph(str(cant), ParagraphStyle("c", parent=estilo, alignment=2)),
            Paragraph(str(iva if iva is not None else ""), ParagraphStyle("iva", parent=estilo, alignment=2)),
            Paragraph(_fmt_money(neto_u), ParagraphStyle("p", parent=estilo, alignment=2)),
            Paragraph(_fmt_money(total_r), ParagraphStyle("t", parent=estilo, alignment=2)),
        ])

    col_widths = [ancho_util * p for p in (0.10, 0.43, 0.09, 0.07, 0.14, 0.17)]
    tabla = Table(data, colWidths=col_widths, repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), azul),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))

    iva_total = (to_decimal_or_none(cab.get("iva_1")) or Decimal("0")) + (to_decimal_or_none(cab.get("iva_2")) or Decimal("0"))
    resumen = Table([
        ["Neto", "Exento", "IVA", "Imp. internos", "Percepciones", "Total"],
        [_fmt_money(cab.get("subtotal_desc")), _fmt_money(cab.get("exento")), _fmt_money(iva_total),
         _fmt_money(cab.get("impuesto_interno_total")), _fmt_money(cab.get("total_percep")), _fmt_money(cab.get("total"))],
    ], colWidths=[ancho_util / 6] * 6)
    resumen.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6eef8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), azul),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
    ]))

    buf = io.BytesIO()
    ctx = {"empresa": empresa, "cab": cab}
    doc = SimpleDocTemplate(
        buf,
        pagesize=page_size,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=70 * mm,
        bottomMargin=22 * mm,
        title=f"Pedido {cab.get('nro_comprobante') or ''}",
    )

    def _marco(canvas, doc_obj):
        w, h = doc_obj.pagesize
        canvas.saveState()
        logo = empresa.get("logo_path")
        if not logo and "best sox" in str(empresa.get("razon_social") or "").lower():
            logo = os.path.join(settings.BASE_DIR, "ecom", "static", "ecom", "img", "best_sox_logo.jpg")
        if logo and os.path.isfile(logo):
            image = ImageReader(logo)
            iw, ih = image.getSize()
            lw = min(43 * mm, 25 * mm * iw / ih)
            canvas.drawImage(image, margin, h - 8 * mm - lw * ih / iw, width=lw, height=lw * ih / iw,
                             preserveAspectRatio=True, mask="auto")
        canvas.setFillColor(azul)
        canvas.setFont("Helvetica-Bold", 14)
        canvas.drawRightString(w - margin, h - 14 * mm, "PEDIDO")
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawRightString(w - margin, h - 20 * mm, "Nro: " + str(cab.get("nro_comprobante") or ""))
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(w - margin, h - 25 * mm, "Fecha: " + str(cab.get("fecha") or "-"))
        canvas.drawRightString(w - margin, h - 30 * mm, "Vendedor: " + str(cab.get("nombre_viajante") or "-"))
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(margin, h - 37 * mm, str(empresa.get("razon_social") or "-")[:65])
        canvas.setFont("Helvetica", 8)
        canvas.drawString(margin, h - 42 * mm, str(empresa.get("domicilio") or "-")[:105])
        canvas.drawString(margin, h - 46 * mm, "CUIT: " + str(empresa.get("cuit_formateado") or "-"))
        canvas.setStrokeColor(azul)
        canvas.line(margin, h - 49 * mm, w - margin, h - 49 * mm)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(margin, h - 53 * mm, "DATOS DEL CLIENTE")
        canvas.setFont("Helvetica", 8)
        canvas.drawString(margin, h - 57 * mm, ("Cliente: " + str(cab.get("nombre_cliente") or "-") +
                                            "  ·  CUIT: " + str(cab.get("cuit_cliente") or "-"))[:112])
        calle = " ".join(str((domicilio or {}).get(k) or "") for k in ("Calle", "NroCalle", "Dpto")).strip()
        lugar = " ".join(str((domicilio or {}).get(k) or "") for k in ("NombreDistrito", "Provincia")).strip()
        canvas.drawString(margin, h - 61 * mm, ("Entrega: " + (calle + " " + lugar).strip() +
                                               "  ·  Fecha: " + str(cab.get("fecha_entrega") or "-"))[:112])
        canvas.drawString(margin, h - 65 * mm, ("Cond. venta: " + str(cab.get("cond_venta") or "-") +
                                               "  ·  Forma de entrega: " + str(cab.get("forma_entrega") or "-"))[:112])
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(azul)
        canvas.drawString(margin, 10 * mm, f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        analytics = os.path.join(settings.BASE_DIR, "ecom", "static", "ecom", "img", "nl_analytics.png")
        if os.path.isfile(analytics):
            image = ImageReader(analytics)
            iw, ih = image.getSize()
            aw = min(18 * mm, 10 * mm * iw / ih)
            canvas.drawImage(image, (w - aw) / 2, 7 * mm, width=aw, height=aw * ih / iw,
                             preserveAspectRatio=True, mask="auto")
        canvas.drawRightString(w - margin, 10 * mm, f"Página {canvas.getPageNumber()}")
        canvas.restoreState()

    elementos = [Paragraph("Detalle de comprobante", estilo_tot), Spacer(1, 5), tabla,
                 Spacer(1, 9), resumen, Spacer(1, 9),
                 Paragraph(f"Total de renglones: {len(renglones)}", estilo)]
    if cab.get("observaciones"):
        elementos.extend([Spacer(1, 6), Paragraph("Detalle: " + _esc(str(cab["observaciones"])), estilo)])
    doc.build(elementos, onFirstPage=_marco, onLaterPages=_marco)
    return buf.getvalue()
