"""PDF de cuenta corriente y comprobantes a cobrar de la cartera activa."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle

from core.report_pdf import get_empresa_para_reporte
from ecom.services.pdf_branding import MUTED, NAVY, PALE, RULE, cell, draw_page


def _number(value):
    try:
        return Decimal(str(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(0)


def _money(value):
    amount = _number(value)
    sign = "-" if amount < 0 else ""
    integer, fraction = f"{abs(amount):,.2f}".split(".")
    return f"{sign}$ {integer.replace(',', '.')},{fraction}"


def _table(data, widths, *, header=True):
    table = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, RULE),
    ]
    if header:
        style.extend([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
        ])
    table.setStyle(TableStyle(style))
    return table


def generar_reporte_cartera_pdf(*, base_empresa, tipo, cliente_nombre, cliente_codigo, filas, saldo_al_dia=None, filtros=None):
    """Recibe filas de los mismos relays usados en pantalla y genera un PDF A4 horizontal."""
    if tipo not in ("cuenta-corriente", "no-cancelados"):
        raise ValueError("Tipo de reporte desconocido")
    empresa = get_empresa_para_reporte(base_empresa)
    title = "Cuenta corriente" if tipo == "cuenta-corriente" else "Comprobantes a cobrar"
    if tipo == "cuenta-corriente":
        spec = [
            ("Fecha", "FechaB", 20), ("Comprobante", "NroComprobante", 43),
            ("Tipo", "TipoComprobante", 14), ("Condición", "CondVenta", 27),
            ("Debe", "Debito", 31), ("Haber", "Credito", 31),
            ("Saldo", "saldo", 31), ("Detalle", "Detalle", 56),
        ]
    else:
        spec = [
            ("Fecha", "FechaB", 20), ("Tipo", "TipoComprobante", 13),
            ("Comprobante", "NroComprobante", 39), ("Condición", "CondVenta", 26),
            ("Vencimiento", "FechaVto", 24), ("Días", "DiasVto", 13),
            ("Importe", "Importe", 29), ("Cancelado", "Cancelado", 29),
            ("Saldo", "SaldoSigned", 29), ("Acumulado", "SaldoAcum", 31),
        ]
    money_fields = {"Debito", "Credito", "saldo", "Importe", "Cancelado", "SaldoSigned", "SaldoAcum"}
    widths = [width * mm for _, _, width in spec]
    data = [[cell(label, bold=True, size=7, color=colors.white) for label, _, _ in spec]]
    for row in filas:
        data.append([
            cell(_money(row.get(key)) if key in money_fields else (row.get(key) or ""),
                 align=2 if key in money_fields else 0, size=7)
            for _, key, _ in spec
        ])
    if not filas:
        data.append([cell("Sin movimientos para los filtros seleccionados.", color=MUTED)] + [""] * (len(spec) - 1))

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm,
        topMargin=43 * mm, bottomMargin=24 * mm, title=title,
    )
    width = doc.width
    fd, fh = (filtros or {}).get("fechaDesde"), (filtros or {}).get("fechaHasta")
    periodo = f"Período: {fd or 'inicio'} a {fh or 'hoy'}"
    context = _table([
        [cell("CLIENTE", bold=True, size=7, color=MUTED), cell("CÓDIGO", bold=True, size=7, color=MUTED), cell("PERÍODO", bold=True, size=7, color=MUTED)],
        [cell(cliente_nombre, bold=True, size=10), cell(cliente_codigo), cell(periodo)],
    ], [width * .48, width * .16, width * .36], header=False)
    context.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PALE)]))
    content = [context, Spacer(1, 5 * mm), _table(data, widths)]
    if tipo == "cuenta-corriente":
        saldo = filas[0].get("saldo") if filas else 0  # Relay ordena fecha descendente.
        total_debe = sum((_number(row.get("Debito")) for row in filas), Decimal(0))
        total_haber = sum((_number(row.get("Credito")) for row in filas), Decimal(0))
        summary = [
            ("Total deudor", _money(total_debe)),
            ("Total acreedor", _money(total_haber)),
            ("Saldo final", _money(saldo)),
        ]
    else:
        summary = [("Saldo a cobrar", _money(saldo_al_dia))]
    summary_rows = [[cell(label, bold=True), cell(value, bold=True, align=2)] for label, value in summary]
    totals = _table(summary_rows, [45 * mm, 40 * mm], header=False)
    totals.setStyle(TableStyle([("BACKGROUND", (0, -1), (-1, -1), PALE)]))
    content.extend([Spacer(1, 5 * mm), totals])
    if tipo == "no-cancelados":
        content.extend([Spacer(1, 2 * mm), cell("Las notas de crédito y los recibos a cuenta sin imputar se muestran con saldo negativo.", size=7, color=MUTED)])
    doc.build(content, onFirstPage=lambda c, d: draw_page(c, d, empresa=empresa, title=title, subtitle="Cliente · administraNET"),
              onLaterPages=lambda c, d: draw_page(c, d, empresa=empresa, title=title, subtitle="Continuación"))
    return buffer.getvalue()
