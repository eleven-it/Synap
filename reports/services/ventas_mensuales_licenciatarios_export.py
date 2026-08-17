# -*- coding: utf-8 -*-
"""Export Excel anual Monthly Reporting licenciatarios (openpyxl + plantillas)."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List

import openpyxl
from openpyxl.utils import get_column_letter

from core.utils.administranet_types import str_or_default
from reports.models import MonthlyReportingPack
from reports.services.monthly_reporting_pack_seed import MONTHLY_REPORTING_TEMPLATE_FILES
from reports.services.monthly_reporting_template_builder import TEMPLATE_DIR
from reports.services.ventas_mensuales_licenciatarios_merger import (
    MergeResult,
    MergedClientMonth,
)

SHEET_SALES = "input Licensee sales"
SHEET_MONTHLY = "monthly"
SHEET_OOH = "input Licensee ooh"
SHEET_MINIMUM = "minimum agreed"
QA_SHEET = "QA"

QA_HEADERS = ("SuperArt / tipo", "Detalle", "Cliente", "Estado match")
SALES_HEADERS_LEVIS = ("Customer", "City / Province", "Store Type", "Product group")
YTD_UNITS_HEADER = "YTD_Units"
YTD_SALES_HEADER = "YTD_Sales"
SUM_LAST_ROW = 4931
UNITS_FORMAT = "#,##0"
AMOUNTS_FORMAT = '"$"#,##0.00'
MONTH_DATE_FORMAT = "mmm-yy"


def resolve_template_path(pack_id: str) -> Path:
    filename = MONTHLY_REPORTING_TEMPLATE_FILES[pack_id]
    return TEMPLATE_DIR / filename


def _month_columns(year: int) -> List[tuple[int, date]]:
    """Enero siempre en columna E (5), 12 pares units|amounts — mismo eje que la plantilla Levi’s."""
    cols: List[tuple[int, date]] = []
    col = 5
    for month in range(1, 13):
        cols.append((col, date(year, month, 1)))
        col += 2
    return cols


def _write_row2_sums(ws, columns: Iterable[int]) -> None:
    for col_idx in columns:
        letter = get_column_letter(col_idx)
        cell = ws.cell(row=2, column=col_idx)
        cell.value = f"=SUM({letter}5:{letter}{SUM_LAST_ROW})"


def _client_meta_from_rows(rows: Iterable[MergedClientMonth]) -> Dict[str, dict]:
    meta: Dict[str, dict] = {}
    for row in rows:
        bucket = meta.setdefault(
            row.identity,
            {
                "display_name": row.display_name,
                "city": "",
                "store_type": "",
                "product_group": "",
                "match_estado": row.match_estado,
                "pending": row.pending,
            },
        )
        bucket["display_name"] = row.display_name
        bucket["match_estado"] = row.match_estado
        bucket["pending"] = row.pending
        if row.city:
            bucket["city"] = row.city
        if row.store_type:
            bucket["store_type"] = row.store_type
        if row.product_group:
            bucket["product_group"] = row.product_group
    return meta


def _write_levis_sales_sheet(
    ws,
    *,
    rows: List[MergedClientMonth],
    year: int,
    month_from: int,
    month_to: int,
    product_group: str,
) -> None:
    month_cols = _month_columns(year)
    for idx, label in enumerate(SALES_HEADERS_LEVIS, start=1):
        ws.cell(row=4, column=idx, value=label)
    ytd_units_col = 29
    ytd_sales_col = 30
    ws.cell(row=4, column=ytd_units_col, value=YTD_UNITS_HEADER)
    ws.cell(row=4, column=ytd_sales_col, value=YTD_SALES_HEADER)
    for col_idx, month_date in month_cols:
        month_cell = ws.cell(row=4, column=col_idx, value=month_date)
        month_cell.number_format = MONTH_DATE_FORMAT
        ws.cell(row=3, column=col_idx, value="units")
        ws.cell(row=3, column=col_idx + 1, value="amounts")

    by_client: dict[str, dict[date, MergedClientMonth]] = defaultdict(dict)
    client_meta = _client_meta_from_rows(rows)
    for row in rows:
        by_client[row.identity][row.month] = row

    excel_row = 5
    unit_letters = [get_column_letter(col_idx) for col_idx, _ in month_cols]
    amount_letters = [get_column_letter(col_idx + 1) for col_idx, _ in month_cols]
    ytd_units_formula_tpl = "=" + "+".join(f"{letter}{{row}}" for letter in reversed(unit_letters))
    ytd_sales_formula_tpl = "=" + "+".join(f"{letter}{{row}}" for letter in reversed(amount_letters))

    for identity, months_map in sorted(
        by_client.items(),
        key=lambda item: client_meta[item[0]]["display_name"].upper(),
    ):
        meta = client_meta[identity]
        ws.cell(row=excel_row, column=1, value=meta["display_name"])
        ws.cell(row=excel_row, column=2, value=meta.get("city") or "")
        ws.cell(row=excel_row, column=3, value=meta.get("store_type") or "")
        ws.cell(
            row=excel_row,
            column=4,
            value=meta.get("product_group") or product_group,
        )
        for col_idx, month_date in month_cols:
            if month_date.month < month_from or month_date.month > month_to:
                continue
            cell = months_map.get(month_date)
            if cell is None:
                continue
            units_cell = ws.cell(row=excel_row, column=col_idx, value=float(cell.units))
            units_cell.number_format = UNITS_FORMAT
            amount_cell = ws.cell(row=excel_row, column=col_idx + 1, value=float(cell.amount))
            amount_cell.number_format = AMOUNTS_FORMAT
        ws.cell(
            row=excel_row,
            column=ytd_units_col,
            value=ytd_units_formula_tpl.format(row=excel_row),
        )
        ws.cell(
            row=excel_row,
            column=ytd_sales_col,
            value=ytd_sales_formula_tpl.format(row=excel_row),
        )
        excel_row += 1

    if ws.max_row >= excel_row:
        ws.delete_rows(excel_row, ws.max_row - excel_row + 1)

    sum_cols = [col for col_idx, _ in month_cols for col in (col_idx, col_idx + 1)]
    sum_cols.extend([ytd_units_col, ytd_sales_col])
    _write_row2_sums(ws, sum_cols)


def _ensure_monthly_links_row2(ws) -> None:
    """La hoja monthly lee totales de la fila 2 de input Licensee sales. No volcar YTD en español."""
    if not ws["B2"].value:
        ws["B2"] = "Best Sox"
    if not ws["D4"].value:
        ws["D4"] = "='input Licensee sales'!E2"


def _write_qa_sheet(
    wb: openpyxl.Workbook,
    *,
    merge_result: MergeResult,
) -> None:
    if QA_SHEET in wb.sheetnames:
        ws = wb[QA_SHEET]
        wb.remove(ws)
    ws = wb.create_sheet(QA_SHEET)
    for col, header in enumerate(QA_HEADERS, start=1):
        ws.cell(row=1, column=col, value=header)

    row = 2
    for superart in merge_result.qa_superarts:
        ws.cell(row=row, column=1, value=superart)
        ws.cell(row=row, column=2, value="SuperArt desconocido")
        row += 1

    for pending in merge_result.pending_clients:
        ws.cell(row=row, column=1, value="match_pendiente")
        ws.cell(row=row, column=2, value=pending.get("seed_key", ""))
        ws.cell(row=row, column=3, value=pending.get("display_name", ""))
        ws.cell(row=row, column=4, value="pending")
        row += 1


def export_licenciatarios_workbook(
    file_path: Path,
    *,
    pack: MonthlyReportingPack,
    merge_result: MergeResult,
    year: int,
    month_from: int,
    month_to: int,
) -> None:
    """
    Clona plantilla anual, reescribe ventas/mensual, conserva hojas auxiliares y agrega QA.
    """
    template_path = resolve_template_path(pack.pack_id)
    if not template_path.exists():
        raise FileNotFoundError(f"Plantilla no encontrada: {template_path}")

    wb = openpyxl.load_workbook(template_path)
    preserved = {SHEET_OOH, SHEET_MINIMUM} & set(wb.sheetnames)

    if SHEET_SALES not in wb.sheetnames:
        raise ValueError(f"La plantilla no contiene hoja '{SHEET_SALES}'")
    sales_ws = wb[SHEET_SALES]
    _write_levis_sales_sheet(
        sales_ws,
        rows=merge_result.rows,
        year=year,
        month_from=month_from,
        month_to=month_to,
        product_group=str_or_default(pack.product_group, ""),
    )

    if SHEET_MONTHLY in wb.sheetnames:
        _ensure_monthly_links_row2(wb[SHEET_MONTHLY])

    _write_qa_sheet(wb, merge_result=merge_result)

    for sheet_name in preserved:
        if sheet_name not in wb.sheetnames:
            raise ValueError(f"Se perdió la hoja auxiliar '{sheet_name}' durante el export")

    file_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(file_path)
