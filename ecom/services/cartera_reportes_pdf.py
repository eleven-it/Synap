"""PDF de los dos reportes financieros de la cartera mayorista."""

from __future__ import annotations

from html import escape
from io import BytesIO
from pathlib import Path

from django.contrib.staticfiles import finders
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

from ecom.mayoristapp_listado_config import PORTAL_CLIENTE_LISTADOS


AZUL = colors.HexColor("#08336d")


def _dinero(value):
    try:
        numero = float(value or 0)
    except (ValueError, TypeError):
        numero = 0.0
    return "$ " + f"{numero:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _logo(empresa):
    ruta = empresa.get("logo_path")
    if ruta and Path(ruta).is_file():
        return ruta
    if "best sox" in str(empresa.get("razon_social") or "").lower():
        return finders.find("ecom/img/best_sox_logo.jpg")
    return None


def generar_pdf_cartera(slug, filas, empresa, cliente, filtros, saldo_final):
    """Devuelve bytes PDF; los valores y filtros llegan del relay del cliente autorizado."""
    if slug not in ("no-cancelados", "cuenta-corriente"):
        raise ValueError("Reporte no disponible")
    titulo = ("Comprobantes a cobrar por cliente" if slug == "no-cancelados"
              else "Cuenta corriente por cliente")
    columnas = PORTAL_CLIENTE_LISTADOS[slug]["columns"]
    if slug == "cuenta-corriente":
        filas = list(reversed(filas))
    salida = BytesIO()
    doc = SimpleDocTemplate(salida, pagesize=landscape(A4), leftMargin=30,
                            rightMargin=30, topMargin=74, bottomMargin=42)
    estilo = ParagraphStyle("celda", fontName="Helvetica", fontSize=7, leading=9)
    estilo_titulo = ParagraphStyle("titulo", fontName="Helvetica-Bold", fontSize=15,
                                  leading=18, textColor=AZUL)
    estilo_dato = ParagraphStyle("dato", fontName="Helvetica", fontSize=8,
                                leading=11, textColor=AZUL)
    estilo_cabecera = ParagraphStyle("cabecera", parent=estilo, fontName="Helvetica-Bold",
                                    textColor=colors.white)
    def p(valor, estilo_usado=estilo):
        return Paragraph(escape(str(valor if valor is not None else "")), estilo_usado)

    historia = [p(titulo, estilo_titulo), Spacer(1, 6),
                p(f"Empresa: {empresa.get('razon_social') or '—'} · CUIT: {empresa.get('cuit_formateado') or '—'}", estilo_dato),
                p(f"Período: {filtros.get('fechaDesde') or '—'} a {filtros.get('fechaHasta') or '—'}", estilo_dato),
                Spacer(1, 12),
                p(f"Cliente: {cliente.get('nombre') or '—'} · Código: {cliente.get('codigo') or '—'} · CUIT: {cliente.get('cuit') or '—'}", estilo_dato),
                p(f"Domicilio: {cliente.get('domicilio') or '—'}", estilo_dato), Spacer(1, 12)]
    datos = [[p(col["label"], estilo_cabecera) for col in columnas]]
    for fila in filas:
        datos.append([p(_dinero(fila.get(col["key"])) if col.get("fmt") == "money"
                        else fila.get(col["key"])) for col in columnas])
    if not filas:
        datos.append([p("Sin movimientos para los filtros seleccionados")] + [""] * (len(columnas) - 1))
    anchos = ([55, 38, 87, 69, 61, 47, 78, 78, 77, 81] if slug == "no-cancelados"
              else [56, 39, 75, 62, 62, 62, 35, 68, 39, 62, 62])
    disponible = landscape(A4)[0] - 60
    escala = disponible / sum(anchos)
    tabla = LongTable(datos, colWidths=[x * escala for x in anchos], repeatRows=1,
                      hAlign="LEFT")
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f6fa")]),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, AZUL),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    historia += [tabla, Spacer(1, 12), p(f"Saldo final: {_dinero(saldo_final)}", estilo_dato)]

    logo_empresa = _logo(empresa)
    logo_analytics = finders.find("ecom/img/nl_analytics.png")
    def pagina(canvas, documento):
        ancho, alto = landscape(A4)
        if logo_empresa:
            img = ImageReader(logo_empresa)
            iw, ih = img.getSize()
            h = 40
            canvas.drawImage(img, ancho - 30 - h * iw / ih, alto - 49,
                             width=h * iw / ih, height=h, mask="auto")
        canvas.setStrokeColor(AZUL)
        canvas.line(30, 36, ancho - 30, 36)
        if logo_analytics:
            canvas.drawImage(logo_analytics, ancho / 2 - 16, 9, width=32, height=24,
                             preserveAspectRatio=True, mask="auto")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(AZUL)
        canvas.drawString(30, 18, "administraNET · Synap")
        canvas.drawRightString(ancho - 30, 18, f"Página {documento.page}")
    doc.build(historia, onFirstPage=pagina, onLaterPages=pagina)
    return salida.getvalue()
