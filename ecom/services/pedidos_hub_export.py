"""Filtros y exportación del listado de pedidos visible para la sesión actual."""

from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
import os
from typing import Any

from django.conf import settings
from core.report_pdf import get_empresa_para_reporte

ESTADOS = {
    "borrador": "Borrador", "enviado": "Pendiente", "por_autorizar": "Por autorizar",
    "credito_finanzas": "Pendiente crédito", "aprobado": "Aprobado",
    "en_curso": "En preparación", "cerrado": "Entregado / Cerrado", "anulado": "Anulado",
}


def _dinero(valor: float) -> str:
    return "$ " + f"{float(valor):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def filtrar_pedidos_hub(
    items: list[dict[str, Any]], *, busqueda: str = "", fecha_desde: str = "",
    fecha_hasta: str = "", columna: str = "",
) -> list[dict[str, Any]]:
    desde = date.fromisoformat(fecha_desde) if fecha_desde else None
    hasta = date.fromisoformat(fecha_hasta) if fecha_hasta else None
    if desde and hasta and desde > hasta:
        raise ValueError("La fecha inicial es posterior a la final.")
    q = busqueda.strip().casefold()
    visibles = []
    for item in items:
        if columna and item.get("columna") != columna:
            continue
        if desde or hasta:
            try:
                fecha = datetime.strptime(str(item.get("fecha") or ""), "%d/%m/%Y").date()
            except ValueError:
                continue
            if (desde and fecha < desde) or (hasta and fecha > hasta):
                continue
        meta = item.get("meta") or {}
        texto = " ".join(str(v or "") for v in (
            item.get("titulo"), item.get("subtitulo"), item.get("cliente"),
            item.get("sucursal"), item.get("sucursal_nro"), item.get("vendedor"),
            item.get("total_fmt"), item.get("fecha"), item.get("id_ref"),
            meta.get("nombre_cliente"), meta.get("codigo_movimiento"),
            meta.get("estado"), meta.get("vendedor"),
        ))
        if q and q not in texto.casefold():
            continue
        visibles.append(item)
    return visibles


def _pedidos_con_importe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in items if item.get("columna") != "anulado"
            and item.get("tipo") in ("ped", "lote_masivo")]


def _suma(items: list[dict[str, Any]], campo: str) -> float:
    return round(sum(float(item.get(campo) or 0) for item in _pedidos_con_importe(items)), 2)


def _texto_excel(valor: Any) -> str:
    texto = str(valor or "")
    return "'" + texto if texto.startswith(("=", "+", "-", "@")) else texto


def _domicilio_adicional(item: dict[str, Any]) -> str:
    if item.get("tipo") == "lote_masivo":
        return "Varios domicilios"
    return str((item.get("meta") or {}).get("sucursal") or item.get("sucursal") or "")


def generar_excel_pedidos(items: list[dict[str, Any]], base_empresa: str) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    empresa = get_empresa_para_reporte(base_empresa)
    wb = Workbook()
    ws = wb.active
    ws.title = "Pedidos"
    ws.merge_cells("A1:H1")
    ws["A1"] = "PEDIDOS · " + str(empresa.get("razon_social") or "")
    ws["A1"].font = Font(size=16, bold=True, color="123B70")
    ws.merge_cells("A2:H2")
    ws["A2"] = "administraNET · Generado el " + datetime.now().strftime("%d/%m/%Y %H:%M")
    headers = ("Fecha", "Pedido", "Cliente", "Domicilio adicional", "Estado", "Vendedor", "Neto", "Final")
    for col, value in enumerate(headers, 1):
        c = ws.cell(4, col, value)
        c.fill = PatternFill("solid", fgColor="123B70")
        c.font = Font(color="FFFFFF", bold=True)
        c.alignment = Alignment(vertical="center")
    for row, item in enumerate(items, 5):
        vals = (
            item.get("fecha"), item.get("titulo"), item.get("cliente"),
            _domicilio_adicional(item), ESTADOS.get(item.get("columna"), item.get("columna")), item.get("vendedor"),
            float(item.get("neto") or 0), float(item.get("total") or 0),
        )
        for col, value in enumerate(vals, 1):
            ws.cell(row, col, _texto_excel(value) if col <= 6 else value)
        for col in (7, 8):
            ws.cell(row, col).number_format = '"$" #,##0.00'
    total_row = len(items) + 6
    ws.cell(total_row, 6, "TOTAL VIGENTE").font = Font(bold=True, color="123B70")
    for col, key in ((7, "neto"), (8, "total")):
        cell = ws.cell(total_row, col, _suma(items, key))
        cell.font = Font(bold=True, color="123B70")
        cell.number_format = '"$" #,##0.00'
    for col, width in {"A": 15, "B": 34, "C": 35, "D": 31, "E": 20, "F": 25, "G": 18, "H": 18}.items():
        ws.column_dimensions[col].width = width
    ws.freeze_panes = "A5"
    ws.auto_filter.ref = f"A4:H{max(4, len(items)+4)}"
    output = BytesIO()
    wb.save(output)
    return output.getvalue()


def generar_pdf_pedidos(items: list[dict[str, Any]], base_empresa: str) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from xml.sax.saxutils import escape

    empresa = get_empresa_para_reporte(base_empresa)
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(A4), leftMargin=30, rightMargin=30,
                            topMargin=87, bottomMargin=40)
    styles = getSampleStyleSheet()
    tiny = ParagraphStyle("PedidoCelda", parent=styles["Normal"], fontName="Helvetica", fontSize=8, leading=10)
    data = [["Fecha", "Pedido", "Cliente", "Domicilio adicional", "Estado", "Vendedor", "Neto", "Final"]]
    for item in items:
        texts = (item.get("fecha"), item.get("titulo"), item.get("cliente"),
                 _domicilio_adicional(item), ESTADOS.get(item.get("columna"), item.get("columna")), item.get("vendedor"))
        data.append([Paragraph(escape(str(value or "")), tiny) for value in texts] + [
            _dinero(item.get("neto") or 0), _dinero(item.get("total") or 0),
        ])
    data.append(["", "", "", "", "", "TOTAL VIGENTE",
                 _dinero(_suma(items, "neto")), _dinero(_suma(items, "total"))])
    widths = [58, 103, 125, 125, 65, 105, 100, 100]
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#08336D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), .25, colors.HexColor("#CCD5E0")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E5F1FA")),
        ("FONTNAME", (5, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (6, 1), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))

    def decorar(canvas, document):
        canvas.saveState()
        page_w, page_h = landscape(A4)
        logo = empresa.get("logo_path")
        if not logo and "best sox" in str(empresa.get("razon_social") or "").lower():
            logo = os.path.join(settings.BASE_DIR, "ecom", "static", "ecom", "img", "best_sox_logo.jpg")
        if logo and os.path.isfile(logo):
            try:
                image = ImageReader(logo)
                iw, ih = image.getSize()
                w = min(105, 45 * iw / ih)
                h = w * ih / iw
                canvas.drawImage(image, 31, page_h - 22 - h, width=w,
                                 height=h, preserveAspectRatio=True, mask="auto")
            except Exception:
                pass
        canvas.setFillColor(colors.HexColor("#08336D"))
        canvas.setFont("Helvetica-Bold", 17)
        canvas.drawString(160, page_h - 37, "Listado de pedidos")
        canvas.setFont("Helvetica", 10)
        canvas.drawString(160, page_h - 53, str(empresa.get("razon_social") or ""))
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawRightString(page_w - 30, page_h - 37, "administraNET")
        canvas.setStrokeColor(colors.HexColor("#1560A8"))
        canvas.line(30, page_h - 75, page_w - 30, page_h - 75)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#526375"))
        canvas.drawString(30, 22, datetime.now().strftime("Generado el %d/%m/%Y %H:%M"))
        analytics = os.path.join(settings.BASE_DIR, "ecom", "static", "ecom", "img", "nl_analytics.png")
        if os.path.isfile(analytics):
            try:
                image = ImageReader(analytics)
                iw, ih = image.getSize()
                w = min(33, 22 * iw / ih)
                canvas.drawImage(image, (page_w - w) / 2, 12, width=w, height=w * ih / iw,
                                 preserveAspectRatio=True, mask="auto")
            except Exception:
                pass
        canvas.drawRightString(page_w - 30, 22, f"Página {document.page}")
        canvas.restoreState()

    doc.build([table, Spacer(1, 1)], onFirstPage=decorar, onLaterPages=decorar)
    return output.getvalue()
