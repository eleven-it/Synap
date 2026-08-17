# -*- coding: utf-8 -*-
"""Conciliación planillas Monthly Reporting vs seed PostgreSQL."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Optional, Sequence

from reports.models import MonthlyReportingPack, MonthlyReportingSeedRow
from reports.services.monthly_reporting_pack_seed import (
    MONTHLY_REPORTING_SOURCE_FILENAMES as PACK_SOURCE_FILES,
    iter_monthly_reporting_pack_ids,
)
from reports.services.ventas_mensuales_licenciatarios_importer import (
    ParsedSeedCell,
    parse_monthly_reporting_workbook,
)
from reports.services.ventas_mensuales_licenciatarios_merger import CUTOVER_DATE
from reports.services.ventas_marcas_mensual_rules import TIPOS_FAC, TIPOS_NC

DEFAULT_SOURCE_DIR = Path("/Users/sebastian/Documents/Best Sox/fwdreportesjun")

FA_NC_REFERENCE_NOTE = (
    "La porción AdministraNET (≥22/07/2026) usa las reglas compartidas VMM "
    f"(FAC={','.join(sorted(TIPOS_FAC))}; NC={','.join(sorted(TIPOS_NC))}). "
    "La conciliación seed compara solo ene–jun (+ jul 1–21) del Excel fuente; "
    "FA/NC se valida en tests VMM y en smoke ANET post-cutover, no en paridad binaria xlsx."
)


@dataclass(frozen=True)
class ClientMonthTotal:
    seed_key: str
    customer_name: str
    month: date
    units: Decimal
    amount: Decimal


@dataclass
class ReconciliationMismatch:
    seed_key: str
    customer_name: str
    month: date
    kind: str
    file_value: Optional[Decimal] = None
    db_value: Optional[Decimal] = None


@dataclass
class YtdClientTotal:
    seed_key: str
    customer_name: str
    units: Decimal
    amount: Decimal


@dataclass
class PackReconciliationResult:
    pack_id: str
    file_path: Optional[str] = None
    file_accessible: bool = False
    file_row_count: int = 0
    db_row_count: int = 0
    coincidencias: int = 0
    discrepancias: list[ReconciliationMismatch] = field(default_factory=list)
    ytd_file: list[YtdClientTotal] = field(default_factory=list)
    ytd_db: list[YtdClientTotal] = field(default_factory=list)
    fa_nc_note: str = FA_NC_REFERENCE_NOTE


@dataclass
class ReconciliationResult:
    dry_run: bool
    year: int
    source_dir: str
    packs: list[PackReconciliationResult] = field(default_factory=list)

    @property
    def total_coincidencias(self) -> int:
        return sum(p.coincidencias for p in self.packs)

    @property
    def total_discrepancias(self) -> int:
        return sum(len(p.discrepancias) for p in self.packs)


def _aggregate_key(seed_key: str, month: date) -> tuple[str, date]:
    return seed_key, month


def aggregate_parsed_cells(
    cells: Iterable[ParsedSeedCell],
) -> dict[tuple[str, date], ClientMonthTotal]:
    """Agrega celdas parseadas del Excel por seed_key×mes."""
    buckets: dict[tuple[str, date], ClientMonthTotal] = {}
    for cell in cells:
        key = _aggregate_key(cell.seed_key, cell.month)
        existing = buckets.get(key)
        if existing is None:
            buckets[key] = ClientMonthTotal(
                seed_key=cell.seed_key,
                customer_name=cell.customer_name,
                month=cell.month,
                units=cell.units,
                amount=cell.amount,
            )
            continue
        buckets[key] = ClientMonthTotal(
            seed_key=cell.seed_key,
            customer_name=cell.customer_name or existing.customer_name,
            month=cell.month,
            units=existing.units + cell.units,
            amount=existing.amount + cell.amount,
        )
    return buckets


def aggregate_db_seed_rows(
    pack_id: str,
    *,
    year: int,
) -> dict[tuple[str, date], ClientMonthTotal]:
    """Agrega filas seed PostgreSQL por match×mes para un pack y año."""
    rows = (
        MonthlyReportingSeedRow.objects.filter(
            pack__pack_id=pack_id,
            month__year=year,
        )
        .select_related("match")
        .order_by("month", "match__seed_key")
    )
    buckets: dict[tuple[str, date], ClientMonthTotal] = {}
    for row in rows:
        match = row.match
        key = _aggregate_key(match.seed_key, row.month)
        existing = buckets.get(key)
        if existing is None:
            buckets[key] = ClientMonthTotal(
                seed_key=match.seed_key,
                customer_name=match.seed_customer_name,
                month=row.month,
                units=row.units,
                amount=row.amount,
            )
            continue
        buckets[key] = ClientMonthTotal(
            seed_key=match.seed_key,
            customer_name=match.seed_customer_name or existing.customer_name,
            month=row.month,
            units=existing.units + row.units,
            amount=existing.amount + row.amount,
        )
    return buckets


def compare_seed_aggregates(
    file_agg: dict[tuple[str, date], ClientMonthTotal],
    db_agg: dict[tuple[str, date], ClientMonthTotal],
) -> tuple[int, list[ReconciliationMismatch]]:
    """Compara totales archivo vs DB; devuelve coincidencias y discrepancias."""
    coincidencias = 0
    discrepancias: list[ReconciliationMismatch] = []
    all_keys = set(file_agg) | set(db_agg)
    for key in sorted(all_keys, key=lambda item: (item[1], item[0])):
        file_row = file_agg.get(key)
        db_row = db_agg.get(key)
        if file_row is None and db_row is not None:
            discrepancias.append(
                ReconciliationMismatch(
                    seed_key=db_row.seed_key,
                    customer_name=db_row.customer_name,
                    month=db_row.month,
                    kind="missing_in_file",
                    db_value=db_row.amount,
                )
            )
            continue
        if db_row is None and file_row is not None:
            discrepancias.append(
                ReconciliationMismatch(
                    seed_key=file_row.seed_key,
                    customer_name=file_row.customer_name,
                    month=file_row.month,
                    kind="missing_in_db",
                    file_value=file_row.amount,
                )
            )
            continue
        assert file_row is not None and db_row is not None
        row_ok = True
        if file_row.units != db_row.units:
            row_ok = False
            discrepancias.append(
                ReconciliationMismatch(
                    seed_key=file_row.seed_key,
                    customer_name=file_row.customer_name,
                    month=file_row.month,
                    kind="units",
                    file_value=file_row.units,
                    db_value=db_row.units,
                )
            )
        if file_row.amount != db_row.amount:
            row_ok = False
            discrepancias.append(
                ReconciliationMismatch(
                    seed_key=file_row.seed_key,
                    customer_name=file_row.customer_name,
                    month=file_row.month,
                    kind="amount",
                    file_value=file_row.amount,
                    db_value=db_row.amount,
                )
            )
        if row_ok:
            coincidencias += 1
    return coincidencias, discrepancias


def compute_ytd_from_aggregates(
    aggregates: dict[tuple[str, date], ClientMonthTotal],
    *,
    year: int,
    through_month: int = 12,
) -> list[YtdClientTotal]:
    """Calcula YTD por cliente desde agregados pack×cliente×mes."""
    by_client: dict[str, YtdClientTotal] = {}
    for (_seed_key, month), row in aggregates.items():
        if month.year != year or month.month > through_month:
            continue
        existing = by_client.get(row.seed_key)
        if existing is None:
            by_client[row.seed_key] = YtdClientTotal(
                seed_key=row.seed_key,
                customer_name=row.customer_name,
                units=row.units,
                amount=row.amount,
            )
            continue
        by_client[row.seed_key] = YtdClientTotal(
            seed_key=row.seed_key,
            customer_name=row.customer_name or existing.customer_name,
            units=existing.units + row.units,
            amount=existing.amount + row.amount,
        )
    return sorted(by_client.values(), key=lambda item: item.customer_name.lower())


def resolve_pack_source_path(
    pack_id: str,
    source_dir: Path | str,
) -> Path:
    """Resuelve ruta de planilla fuente para un pack."""
    filename = PACK_SOURCE_FILES.get(pack_id)
    if not filename:
        raise ValueError(f"Pack sin archivo fuente configurado: {pack_id}")
    return Path(source_dir) / filename


def reconcile_pack_from_file(
    pack_id: str,
    file_path: Path | str,
    *,
    year: int = 2026,
    through_month: int = 6,
) -> PackReconciliationResult:
    """Concilia una planilla contra seed PostgreSQL del pack."""
    path = Path(file_path)
    pack = MonthlyReportingPack.objects.get(pack_id=pack_id)
    result = PackReconciliationResult(
        pack_id=pack_id,
        file_path=str(path),
        file_accessible=path.exists(),
    )
    if not path.exists():
        result.discrepancias.append(
            ReconciliationMismatch(
                seed_key="",
                customer_name="",
                month=date(year, 1, 1),
                kind="file_not_found",
            )
        )
        return result

    parsed = parse_monthly_reporting_workbook(path, pack, default_year=year)
    file_agg = aggregate_parsed_cells(parsed)
    db_agg = aggregate_db_seed_rows(pack_id, year=year)

    # Limitar seed a ene–jun (+ jul 1–21 conceptualmente en through_month)
    seed_month_limit = through_month
    if year == CUTOVER_DATE.year and through_month >= 7:
        seed_month_limit = 7

    file_agg_seed = {
        key: row
        for key, row in file_agg.items()
        if key[1].year == year and key[1].month <= seed_month_limit
    }
    db_agg_seed = {
        key: row
        for key, row in db_agg.items()
        if key[1].year == year and key[1].month <= seed_month_limit
    }

    result.file_row_count = len(file_agg_seed)
    result.db_row_count = len(db_agg_seed)
    result.coincidencias, result.discrepancias = compare_seed_aggregates(
        file_agg_seed,
        db_agg_seed,
    )
    result.ytd_file = compute_ytd_from_aggregates(
        file_agg_seed,
        year=year,
        through_month=seed_month_limit,
    )
    result.ytd_db = compute_ytd_from_aggregates(
        db_agg_seed,
        year=year,
        through_month=seed_month_limit,
    )
    return result


def reconcile_all_packs(
    *,
    source_dir: Path | str = DEFAULT_SOURCE_DIR,
    pack_ids: Optional[Sequence[str]] = None,
    year: int = 2026,
    through_month: int = 6,
    dry_run: bool = True,
) -> ReconciliationResult:
    """Concilia los 6 packs contra seed PostgreSQL (solo lectura)."""
    selected = list(pack_ids or iter_monthly_reporting_pack_ids())
    result = ReconciliationResult(
        dry_run=dry_run,
        year=year,
        source_dir=str(source_dir),
    )
    for pack_id in selected:
        file_path = resolve_pack_source_path(pack_id, source_dir)
        result.packs.append(
            reconcile_pack_from_file(
                pack_id,
                file_path,
                year=year,
                through_month=through_month,
            )
        )
    return result
