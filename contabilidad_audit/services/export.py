"""Exportación CSV/Excel de una corrida de auditoría contable.

Reutiliza las convenciones visuales del canon de reportes
(`reports/services/export_service.py`: openpyxl, estilos de cabecera,
bloque de metadatos) pero opera sobre el payload de `ejecutar_corrida()`,
que no es un `ReportDefinition`. Incluye `config_hash`, fecha dd/MM/yyyy
y detalle por check. No escribe nunca en el MySQL legacy.
"""
from __future__ import annotations

import csv
import io
import json
from typing import Any

from django.http import HttpResponse

SEVERIDAD_ETIQUETA = {
    "critico": "Crítico",
    "alto": "Alto",
    "medio": "Medio",
}

# Columnas del detalle de diferencias (orden estable, español).
_COLUMNAS_DIFERENCIA = [
    ("check_id", "Check"),
    ("titulo", "Título"),
    ("severidad", "Severidad"),
    ("referencia_hallazgo", "Referencia"),
    ("cod_pc", "Cód. cuenta"),
    ("id_pc", "ID cuenta"),
    ("id_ejercicio", "Ejercicio"),
    ("id_periodo", "Período"),
    ("nro_asiento", "N° asiento"),
    ("codigo_movimiento", "Cód. movimiento"),
    ("valor_esperado", "Valor esperado"),
    ("valor_actual", "Valor actual"),
    ("delta", "Delta"),
]

_COLUMNAS_RESUMEN = [
    ("check_id", "Check"),
    ("titulo", "Título"),
    ("severidad", "Severidad"),
    ("estado", "Estado"),
    ("total_evaluado", "Evaluados"),
    ("total_diferencias", "Diferencias"),
    ("error", "Error"),
]


def _severidad_label(valor: str) -> str:
    return SEVERIDAD_ETIQUETA.get((valor or "").lower(), valor or "")


def _estado_label(check: dict) -> str:
    if check.get("error"):
        return "Error"
    return "OK" if check.get("ok") else "Con diferencias"


def _nombre_archivo(payload: dict, extension: str) -> str:
    base = (payload.get("base_empresa") or "empresa").replace("/", "_")
    filtros = payload.get("filtros") or {}
    ejercicio = filtros.get("id_ejercicio") or "ejercicio"
    return f"auditoria_contable_{base}_{ejercicio}.{extension}"


def _filas_resumen(payload: dict) -> list[dict[str, Any]]:
    filas: list[dict[str, Any]] = []
    for check in payload.get("checks", []):
        filas.append(
            {
                "check_id": check.get("check_id", ""),
                "titulo": check.get("titulo", ""),
                "severidad": _severidad_label(check.get("severidad", "")),
                "estado": _estado_label(check),
                "total_evaluado": check.get("total_evaluado", 0),
                "total_diferencias": check.get("total_diferencias", 0),
                "error": check.get("error") or "",
            }
        )
    return filas


def _filas_diferencias(payload: dict) -> list[dict[str, Any]]:
    filas: list[dict[str, Any]] = []
    for check in payload.get("checks", []):
        for dif in check.get("diferencias", []):
            fila = {
                "check_id": check.get("check_id", ""),
                "titulo": check.get("titulo", ""),
                "severidad": _severidad_label(check.get("severidad", "")),
            }
            for clave, _label in _COLUMNAS_DIFERENCIA:
                if clave in ("check_id", "titulo", "severidad"):
                    continue
                fila[clave] = dif.get(clave)
            filas.append(fila)
    return filas


def _metadatos(payload: dict) -> list[tuple[str, str]]:
    filtros = payload.get("filtros") or {}
    return [
        ("Auditoría de imputación contable", ""),
        ("Empresa", str(payload.get("base_empresa") or "—")),
        ("Ejercicio", str(filtros.get("id_ejercicio") or "—")),
        ("Período", str(filtros.get("id_periodo")) if filtros.get("id_periodo") else "Todos"),
        ("Fecha de corrida", str(payload.get("fecha_corrida") or "—")),
        ("config_hash", str(payload.get("config_hash") or "—")),
        ("Corrida", str(payload.get("corrida_id") or "—")),
    ]


def exportar_corrida_csv(payload: dict) -> HttpResponse:
    """CSV plano: bloque de metadatos + resumen por check + detalle de diferencias."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    for etiqueta, valor in _metadatos(payload):
        writer.writerow([etiqueta, valor])
    writer.writerow([])

    writer.writerow(["Resumen por check"])
    writer.writerow([label for _clave, label in _COLUMNAS_RESUMEN])
    for fila in _filas_resumen(payload):
        writer.writerow([fila.get(clave, "") for clave, _label in _COLUMNAS_RESUMEN])
    writer.writerow([])

    writer.writerow(["Detalle de diferencias"])
    writer.writerow([label for _clave, label in _COLUMNAS_DIFERENCIA])
    filas_dif = _filas_diferencias(payload)
    if filas_dif:
        for fila in filas_dif:
            writer.writerow(
                ["" if fila.get(clave) is None else fila.get(clave) for clave, _label in _COLUMNAS_DIFERENCIA]
            )
    else:
        writer.writerow(["Sin diferencias en la corrida."])

    contenido = buffer.getvalue()
    # BOM para que Excel abra correctamente los acentos en UTF-8.
    response = HttpResponse(
        "\ufeff" + contenido,
        content_type="text/csv; charset=utf-8",
    )
    response["Content-Disposition"] = f'attachment; filename="{_nombre_archivo(payload, "csv")}"'
    return response


def exportar_corrida_xlsx(payload: dict) -> HttpResponse:
    """Excel con hoja Resumen (metadatos + por check) y hoja Diferencias."""
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    title_font = Font(bold=True, size=14, color="1E40AF")
    label_font = Font(bold=True, size=10)
    value_font = Font(size=10)
    border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    wb = openpyxl.Workbook()

    # ── Hoja Resumen ──────────────────────────────────────────────
    ws = wb.active
    ws.title = "Resumen"
    row = 1
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=len(_COLUMNAS_RESUMEN))
    cell = ws.cell(row=row, column=1, value="Auditoría de imputación contable")
    cell.font = title_font
    cell.alignment = Alignment(horizontal="left", vertical="center")
    row += 1

    for etiqueta, valor in _metadatos(payload)[1:]:
        lc = ws.cell(row=row, column=1, value=etiqueta)
        lc.font = label_font
        vc = ws.cell(row=row, column=2, value=valor)
        vc.font = value_font
        vc.alignment = Alignment(horizontal="left", vertical="center")
        row += 1
    row += 1

    ws.cell(row=row, column=1, value="Resumen por check").font = Font(bold=True, size=12)
    row += 1
    for col_num, (_clave, label) in enumerate(_COLUMNAS_RESUMEN, 1):
        c = ws.cell(row=row, column=col_num, value=label)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = border
    row += 1
    for fila in _filas_resumen(payload):
        for col_num, (clave, _label) in enumerate(_COLUMNAS_RESUMEN, 1):
            c = ws.cell(row=row, column=col_num, value=fila.get(clave, ""))
            c.border = border
            c.alignment = Alignment(horizontal="left", vertical="center")
        row += 1

    for col_num in range(1, ws.max_column + 1):
        col_letter = get_column_letter(col_num)
        max_len = 0
        for cell in ws[col_letter]:
            if cell.value is not None:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = min(max_len + 2, 60)

    # ── Hoja Diferencias ──────────────────────────────────────────
    ws2 = wb.create_sheet("Diferencias")
    row = 1
    for col_num, (_clave, label) in enumerate(_COLUMNAS_DIFERENCIA, 1):
        c = ws2.cell(row=row, column=col_num, value=label)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = border
    row += 1
    filas_dif = _filas_diferencias(payload)
    if filas_dif:
        for fila in filas_dif:
            for col_num, (clave, _label) in enumerate(_COLUMNAS_DIFERENCIA, 1):
                valor = fila.get(clave)
                c = ws2.cell(row=row, column=col_num, value="" if valor is None else valor)
                c.border = border
                c.alignment = Alignment(horizontal="left", vertical="center")
            row += 1
    else:
        ws2.cell(row=row, column=1, value="Sin diferencias en la corrida.")

    for col_num in range(1, ws2.max_column + 1):
        col_letter = get_column_letter(col_num)
        max_len = 0
        for cell in ws2[col_letter]:
            if cell.value is not None:
                max_len = max(max_len, len(str(cell.value)))
        ws2.column_dimensions[col_letter].width = min(max_len + 2, 40)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{_nombre_archivo(payload, "xlsx")}"'
    return response


# ── Export dry-run Fase 2 ───────────────────────────────────────────────────

_COLUMNAS_PLAN_ITEM = [
    ("tabla", "Tabla"),
    ("accion", "Acción"),
    ("check_id", "Check"),
    ("referencia", "Referencia"),
    ("id_pc", "ID cuenta"),
    ("id_ejercicio", "Ejercicio"),
    ("codigo_movimiento", "Cód. movimiento"),
    ("valor_anterior", "Valor anterior"),
    ("valor_nuevo", "Valor nuevo"),
    ("delta", "Delta"),
    ("excluido", "Excluido"),
    ("motivo_exclusion", "Motivo exclusión"),
]


def _nombre_archivo_dry_run(payload: dict, extension: str) -> str:
    base = (payload.get("base_empresa") or "empresa").replace("/", "_")
    alcance = payload.get("alcance") or {}
    ejercicio = alcance.get("id_ejercicio") or "ejercicio"
    dry_id = (payload.get("dry_run_id") or "plan")[:8]
    return f"dry_run_contable_{base}_{ejercicio}_{dry_id}.{extension}"


def _metadatos_dry_run(payload: dict) -> list[tuple[str, str]]:
    alcance = payload.get("alcance") or {}
    impacto = payload.get("impacto") or {}
    totales = impacto.get("totales_por_tabla") or {}
    return [
        ("Dry-run de corrección contable", ""),
        ("Empresa", str(payload.get("base_empresa") or "—")),
        ("Ejercicio (alcance)", str(alcance.get("id_ejercicio") or "—")),
        ("dry_run_id", str(payload.get("dry_run_id") or "—")),
        ("Fecha dry-run", str(payload.get("creado_en") or "—")),
        ("Expira", str(payload.get("expira_en") or "—")),
        ("config_hash", str(payload.get("config_hash") or "—")),
        ("data_fingerprint", str(payload.get("data_fingerprint") or "—")),
        ("TTL (minutos)", str((payload.get("guards") or {}).get("ttl_minutos", "—"))),
        ("Total items plan", str(impacto.get("total_items", 0))),
        ("Items aplicables", str(impacto.get("total_aplicables", 0))),
        ("Items excluidos", str(impacto.get("total_excluidos", 0))),
        ("cont_asiento (items)", str(totales.get("cont_asiento", 0))),
        ("cont_ejercicio_saldo_cta (items)", str(totales.get("cont_ejercicio_saldo_cta", 0))),
    ]


def _filas_plan_items(payload: dict) -> list[dict[str, Any]]:
    plan = payload.get("plan") or {}
    filas: list[dict[str, Any]] = []
    for item in plan.get("items") or []:
        clave = item.get("clave") or {}
        vn = item.get("valor_nuevo")
        if isinstance(vn, dict):
            valor_nuevo_str = json.dumps(vn, ensure_ascii=False, sort_keys=True)
        else:
            valor_nuevo_str = "" if vn is None else str(vn)
        filas.append(
            {
                "tabla": item.get("tabla", ""),
                "accion": item.get("accion", ""),
                "check_id": item.get("check_id", ""),
                "referencia": item.get("referencia", ""),
                "id_pc": clave.get("id_pc") or (vn.get("id_pc") if isinstance(vn, dict) else ""),
                "id_ejercicio": clave.get("id_ejercicio")
                or (vn.get("id_ejercicio") if isinstance(vn, dict) else ""),
                "codigo_movimiento": clave.get("codigo_movimiento")
                or (vn.get("codigo_movimiento") if isinstance(vn, dict) else ""),
                "valor_anterior": item.get("valor_anterior"),
                "valor_nuevo": valor_nuevo_str,
                "delta": item.get("delta"),
                "excluido": "Sí" if item.get("excluido") else "No",
                "motivo_exclusion": item.get("motivo_exclusion") or "",
            }
        )
    return filas


def exportar_dry_run_csv(payload: dict) -> HttpResponse:
    """CSV del plan dry-run con metadatos, impacto y detalle de items."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    for etiqueta, valor in _metadatos_dry_run(payload):
        writer.writerow([etiqueta, valor])
    writer.writerow([])

    impacto = payload.get("impacto") or {}
    writer.writerow(["Impacto por tipo de comprobante"])
    por_tipo = impacto.get("asientos_regenerar_por_tipo") or {}
    if por_tipo:
        writer.writerow(["Tipo", "Asientos a regenerar"])
        for tipo, cant in sorted(por_tipo.items()):
            writer.writerow([tipo, cant])
    else:
        writer.writerow(["Sin regeneración de asientos en el alcance."])
    writer.writerow([])

    writer.writerow(["Cuentas impactadas (delta saldo)"])
    writer.writerow(["ID cuenta", "Delta total"])
    for cuenta in impacto.get("cuentas_impactadas") or []:
        writer.writerow([cuenta.get("id_pc"), cuenta.get("delta_total")])
    writer.writerow([])

    backups = payload.get("backups_propuestos") or {}
    if backups:
        writer.writerow(["Backups propuestos (simulados)"])
        for tabla, nombre in sorted(backups.items()):
            writer.writerow([tabla, nombre])
        writer.writerow([])

    writer.writerow(["Detalle del plan"])
    writer.writerow([label for _clave, label in _COLUMNAS_PLAN_ITEM])
    filas = _filas_plan_items(payload)
    if filas:
        for fila in filas:
            writer.writerow([fila.get(clave, "") for clave, _label in _COLUMNAS_PLAN_ITEM])
    else:
        writer.writerow(["Plan vacío: no hay cambios propuestos en el alcance."])

    response = HttpResponse(
        "\ufeff" + buffer.getvalue(),
        content_type="text/csv; charset=utf-8",
    )
    response["Content-Disposition"] = f'attachment; filename="{_nombre_archivo_dry_run(payload, "csv")}"'
    return response


def exportar_dry_run_xlsx(payload: dict) -> HttpResponse:
    """Excel del dry-run: Resumen + Plan."""
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    title_font = Font(bold=True, size=14, color="1E40AF")
    label_font = Font(bold=True, size=10)
    value_font = Font(size=10)
    border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Resumen"
    row = 1
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
    cell = ws.cell(row=row, column=1, value="Dry-run de corrección contable")
    cell.font = title_font
    row += 1

    for etiqueta, valor in _metadatos_dry_run(payload)[1:]:
        ws.cell(row=row, column=1, value=etiqueta).font = label_font
        ws.cell(row=row, column=2, value=valor).font = value_font
        row += 1
    row += 1

    impacto = payload.get("impacto") or {}
    ws.cell(row=row, column=1, value="Asientos a regenerar por tipo").font = Font(bold=True, size=12)
    row += 1
    for tipo, cant in sorted((impacto.get("asientos_regenerar_por_tipo") or {}).items()):
        ws.cell(row=row, column=1, value=tipo)
        ws.cell(row=row, column=2, value=cant)
        row += 1
    row += 1

    ws2 = wb.create_sheet("Plan")
    row = 1
    for col_num, (_clave, label) in enumerate(_COLUMNAS_PLAN_ITEM, 1):
        c = ws2.cell(row=row, column=col_num, value=label)
        c.fill = header_fill
        c.font = header_font
        c.border = border
    row += 1
    for fila in _filas_plan_items(payload):
        for col_num, (clave, _label) in enumerate(_COLUMNAS_PLAN_ITEM, 1):
            c = ws2.cell(row=row, column=col_num, value=fila.get(clave, ""))
            c.border = border
        row += 1

    for hoja in (ws, ws2):
        for col_num in range(1, hoja.max_column + 1):
            col_letter = get_column_letter(col_num)
            max_len = 0
            for cell_obj in hoja[col_letter]:
                if cell_obj.value is not None:
                    max_len = max(max_len, len(str(cell_obj.value)))
            hoja.column_dimensions[col_letter].width = min(max_len + 2, 50)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{_nombre_archivo_dry_run(payload, "xlsx")}"'
    return response
