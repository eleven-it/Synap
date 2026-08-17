# -*- coding: utf-8 -*-
"""Runner híbrido — Ventas Mensuales Licenciatarios (seed + AdministraNET RO)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable, Dict, List, Optional

from django.conf import settings

from core.utils.administranet_types import str_or_default, to_date_or_none, to_int_or_none
from reports.models import MonthlyReportingPack
from reports.services.monthly_reporting_superart_service import (
    make_classify_fn,
    register_qa_pending,
)
from reports.services.query_runner import QueryResult
from reports.services.ventas_mensuales_licenciatarios_merger import (
    MergeResult,
    filter_merge_result_by_clientes_excluidos,
    merge_pack_year,
)
from reports.services.ventas_mensuales_licenciatarios_query import (
    AnetSalesRow,
    fetch_anet_sales,
)

CUTOVER_DATE = date(2026, 7, 22)


def _parse_filter_date(value: Any) -> Optional[date]:
    normalized = to_date_or_none(value)
    if not normalized:
        return None
    try:
        return datetime.strptime(normalized[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def validate_calendar_year_range(fecha_inicio: Any, fecha_fin: Any) -> tuple[int, int, int]:
    """
    Valida rango dentro de un único año calendario.

    Returns:
        (year, month_from, month_to)

    Raises:
        ValueError: si falta fecha, cruza años o inicio > fin.
    """
    d_start = _parse_filter_date(fecha_inicio)
    d_end = _parse_filter_date(fecha_fin)
    if not d_start or not d_end:
        raise ValueError("Debe indicar fecha inicio y fin de facturación.")
    if d_start.year != d_end.year:
        raise ValueError(
            "El rango debe estar dentro del mismo año calendario (01/01–31/12)."
        )
    if d_start > d_end:
        raise ValueError("La fecha inicio no puede ser posterior a la fecha fin.")
    return d_start.year, d_start.month, d_end.month


def _parse_clientes_excluidos_filters(filters: Dict[str, Any]) -> List[int]:
    raw = filters.get("clientes_excluidos", [])
    if isinstance(raw, str):
        raw = [raw] if raw.strip() else []
    elif not isinstance(raw, list):
        raw = []
    ids: List[int] = []
    for item in raw:
        parsed = to_int_or_none(item)
        if parsed is not None:
            ids.append(parsed)
    return ids


def _resolve_base_empresa(payload: Dict[str, Any], user=None) -> str:
    filters = payload.get("filters") or {}
    base = payload.get("base_empresa") or filters.get("base_empresa")
    if not base and user is not None and hasattr(user, "base_empresa"):
        base = getattr(user, "base_empresa", None)
    if not base:
        base = getattr(settings, "DEFAULT_BASE_EMPRESA", None)
    return str_or_default(base, "").strip()


def merged_to_dashboard_rows(
    merge_result: MergeResult,
    *,
    year: int,
    month_from: int,
    month_to: int,
) -> List[Dict[str, Any]]:
    """Convierte filas fusionadas a filas tabulares para dashboard/export."""
    out: List[Dict[str, Any]] = []
    for row in merge_result.rows:
        if row.month.year != year:
            continue
        if not (month_from <= row.month.month <= month_to):
            continue
        ytd = merge_result.ytd_by_identity.get(row.identity, {})
        out.append(
            {
                "identity": row.identity,
                "cliente": row.display_name,
                "mes": row.month.isoformat(),
                "anio_mes": f"{row.month.year}{row.month.month:02d}",
                "unidades": float(row.units),
                "facturacion": float(row.amount),
                "ytd_unidades": float(ytd.get("units", 0)),
                "ytd_facturacion": float(ytd.get("amount", 0)),
                "fuente": row.source,
                "pendiente": row.pending,
                "match_estado": row.match_estado,
            }
        )
    return out


def run_ventas_mensuales_licenciatarios(
    report,
    payload: Optional[Dict[str, Any]],
    user=None,
    *,
    fetch_anet_fn: Optional[Callable[..., List[AnetSalesRow]]] = None,
) -> QueryResult:
    """
    Ejecuta merger seed + ANET read-only para un pack y rango anual.

    Alcance global autorizado: no filtra por vendedor/sucursal.
    """
    payload = payload if isinstance(payload, dict) else {}
    filters = payload.get("filters") or {}
    pack_id = str_or_default(filters.get("pack_id"), "").strip()

    meta: Dict[str, Any] = {
        "slug": report.slug,
        "name": report.name,
        "category": getattr(report, "category", None),
        "version": getattr(report, "version", None),
        "extra": {
            "cutover_date": CUTOVER_DATE.isoformat(),
            "sibling_of": "ventas-marcas-mensual",
            "pack_id": pack_id or None,
        },
    }

    if not pack_id:
        return QueryResult(
            meta=meta,
            data=[],
            totals={},
            notes=["Debe seleccionar un pack licenciatario."],
        )

    fi = filters.get("fecha_inicio_facturacion")
    ff = filters.get("fecha_fin_facturacion")
    try:
        year, month_from, month_to = validate_calendar_year_range(fi, ff)
    except ValueError as exc:
        return QueryResult(meta=meta, data=[], totals={}, notes=[str(exc)])

    base_empresa = _resolve_base_empresa(payload, user)
    if not base_empresa:
        return QueryResult(
            meta=meta,
            data=[],
            totals={},
            notes=["No se pudo resolver base_empresa para consultar AdministraNET."],
        )

    try:
        pack = MonthlyReportingPack.objects.get(pack_id=pack_id, active=True)
    except MonthlyReportingPack.DoesNotExist:
        return QueryResult(
            meta=meta,
            data=[],
            totals={},
            notes=[f"Pack licenciatario no encontrado: {pack_id}"],
        )

    classify_fn = make_classify_fn()
    qa_collected: set[str] = set()

    def _register_unknown(superart: str, sample: Optional[dict] = None) -> None:
        key = str_or_default(superart, "").strip()
        if not key:
            return
        qa_collected.add(key)
        register_qa_pending(key, sample)

    fetch_fn = fetch_anet_fn or fetch_anet_sales
    merge_result = merge_pack_year(
        pack=pack,
        year=year,
        month_from=month_from,
        month_to=month_to,
        base_empresa=base_empresa,
        fetch_anet_fn=fetch_fn,
        classify_genero=classify_fn,
        register_unknown_superart=_register_unknown,
    )
    clientes_excluidos = _parse_clientes_excluidos_filters(filters)
    if clientes_excluidos:
        merge_result = filter_merge_result_by_clientes_excluidos(
            merge_result,
            clientes_excluidos,
            base_empresa=base_empresa,
        )
    qa_all = sorted(set(merge_result.qa_superarts) | qa_collected)

    data = merged_to_dashboard_rows(
        merge_result,
        year=year,
        month_from=month_from,
        month_to=month_to,
    )
    totals = {
        "unidades": sum(row["unidades"] for row in data),
        "facturacion": sum(row["facturacion"] for row in data),
    }

    notes: List[str] = []
    if clientes_excluidos:
        notes.append(f"Clientes excluidos: {len(clientes_excluidos)} cliente(s).")

    meta["filters_applied"] = {
        "pack_id": pack_id,
        "fecha_inicio_facturacion": str_or_default(fi, "")[:10],
        "fecha_fin_facturacion": str_or_default(ff, "")[:10],
        "base_empresa": base_empresa,
        "clientes_excluidos": clientes_excluidos,
    }
    meta["extra"].update(
        {
            "pack_id": pack_id,
            "year": year,
            "month_from": month_from,
            "month_to": month_to,
            "ytd_by_identity": {
                ident: {k: float(v) for k, v in bucket.items()}
                for ident, bucket in merge_result.ytd_by_identity.items()
            },
            "pending_clients": merge_result.pending_clients,
            "qa_superarts": qa_all,
            "pack_codigo_salida": pack.codigo_salida,
            "unit_mode": pack.unit_mode,
        }
    )

    return QueryResult(
        meta=meta,
        data=data,
        totals=totals,
        notes=notes,
        artifacts={"merge_result": merge_result},
    )
