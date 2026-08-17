# -*- coding: utf-8 -*-
"""Export Excel anual Monthly Reporting licenciatarios (openpyxl + plantillas)."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import openpyxl

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
SALES_HEADERS_LEVIS = ("Customer", "City", "Store Type", "Product group")


def resolve_template_path(pack_id: str) -> Path:
    filename = MONTHLY_REPORTING_TEMPLATE_FILES[pack_id]
    return TEMPLATE_DIR / filename


def _month_columns(month_from: int, month_to: int, year: int) -> List[tuple[int, date]]:
    cols: List[tuple[int, date]] = []
    col = 5
    for month in range(month_from, month_to + 1):
        cols.append((col, date(year, month, 1)))
        col += 2
    return cols


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
    month_cols = _month_columns(month_from, month_to, year)
    for idx, label in enumerate(SALES_HEADERS_LEVIS, start=1):
        ws.cell(row=4, column=idx, value=label)
    for col_idx, month_date in month_cols:
        ws.cell(row=4, column=col_idx, value=month_date)
    ws.cell(row=3, column=5, value="units")
    ws.cell(row=3, column=6, value="amounts")

    by_client: dict[str, dict[date, MergedClientMonth]] = defaultdict(dict)
    client_meta = _client_meta_from_rows(rows)
    for row in rows:
        by_client[row.identity][row.month] = row

    excel_row = 5
    for identity, months_map in sorted(
        by_client.items(),
        key=lambda item: client_meta[item[0]]["display_name"].upper(),
    ):
        meta = client_meta[identity]
        ws.cell(row=excel_row, column=1, value=meta["display_name"])
        ws.cell(row=excel_row, column=2, value=meta.get("city") or "")
        ws.cell(row=excel_row, column=3, value=meta.get("store_type") or "")
        ws.cell(row=excel_row, column=4, value=meta.get("product_group") or product_group)
        for col_idx, month_date in month_cols:
            cell = months_map.get(month_date)
            if cell is None:
                continue
            ws.cell(row=excel_row, column=col_idx, value=float(cell.units))
            ws.cell(row=excel_row, column=col_idx + 1, value=float(cell.amount))
        excel_row += 1


def _write_monthly_ytd(
    ws,
    *,
    merge_result: MergeResult,
    year: int,
    month_to: int,
) -> None:
    """Recalcula YTD acumulado en hoja monthly (columna auxiliar)."""
    ws["B2"] = "Best Sox"
    ws["A20"] = "YTD recalculado Synap"
    ws["B20"] = "Cliente"
    ws["C20"] = "Unidades YTD"
    ws["D20"] = "Facturación YTD"
    excel_row = 21
    for identity, bucket in sorted(merge_result.ytd_by_identity.items()):
        display = next(
            (r.display_name for r in merge_result.rows if r.identity == identity),
            identity,
        )
        ws.cell(row=excel_row, column=2, value=display)
        ws.cell(row=excel_row, column=3, value=float(bucket.get("units", 0)))
        ws.cell(row=excel_row, column=4, value=float(bucket.get("amount", 0)))
        excel_row += 1
    ws["A19"] = f"FY {year} hasta mes {month_to:02d}"


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
        _write_monthly_ytd(
            wb[SHEET_MONTHLY],
            merge_result=merge_result,
            year=year,
            month_to=month_to,
        )

    _write_qa_sheet(wb, merge_result=merge_result)

    for sheet_name in preserved:
        if sheet_name not in wb.sheetnames:
            raise ValueError(f"Se perdió la hoja auxiliar '{sheet_name}' durante el export")

    file_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(file_path)
