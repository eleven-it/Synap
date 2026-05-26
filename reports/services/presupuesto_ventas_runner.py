# -*- coding: utf-8 -*-
"""Dataset operativo «documento presupuesto ventas»: cabecera `comp_ped` + renglones `stockp`."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict

from django.conf import settings

from core.utils.administranet_types import to_int_or_none
from ventas.services.presupuesto_mysql import (
    listar_lineas_presupuesto_stockp,
    obtener_presupuesto_cabecera,
)

from .query_runner import QueryResult


def _fmt_fecha(d: Any) -> str:
    if d is None:
        return "—"
    if isinstance(d, datetime):
        d = d.date()
    if isinstance(d, date):
        return d.strftime("%d/%m/%Y")
    return str(d)


def _decimal_sum(rows: list, key: str) -> Decimal:
    total = Decimal("0")
    for r in rows:
        v = r.get(key)
        if v is None:
            continue
        if isinstance(v, Decimal):
            total += v
        else:
            try:
                total += Decimal(str(v))
            except Exception:
                continue
    return total


def run_documento_presupuesto_ventas(report, payload: Dict, user) -> QueryResult:
    """
    Ejecuta el informe documento-presupuesto-ventas.
    Filtros requeridos: base_empresa, codigo_movimiento (en filters o raíz del payload).
    """
    filters = payload.get("filters") or {}
    base_empresa = (filters.get("base_empresa") or payload.get("base_empresa") or "").strip()
    if not base_empresa and hasattr(user, "base_empresa"):
        base_empresa = (getattr(user, "base_empresa", None) or "").strip()
    if not base_empresa:
        base_empresa = (getattr(settings, "DEFAULT_BASE_EMPRESA", None) or "").strip()

    raw_cm = filters.get("codigo_movimiento")
    if raw_cm is None:
        raw_cm = payload.get("codigo_movimiento")
    codigo_movimiento = to_int_or_none(raw_cm)

    meta_base = {
        "slug": report.slug,
        "name": report.name,
        "category": report.category,
        "base_empresa": base_empresa or "",
    }

    if not base_empresa or codigo_movimiento is None or int(codigo_movimiento) <= 0:
        return QueryResult(
            meta={**meta_base, "cabecera": {}},
            data=[],
            totals={},
            notes=[
                "Indique base empresa y código de movimiento válidos para generar el documento.",
            ],
        )

    cm = int(codigo_movimiento)
    ok_cab, err_cab, cab = obtener_presupuesto_cabecera(base_empresa, cm)
    if not ok_cab or not cab:
        return QueryResult(
            meta={**meta_base, "cabecera": {}},
            data=[],
            totals={},
            notes=[err_cab or "No se encontró el presupuesto."],
        )

    ok_ln, err_ln, lineas = listar_lineas_presupuesto_stockp(base_empresa, cm)
    if not ok_ln:
        lineas = []
        notes_extra = err_ln or ""
    else:
        notes_extra = ""

    cab_display = {
        **cab,
        "fecha_fmt": _fmt_fecha(cab.get("fecha")),
        "vencimiento_fmt": _fmt_fecha(cab.get("vencimiento")),
    }

    filas_export: list[Dict[str, Any]] = []
    for ln in lineas:
        filas_export.append(
            {
                "orden": ln.get("orden"),
                "codigo_articulo": ln.get("codigo_articulo") or "",
                "descripcion": ln.get("descripcion") or "",
                "cantidad": ln.get("cantidad"),
                "precio_unitario": ln.get("precio_unitario"),
                "precio_neto_renglon": ln.get("precio_neto_renglon"),
                "precio_venta_renglon": ln.get("precio_venta_renglon"),
                "cod_deposito": ln.get("cod_deposito"),
                "detalle_renglon": ln.get("detalle_renglon") or "",
            }
        )

    sum_neto = _decimal_sum(filas_export, "precio_neto_renglon")
    sum_venta = _decimal_sum(filas_export, "precio_venta_renglon")
    sum_cant = _decimal_sum(filas_export, "cantidad")

    iv = cab.get("importe_venta")
    try:
        importe_cab = float(iv) if iv is not None else 0.0
    except (TypeError, ValueError):
        importe_cab = 0.0

    totals = {
        "suma_precio_neto_renglon": float(sum_neto),
        "suma_precio_venta_renglon": float(sum_venta),
        "suma_cantidad": float(sum_cant),
        "importe_cabecera_comp_ped": importe_cab,
    }

    nro = cab.get("nro_comprobante") or ""
    notes = [
        f"Presupuesto {nro} · Movimiento {cm} · Cliente {cab_display.get('nombre_cliente') or '—'}",
    ]
    if notes_extra:
        notes.append(f"Aviso renglones: {notes_extra}")

    meta = {
        **meta_base,
        "cabecera": cab_display,
        "codigo_movimiento": cm,
    }

    return QueryResult(meta=meta, data=filas_export, totals=totals, notes=notes)
