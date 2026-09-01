# -*- coding: utf-8 -*-
"""Merger seed PostgreSQL + AdministraNET read-only para licenciatarios."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from django.db.models import QuerySet

from core.utils.administranet_types import str_or_default, to_decimal_or_none, to_int_or_none
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


_NAME_NON_ALNUM = re.compile(r"[^A-Z0-9]+")


def _normalize_customer_name(value: str) -> str:
    """Clave estable para vincular ANET ↔ seed cuando el match aún no tiene anet_id.

    Ignora puntuación (p. ej. «S.A.» vs «S.A») y colapsa espacios para homónimos
    tipo VARTAT: seed pendiente + venta ANET con el mismo nombre comercial.
    """
    cleaned = _NAME_NON_ALNUM.sub(" ", str(value or "").upper())
    return " ".join(cleaned.split())


def _build_match_indexes() -> tuple[
    dict[int, MonthlyReportingClientMatch],
    dict[str, MonthlyReportingClientMatch],
]:
    """
    Índices para resolver match de filas ANET.

    1) por codigo AdministraNET (matcheados)
    2) por nombre normalizado (pendientes o matcheados) — evita filas duplicadas
       tipo VARTAT: seed pendiente + ANET julio con el mismo display_name.
    """
    by_anet: dict[int, MonthlyReportingClientMatch] = {}
    by_name: dict[str, MonthlyReportingClientMatch] = {}
    qs = MonthlyReportingClientMatch.objects.all().order_by("id")
    for match in qs:
        name_key = _normalize_customer_name(match.seed_customer_name)
        if name_key and name_key not in by_name:
            by_name[name_key] = match
        if match.estado == MonthlyReportingClientMatch.Estado.MATCHED:
            anet_id = to_int_or_none(match.anet_cliente_id)
            if anet_id is not None:
                by_anet[anet_id] = match
            # Matcheado gana sobre pendiente homónimo.
            if name_key:
                by_name[name_key] = match
    return by_anet, by_name


def resolve_anet_match(
    *,
    codigo_cliente: int,
    nombre_cliente: str,
    matches_by_anet: dict[int, MonthlyReportingClientMatch],
    matches_by_name: dict[str, MonthlyReportingClientMatch],
) -> Optional[MonthlyReportingClientMatch]:
    anet_id = to_int_or_none(codigo_cliente)
    if anet_id is not None and anet_id in matches_by_anet:
        return matches_by_anet[anet_id]
    name_key = _normalize_customer_name(nombre_cliente)
    if name_key:
        return matches_by_name.get(name_key)
    return None


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
    city: str = ""
    store_type: str = ""
    product_group: str = ""


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
        city=(row.city or match.seed_city or "").strip(),
        store_type=(row.store_type or match.seed_store_type or "").strip(),
        product_group=(match.seed_product_group or "").strip(),
    )


def anet_row_to_merged(
    row: AnetSalesRow,
    *,
    base_empresa: str,
    match: Optional[MonthlyReportingClientMatch] = None,
) -> MergedClientMonth:
    if match is not None:
        identity = resolve_client_identity(match, base_empresa)
        display_name = match.seed_customer_name or row.nombre_cliente
        match_estado = match.estado
        pending = match.estado == MonthlyReportingClientMatch.Estado.PENDING
        city = (match.seed_city or "").strip()
        store_type = (match.seed_store_type or "").strip()
        product_group = (match.seed_product_group or "").strip()
        anet_cliente_id = match.anet_cliente_id or row.codigo_cliente
    else:
        identity = f"anet:{base_empresa}:{row.codigo_cliente}"
        display_name = row.nombre_cliente
        match_estado = "anet_only"
        pending = False
        city = ""
        store_type = ""
        product_group = ""
        anet_cliente_id = row.codigo_cliente
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
        anet_cliente_id=anet_cliente_id,
        city=city,
        store_type=store_type,
        product_group=product_group,
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
        city=prev.city or row.city,
        store_type=prev.store_type or row.store_type,
        product_group=prev.product_group or row.product_group,
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


def _parse_clientes_excluidos_ids(clientes_excluidos: Sequence) -> set[int]:
    excluded: set[int] = set()
    for raw in clientes_excluidos or []:
        parsed = to_int_or_none(raw)
        if parsed is not None:
            excluded.add(parsed)
    return excluded


def filter_merge_result_by_clientes_excluidos(
    merge_result: MergeResult,
    clientes_excluidos: Sequence,
    *,
    base_empresa: str = "",
) -> MergeResult:
    """
    Excluye clientes AdministraNET del merge (filas seed matcheadas, ANET-only e identidades).

    Recalcula YTD y pending_clients solo con filas restantes.
    """
    excluded_ids = _parse_clientes_excluidos_ids(clientes_excluidos)
    if not excluded_ids:
        return merge_result

    base = (base_empresa or "default").strip()
    excluded_identities: set[str] = {f"anet:{base}:{anet_id}" for anet_id in excluded_ids}
    excluded_seed_keys: set[str] = set()

    for match in MonthlyReportingClientMatch.objects.filter(anet_cliente_id__in=excluded_ids):
        excluded_seed_keys.add(match.seed_key)
        excluded_identities.add(f"seed:{match.seed_key}")
        excluded_identities.add(resolve_client_identity(match, base_empresa))

    def _row_excluded(row: MergedClientMonth) -> bool:
        anet_id = to_int_or_none(row.anet_cliente_id)
        if anet_id is not None and anet_id in excluded_ids:
            return True
        if row.identity in excluded_identities:
            return True
        if row.identity.startswith("seed:"):
            seed_key = row.identity[5:]
            if seed_key in excluded_seed_keys:
                return True
        if row.identity.startswith("anet:"):
            parts = row.identity.split(":")
            if len(parts) >= 3 and to_int_or_none(parts[-1]) in excluded_ids:
                return True
        return False

    def _pending_excluded(pending: dict) -> bool:
        anet_id = to_int_or_none(pending.get("anet_cliente_id"))
        if anet_id is not None and anet_id in excluded_ids:
            return True
        identity = str_or_default(pending.get("identity"), "")
        if identity in excluded_identities:
            return True
        seed_key = str_or_default(pending.get("seed_key"), "")
        return bool(seed_key and seed_key in excluded_seed_keys)

    filtered_rows = [row for row in merge_result.rows if not _row_excluded(row)]
    filtered_pending = [
        pending for pending in merge_result.pending_clients if not _pending_excluded(pending)
    ]
    return MergeResult(
        rows=filtered_rows,
        ytd_by_identity=compute_ytd(filtered_rows),
        pending_clients=filtered_pending,
        qa_superarts=merge_result.qa_superarts,
    )


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
    sucursales: Optional[Sequence[int]] = None,
    puntos_venta: Optional[Sequence[int]] = None,
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

    matches_by_anet, matches_by_name = _build_match_indexes()

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
            sucursales=sucursales,
            puntos_venta=puntos_venta,
            classify_genero=classify_genero,
            register_unknown_superart=_qa_hook if classify_genero else register_unknown_superart,
        )
        for _key, agg in aggregate_anet_rows(anet_rows).items():
            match = resolve_anet_match(
                codigo_cliente=agg.codigo_cliente,
                nombre_cliente=agg.nombre_cliente,
                matches_by_anet=matches_by_anet,
                matches_by_name=matches_by_name,
            )
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
