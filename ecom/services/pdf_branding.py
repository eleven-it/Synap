"""Identidad visual compartida de los PDF comerciales de administraNET."""

from __future__ import annotations

import os
from datetime import datetime
from xml.sax.saxutils import escape

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph


NAVY = colors.HexColor("#12386b")
INK = colors.HexColor("#273b54")
MUTED = colors.HexColor("#63758a")
PALE = colors.HexColor("#edf3f9")
RULE = colors.HexColor("#d8e2ed")


def cell(value, *, bold=False, align=0, size=8, color=INK):
    style = ParagraphStyle(
        "pdf-cell", fontName="Helvetica-Bold" if bold else "Helvetica",
        fontSize=size, leading=size + 3, alignment=align, textColor=color,
    )
    return Paragraph(escape(str(value if value is not None else "")), style)


def _logo(canvas, path, x, y, max_width, max_height):
    if not path or not os.path.isfile(path):
        return 0
    try:
        width, height = ImageReader(path).getSize()
        scale = min(max_width / width, max_height / height)
        width, height = width * scale, height * scale
        canvas.drawImage(path, x, y - height, width, height, mask="auto")
        return width
    except Exception:
        return 0


def draw_page(canvas, doc, *, empresa, title, subtitle=""):
    """Dibuja encabezado y pie, también en páginas continuadas."""
    page_w, page_h = doc.pagesize
    left, right = doc.leftMargin, page_w - doc.rightMargin
    top = page_h - 13 * mm
    canvas.setFillColor(NAVY)
    canvas.rect(0, page_h - 4 * mm, page_w, 4 * mm, stroke=0, fill=1)

    logo_width = _logo(canvas, empresa.get("logo_path"), left, top, 36 * mm, 17 * mm)
    company_x = left + (logo_width + 5 * mm if logo_width else 0)
    canvas.setFillColor(NAVY)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(company_x, top - 5 * mm, str(empresa.get("razon_social") or "Empresa")[:45])
    canvas.setFont("Helvetica", 7.3)
    canvas.setFillColor(MUTED)
    canvas.drawString(company_x, top - 10 * mm, str(empresa.get("domicilio") or "")[:65])
    canvas.drawString(company_x, top - 14 * mm, f"CUIT: {empresa.get('cuit_formateado') or '-'}")

    canvas.setFillColor(NAVY)
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawRightString(right, top - 6 * mm, title)
    if subtitle:
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(right, top - 11 * mm, subtitle[:55])
    canvas.setStrokeColor(RULE)
    canvas.line(left, top - 20 * mm, right, top - 20 * mm)

    canvas.line(left, 17 * mm, right, 17 * mm)
    brand_path = os.path.join(settings.BASE_DIR, "theme", "static", "img", "brand", "logo_signo_administranet.png")
    icon_w = _logo(canvas, brand_path, page_w / 2 - 22 * mm, 14 * mm, 6 * mm, 6 * mm)
    canvas.setFillColor(INK)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(page_w / 2 - 22 * mm + icon_w + 2 * mm, 9 * mm, "administraNET")
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(left, 10 * mm, datetime.now().strftime("Generado: %d/%m/%Y %H:%M"))
    canvas.drawRightString(right, 10 * mm, f"Página {doc.page}")
