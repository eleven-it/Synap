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


def _escribir_seccion_csv(
    writer: csv.writer,
    titulo: str,
    columnas: Sequence[Tuple[str, str]],
    filas: Iterable[Dict[str, Any]],
) -> None:
    writer.writerow([])
    writer.writerow([titulo])
    writer.writerow([titulo_col for _, titulo_col in columnas])
    for fila in filas or []:
        writer.writerow([_celda_csv(fila.get(clave)) for clave, _ in columnas])


def _cantidad_export(fila: Dict[str, Any], clave: str, modo: str) -> Any:
    if modo == "docenas":
        display = fila.get(f"{clave}_display")
        if display is not None and str(display).strip():
            return display
    return fila.get(clave)


def _detalle_movimiento_export(mov: Dict[str, Any]) -> str:
    """Texto de «Qué pasó» que ve el usuario, incluido el aviso si el conteo no cierra."""
    texto = str(mov.get("detalle_ui") or mov.get("detalle") or "").strip()
    aviso = str(mov.get("aviso_conteo") or "").strip()
    if aviso and aviso not in texto:
        return f"{texto} {aviso}".strip() if texto else aviso
    return texto


def analisis_trazabilidad_a_csv(
    analisis: Dict[str, Any],
    *,
    modo: str = "docenas",
    fecha_desde_display: str = "",
    fecha_hasta_display: str = "",
    etapas: Optional[List[Dict[str, Any]]] = None,
) -> bytes:
    """
    CSV multi-sección del análisis trazabilidad artículo (UTF-8 BOM).

    Secciones: resumen, demanda PED, stock/brecha, movimientos, eventos MPR, a producir.
    """
    buf = io.StringIO()
    buf.write("\ufeff")
    writer = csv.writer(buf, lineterminator="\r\n")

    articulo = analisis.get("articulo") or {}
    kpis = analisis.get("kpis") or {}
    demanda = analisis.get("demanda_ped") or {}
    stock = analisis.get("stock") or {}
    brechas = analisis.get("brechas") or {}
    a_producir = analisis.get("a_producir") or {}
    saldo_inicial = analisis.get("saldo_inicial") or {}
    movimientos = analisis.get("movimientos") or []
    eventos = analisis.get("eventos_mpr") or []

    writer.writerow(["Análisis trazabilidad artículo"])
    writer.writerow(["Código", articulo.get("codigo") or "-"])
    writer.writerow(["Descripción", articulo.get("descripcion") or "-"])
    writer.writerow(["ID artículo", articulo.get("id") or ""])
    periodo = ""
    if fecha_desde_display or fecha_hasta_display:
        periodo = f"{fecha_desde_display} — {fecha_hasta_display}".strip(" —")
    writer.writerow(["Período", periodo])
    writer.writerow(["Saldo inicial", saldo_inicial.get("valor", 0)])
    writer.writerow(["Saldo inicial calculado", "Sí" if saldo_inicial.get("calculado_ok") else "No"])

    writer.writerow([])
    writer.writerow(["Resumen KPI"])
    writer.writerow(["Concepto", "Valor"])
    writer.writerow(["Pedido (P_ped)", kpis.get("pedido", 0)])
    writer.writerow(["Terminado", kpis.get("terminado", 0)])
    writer.writerow(["PED Urgente", kpis.get("ped_urgente", 0)])
    writer.writerow(["TOT Urgente", kpis.get("tot_urgente", 0)])
    writer.writerow(["Saldo final", kpis.get("saldo_final", 0)])

    demanda_filas = []
    for ped in demanda.get("filas") or []:
        demanda_filas.append({
            "nro_pedido": ped.get("nro_pedido") or "-",
            "nombre_cliente": ped.get("nombre_cliente") or "-",
            "fecha": ped.get("fecha") or "-",
            "cantidad_pendiente_prod": _cantidad_export(
                ped, "cantidad_pendiente_prod", modo
            ),
        })
    _escribir_seccion_csv(
        writer,
        "DEMANDA PED",
        [
            ("nro_pedido", "Nº pedido"),
            ("nombre_cliente", "Cliente"),
            ("fecha", "Fecha"),
            ("cantidad_pendiente_prod", "Pendiente"),
        ],
        demanda_filas,
    )
    writer.writerow([])
    writer.writerow(["Total P_ped", demanda.get("totales", {}).get("p_ped", 0)])

    writer.writerow([])
    writer.writerow(["STOCK Y BRECHA"])
    writer.writerow(["Concepto", "Valor"])
    writer.writerow(["Terminado", stock.get("terminado", 0)])
    writer.writerow(["Terminado negativo", "Sí" if stock.get("negativo") else "No"])
    writer.writerow(["PED Urgente", brechas.get("ped_urgente", 0)])
    writer.writerow(["TOT Urgente", brechas.get("tot_urgente", 0)])
    writer.writerow(["Reserva", brechas.get("reserva", 0)])
    writer.writerow(["Texto explicativo", brechas.get("texto_explicativo") or ""])

    deposito = analisis.get("deposito") or {}
    es_pipeline = deposito.get("tipo_eje") == "pipeline_fabricados"
    etapas_csv = etapas or deposito.get("etapas") or []

    mov_filas = []
    for mov in movimientos:
        fila = {
            "fecha_display": mov.get("fecha_display") or "-",
            "tipo_mov": mov.get("tipo_mov") or mov.get("clase_ui") or "-",
            "nro_comprobante": mov.get("nro_comprobante") or "-",
            "detalle": _detalle_movimiento_export(mov),
            "contado": "" if mov.get("conteo") is None else mov.get("conteo"),
            "entrada": _cantidad_export(mov, "entrada", modo),
            "salida": _cantidad_export(mov, "salida", modo),
            "saldo_corrido": mov.get("saldo_corrido", ""),
            "afecta_deposito": mov.get("afecta_deposito"),
            "operario": mov.get("operario") or "-",
        }
        if es_pipeline:
            saldos = mov.get("saldos_por_etapa") or {}
            fila["etapa_label"] = mov.get("etapa_label") or ""
            fila["cod_deposito"] = mov.get("cod_deposito", "")
            for et in etapas_csv:
                tipo = et.get("tipo_mpr")
                label = et.get("label") or tipo
                if tipo:
                    fila[f"saldo_{tipo}"] = saldos.get(tipo, "")
        mov_filas.append(fila)

    columnas_mov = [
        ("fecha_display", "Fecha"),
        ("tipo_mov", "Tipo"),
        ("nro_comprobante", "Comprobante"),
        ("detalle", "Detalle"),
        ("contado", "Contado"),
        ("entrada", "Entrada"),
        ("salida", "Salida"),
        ("saldo_corrido", "Saldo corrido"),
        ("afecta_deposito", "Afecta depósito"),
        ("operario", "Operario"),
    ]
    if es_pipeline:
        columnas_mov.extend([
            ("etapa_label", "Etapa"),
            ("cod_deposito", "Cód. depósito"),
        ])
        for et in etapas_csv:
            tipo = et.get("tipo_mpr")
            label = et.get("label") or tipo
            if tipo:
                columnas_mov.append((f"saldo_{tipo}", f"Saldo {label}"))

    _escribir_seccion_csv(writer, "MOVIMIENTOS", columnas_mov, mov_filas)

    if es_pipeline and etapas_csv:
        writer.writerow([])
        writer.writerow(["SALDOS POR ETAPA"])
        writer.writerow(["Concepto", "Valor"])
        saldo_ini = analisis.get("saldo_inicial") or {}
        por_ini = saldo_ini.get("por_etapa") or {}
        kpis = analisis.get("kpis") or {}
        por_cierre = kpis.get("saldo_final_por_etapa") or {}
        stock_pe = (analisis.get("stock") or {}).get("por_etapa") or {}
        for et in etapas_csv:
            tipo = et.get("tipo_mpr")
            label = et.get("label") or tipo
            if not tipo:
                continue
            writer.writerow([f"Inicial {label}", por_ini.get(tipo, 0)])
            writer.writerow([f"Cierre {label}", por_cierre.get(tipo, 0)])
            writer.writerow([f"Stock actual {label}", stock_pe.get(tipo, 0)])
            writer.writerow([
                f"Diferencia {label}",
                int(por_cierre.get(tipo, 0)) - int(stock_pe.get(tipo, 0)),
            ])

    evento_filas = []
    for ev in eventos:
        evento_filas.append({
            "fecha_display": ev.get("fecha_display") or "-",
            "tipo_label": ev.get("tipo_label") or ev.get("tipo") or "-",
            "cantidad": _cantidad_export(ev, "cantidad", modo),
            "detalle": ev.get("detalle") or "",
            "operario": ev.get("operario") or "-",
        })
    _escribir_seccion_csv(
        writer,
        "EVENTOS MPR",
        [
            ("fecha_display", "Fecha"),
            ("tipo_label", "Tipo"),
            ("cantidad", "Cantidad"),
            ("detalle", "Detalle"),
            ("operario", "Operario"),
        ],
        evento_filas,
    )

    writer.writerow([])
    writer.writerow(["A PRODUCIR"])
    writer.writerow(["Concepto", "Valor"])
    writer.writerow(["Cantidad a producir", a_producir.get("cantidad", 0)])
    writer.writerow(["Capacidad Semi", a_producir.get("capacidad_semi", 0)])
    writer.writerow(["Alerta Semi cero", "Sí" if a_producir.get("alerta_semi_cero") else "No"])

    return buf.getvalue().encode("utf-8")


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


def exportar_fabricados_superart_csv(
    context: Dict[str, Any],
    *,
    modo: str = "docenas",
) -> HttpResponse:
    """CSV consolidado por superartículo (mismas columnas que la tabla principal)."""
    meses_columnas = context.get("meses_columnas") or []
    filas = context.get("filas_superart") or []
    columnas: List[Tuple[str, str]] = [
        ("codigo_superart", "Código superartículo"),
        ("descripcion_superart", "Descripción superartículo"),
    ]
    for col in meses_columnas:
        ym = col.get("ym") or ""
        columnas.append((f"mes_{ym}", col.get("label") or ym))
    columnas.append(("total_display", "Total"))

    csv_rows: List[Dict[str, Any]] = []
    for sa in filas:
        row = {
            "codigo_superart": sa.get("codigo_superart") or "",
            "descripcion_superart": sa.get("descripcion_superart") or "",
            "total_display": sa.get("total_display") or sa.get("total"),
        }
        for cm in sa.get("columnas_mes") or []:
            row[f"mes_{cm.get('ym')}"] = cm.get("display")
        csv_rows.append(row)
    tot = {
        "codigo_superart": "TOTALES",
        "descripcion_superart": "",
        "total_display": context.get("total_general_display") or context.get("total_general"),
    }
    for cm in context.get("totales_columnas") or []:
        tot[f"mes_{cm.get('ym')}"] = cm.get("display")
    csv_rows.append(tot)

    payload = filas_a_csv(csv_rows, columnas)
    resp = HttpResponse(payload, content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="fabricados_superart.csv"'
    return resp


def exportar_fabricados_superart_xlsx(
    context: Dict[str, Any],
    *,
    titulo: str = "Fabricados por superartículo",
) -> HttpResponse:
    """Excel con hojas Por superartículo y Detalle por artículo."""
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    meses_columnas = context.get("meses_columnas") or []
    wb = openpyxl.Workbook()
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)

    def _write_sheet(ws, headers: List[str], data_rows: List[List[Any]], total_row: Optional[List[Any]] = None):
        for c, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=c, value=h)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")
        r = 2
        for vals in data_rows:
            for c, v in enumerate(vals, 1):
                ws.cell(row=r, column=c, value=v)
            r += 1
        if total_row:
            for c, v in enumerate(total_row, 1):
                cell = ws.cell(row=r, column=c, value=v)
                cell.font = Font(bold=True)
        for col_num in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col_num)].width = min(18, max(10, len(str(headers[col_num - 1])) + 2))

    ws1 = wb.active
    ws1.title = "Por superartículo"
    h1 = ["Código", "Descripción"] + [c.get("label") or c.get("ym") for c in meses_columnas] + ["Total"]
    rows1: List[List[Any]] = []
    for sa in context.get("filas_superart") or []:
        vals = [
            sa.get("codigo_superart") or "",
            sa.get("descripcion_superart") or "",
        ]
        vals.extend(cm.get("display") for cm in (sa.get("columnas_mes") or []))
        vals.append(sa.get("total_display") or sa.get("total"))
        rows1.append(vals)
    tot1 = ["TOTALES", ""]
    tot1.extend(cm.get("display") for cm in (context.get("totales_columnas") or []))
    tot1.append(context.get("total_general_display") or context.get("total_general"))
    _write_sheet(ws1, h1, rows1, tot1)

    ws2 = wb.create_sheet("Detalle por artículo")
    h2 = ["Superartículo", "Código artículo", "Descripción artículo"] + [
        c.get("label") or c.get("ym") for c in meses_columnas
    ] + ["Total"]
    rows2: List[List[Any]] = []
    for sa in context.get("filas_superart") or []:
        sa_label = sa.get("descripcion_superart") or sa.get("codigo_superart") or ""
        for art in sa.get("articulos") or []:
            vals = [
                sa_label,
                art.get("codigo_articulo") or "",
                art.get("descripcion_articulo") or "",
            ]
            vals.extend(cm.get("display") for cm in (art.get("columnas_mes") or []))
            vals.append(art.get("total_display") or art.get("total"))
            rows2.append(vals)
    _write_sheet(ws2, h2, rows2, None)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="fabricados_superart.xlsx"'
    return response
