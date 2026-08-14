"""Exportación CSV/Excel para reportes MPR."""
import csv
import io
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from django.http import HttpResponse

from core.utils.administranet_types import to_decimal_or_none


def filas_a_csv(
    filas: Iterable[Dict[str, Any]],
    columnas: Sequence[Tuple[str, str]],
) -> bytes:
    """
    Genera CSV UTF-8 con BOM.

    columnas: secuencia de (clave_dict, encabezado_español).
    """
    buf = io.StringIO()
    buf.write("\ufeff")
    writer = csv.writer(buf, lineterminator="\r\n")
    writer.writerow([titulo for _, titulo in columnas])
    for fila in filas or []:
        writer.writerow([_celda_csv(fila.get(clave)) for clave, _ in columnas])
    return buf.getvalue().encode("utf-8")


def _celda_csv(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, bool):
        return "Sí" if val else "No"
    return str(val)


def _fmt_fecha_export(val: Any) -> str:
    if isinstance(val, datetime):
        val = val.date()
    if isinstance(val, date):
        return val.strftime("%d/%m/%Y")
    return str(val or "")


def _num_xlsx(val: Any) -> Any:
    dec = to_decimal_or_none(val)
    if dec is None:
        return ""
    if dec == dec.to_integral_value():
        return int(dec)
    return float(dec)


def exportar_inventario_deposito_xlsx(
    filas: Iterable[Dict[str, Any]],
    *,
    total_docenas: float,
    fecha_corte: Optional[date] = None,
    titulo: str = "Inventario por depósito",
) -> HttpResponse:
    """Export Excel inventario_deposito: Depósito, Marca, Artículo, Talle, Stock, Docenas + TOTAL."""
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inventario"

    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )
    center = Alignment(horizontal="center", vertical="center")
    left = Alignment(horizontal="left", vertical="center")

    headers = ["Depósito", "Marca", "Artículo", "Talle", "Stock", "Docenas"]
    row = 1
    if fecha_corte:
        ws.cell(row=row, column=1, value=f"{titulo} · Corte {_fmt_fecha_export(fecha_corte)}")
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=len(headers))
        ws.cell(row=row, column=1).font = Font(bold=True, size=12, color="1E40AF")
        row += 1

    for col_num, label in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col_num, value=label)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center
        cell.border = border
    row += 1

    for fila in filas or []:
        codigo = fila.get("codigo_manual") or fila.get("codigo_articulo") or "-"
        desc = (fila.get("descripcion_articulo") or "").strip()
        articulo = f"{codigo} — {desc}" if desc else str(codigo)
        valores = [
            fila.get("nombre_deposito") or "",
            fila.get("marca_nombre") or "",
            articulo,
            fila.get("talle") or "",
            _num_xlsx(fila.get("stock_um")),
            _num_xlsx(fila.get("docenas")),
        ]
        for col_num, valor in enumerate(valores, 1):
            cell = ws.cell(row=row, column=col_num, value="" if valor is None else valor)
            cell.border = border
            cell.alignment = left if col_num <= 4 else center
        row += 1

    total_font = Font(bold=True)
    ws.cell(row=row, column=1, value="TOTAL").font = total_font
    ws.cell(row=row, column=5, value="").font = total_font
    total_cell = ws.cell(row=row, column=6, value=_num_xlsx(total_docenas))
    total_cell.font = total_font
    for col_num in range(1, len(headers) + 1):
        ws.cell(row=row, column=col_num).border = border

    from openpyxl.utils import get_column_letter

    for col_num in range(1, len(headers) + 1):
        col_letter = get_column_letter(col_num)
        max_len = len(str(headers[col_num - 1]))
        for cell in ws[col_letter]:
            if cell.value is not None:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = min(max_len + 2, 60)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    sufijo = _fmt_fecha_export(fecha_corte).replace("/", "") if fecha_corte else "hoy"
    nombre = f"inventario_deposito_{sufijo}.xlsx"
    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{nombre}"'
    return response
