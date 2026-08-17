# -*- coding: utf-8 -*-
"""Merger seed PostgreSQL + AdministraNET read-only para licenciatarios."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from django.db.models import QuerySet

from core.utils.administranet_types import to_decimal_or_none
from reports.models import (
    MonthlyReportingClientMatch,
    MonthlyReportingPack,
    MonthlyReportingSeedRow,
)
from reports.services.monthly_reporting_client_match_service import (
    match_to_aggregate_row,
    resolve_client_identity,
)
from reports.services.ventas_mensuales_licenciatarios_query import (
    AnetSalesRow,
    aggregate_anet_rows,
    fetch_anet_sales,
)

CUTOVER_DATE = date(2026, 7, 22)
CUTOVER_YEAR = CUTOVER_DATE.year


@dataclass
class MergedClientMonth:
    identity: str
    display_name: str
    match_estado: str
    month: date
    units: Decimal
    amount: Decimal
    units_men: Decimal = Decimal("0")
    units_women: Decimal = Decimal("0")
    amount_men: Decimal = Decimal("0")
    amount_women: Decimal = Decimal("0")
    source: str = "seed"
    pending: bool = False
    anet_cliente_id: Optional[int] = None


@dataclass
class MergeResult:
    rows: List[MergedClientMonth] = field(default_factory=list)
    ytd_by_identity: Dict[str, Dict[str, Decimal]] = field(default_factory=dict)
    pending_clients: List[dict] = field(default_factory=list)
    qa_superarts: List[str] = field(default_factory=list)


def anet_range_for_month(year: int, month: int) -> Optional[tuple[date, date]]:
    """Rango ANET según cutover 21/22 julio 2026."""
    if year < CUTOVER_YEAR:
        return None
    if year > CUTOVER_YEAR:
        first = date(year, month, 1)
        if month == 12:
            last = date(year, 12, 31)
        else:
            last = date(year, month + 1, 1) - timedelta(days=1)
        return first, last
    # año cutover 2026
    if month < 7:
        return None
    if month == 7:
        return date(2026, 7, 22), date(2026, 7, 31)
    first = date(year, month, 1)
    if month == 12:
        return first, date(year, 12, 31)
    next_month = date(year, month + 1, 1)
    last = next_month - timedelta(days=1)
    return first, last


def seed_months_in_range(year: int, month_from: int, month_to: int) -> List[int]:
    """Meses que aportan seed en el rango (ene–jun; jul parcial vía fila seed)."""
    months: List[int] = []
    for month in range(month_from, month_to + 1):
        if year < CUTOVER_YEAR:
            months.append(month)
        elif year == CUTOVER_YEAR and month <= 7:
            months.append(month)
    return months


def load_seed_rows(
    pack: MonthlyReportingPack,
    year: int,
    months: Sequence[int],
) -> QuerySet[MonthlyReportingSeedRow]:
    month_dates = [date(year, m, 1) for m in months]
    return (
        MonthlyReportingSeedRow.objects.filter(pack=pack, month__in=month_dates)
        .select_related("match")
    )


def seed_row_to_merged(row: MonthlyReportingSeedRow, base_empresa: str) -> MergedClientMonth:
    match = row.match
    meta = match_to_aggregate_row(match, base_empresa)
    return MergedClientMonth(
        identity=meta["identity"],
        display_name=meta["display_name"],
        match_estado=meta["match_estado"],
        month=row.month,
        units=row.units,
        amount=row.amount,
        units_men=row.units_men,
        units_women=row.units_women,
        amount_men=row.amount_men,
        amount_women=row.amount_women,
        source="seed",
        pending=meta["pending"],
        anet_cliente_id=match.anet_cliente_id,
    )


def anet_row_to_merged(
    row: AnetSalesRow,
    *,
    base_empresa: str,
    match: Optional[MonthlyReportingClientMatch] = None,
) -> MergedClientMonth:
    if match and match.estado == MonthlyReportingClientMatch.Estado.MATCHED:
        identity = resolve_client_identity(match, base_empresa)
        display_name = match.seed_customer_name or row.nombre_cliente
        match_estado = match.estado
        pending = False
    else:
        identity = f"anet:{base_empresa}:{row.codigo_cliente}"
        display_name = row.nombre_cliente
        match_estado = "anet_only"
        pending = False
    return MergedClientMonth(
        identity=identity,
        display_name=display_name,
        match_estado=match_estado,
        month=row.month,
        units=row.units,
        amount=row.amount,
        units_men=row.units_men,
        units_women=row.units_women,
        amount_men=row.amount_men,
        amount_women=row.amount_women,
        source="anet",
        pending=pending,
        anet_cliente_id=row.codigo_cliente,
    )


def _add_row(acc: dict[tuple[str, date], MergedClientMonth], row: MergedClientMonth) -> None:
    key = (row.identity, row.month)
    prev = acc.get(key)
    if prev is None:
        acc[key] = row
        return
    acc[key] = MergedClientMonth(
        identity=prev.identity,
        display_name=prev.display_name,
        match_estado=prev.match_estado,
        month=prev.month,
        units=prev.units + row.units,
        amount=prev.amount + row.amount,
        units_men=prev.units_men + row.units_men,
        units_women=prev.units_women + row.units_women,
        amount_men=prev.amount_men + row.amount_men,
        amount_women=prev.amount_women + row.amount_women,
        source="merged" if prev.source != row.source else prev.source,
        pending=prev.pending or row.pending,
        anet_cliente_id=prev.anet_cliente_id or row.anet_cliente_id,
    )


def compute_ytd(rows: Iterable[MergedClientMonth]) -> Dict[str, Dict[str, Decimal]]:
    ytd: Dict[str, Dict[str, Decimal]] = {}
    for row in sorted(rows, key=lambda r: (r.identity, r.month)):
        bucket = ytd.setdefault(
            row.identity,
            {
                "units": Decimal("0"),
                "amount": Decimal("0"),
                "units_men": Decimal("0"),
                "units_women": Decimal("0"),
                "amount_men": Decimal("0"),
                "amount_women": Decimal("0"),
            },
        )
        bucket["units"] += row.units
        bucket["amount"] += row.amount
        bucket["units_men"] += row.units_men
        bucket["units_women"] += row.units_women
        bucket["amount_men"] += row.amount_men
        bucket["amount_women"] += row.amount_women
    return ytd


def merge_pack_year(
    *,
    pack: MonthlyReportingPack,
    year: int,
    month_from: int = 1,
    month_to: int = 12,
    base_empresa: str,
    fetch_anet_fn: Callable[..., List[AnetSalesRow]] = fetch_anet_sales,
    classify_genero=None,
    register_unknown_superart=None,
) -> MergeResult:
    """
    Fusiona seed + ANET respetando cutover 22/07/2026.

    Ene–jun: seed. Julio: seed + ANET 22–31. Ago+: ANET.
    """
    acc: dict[tuple[str, date], MergedClientMonth] = {}
    pending_clients: dict[str, dict] = {}
    qa_superarts: set[str] = set()

    seed_months = seed_months_in_range(year, month_from, month_to)
    for seed_row in load_seed_rows(pack, year, seed_months):
        merged = seed_row_to_merged(seed_row, base_empresa)
        _add_row(acc, merged)
        if merged.pending:
            pending_clients[merged.identity] = match_to_aggregate_row(seed_row.match, base_empresa)

    matches_by_anet = {
        m.anet_cliente_id: m
        for m in MonthlyReportingClientMatch.objects.filter(
            estado=MonthlyReportingClientMatch.Estado.MATCHED,
            anet_cliente_id__isnull=False,
        )
    }

    def _qa_hook(superart: str, sample: Optional[dict] = None) -> None:
        key = (superart or "").strip()
        if key:
            qa_superarts.add(key)
        if register_unknown_superart:
            register_unknown_superart(superart, sample)

    for month in range(month_from, month_to + 1):
        anet_range = anet_range_for_month(year, month)
        if anet_range is None:
            continue
        d_from, d_to = anet_range
        anet_rows = fetch_anet_fn(
            base_empresa=base_empresa,
            pack=pack,
            date_from=d_from,
            date_to=d_to,
            classify_genero=classify_genero,
            register_unknown_superart=_qa_hook if classify_genero else register_unknown_superart,
        )
        for _key, agg in aggregate_anet_rows(anet_rows).items():
            match = matches_by_anet.get(agg.codigo_cliente)
            merged = anet_row_to_merged(agg, base_empresa=base_empresa, match=match)
            merged.month = date(year, month, 1)
            _add_row(acc, merged)

    rows = sorted(acc.values(), key=lambda r: (r.identity, r.month))
    ytd = compute_ytd(rows)
    return MergeResult(
        rows=rows,
        ytd_by_identity=ytd,
        pending_clients=list(pending_clients.values()),
        qa_superarts=sorted(qa_superarts),
    )


def compare_dz_pk_parity(
    dz_rows: Iterable[MergedClientMonth],
    pk_rows: Iterable[MergedClientMonth],
) -> dict[tuple[str, date], dict[str, Decimal]]:
    """
    Verifica paridad LEV DZ/PK: misma facturación; unidades pueden diferir por U.M.
    Retorna discrepancias de amount por identity×month.
    """
    dz_map = {(r.identity, r.month): r for r in dz_rows}
    pk_map = {(r.identity, r.month): r for r in pk_rows}
    discrepancies: dict[tuple[str, date], dict[str, Decimal]] = {}
    for key, dz in dz_map.items():
        pk = pk_map.get(key)
        if pk is None:
            continue
        if (dz.amount - pk.amount).copy_abs() > Decimal("0.01"):
            discrepancies[key] = {"dz": dz.amount, "pk": pk.amount}
    return discrepancies
