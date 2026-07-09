# -*- coding: utf-8 -*-
"""Runner Reports — evolución / ranking de precios (precios_historial)."""

from __future__ import annotations

from typing import Any, Dict

from django.conf import settings

from core.utils.administranet_types import to_date_or_none, to_int_or_none
from ventas.services.precios_historial import (
    HistorialPreciosFiltros,
    ranking_variaciones_precios,
)

from .query_runner import QueryResult


def _base_empresa_from_payload(payload: Dict, user) -> str:
    filters = payload.get("filters") or {}
    base = (filters.get("base_empresa") or payload.get("base_empresa") or "").strip()
    if not base and hasattr(user, "base_empresa"):
        base = (getattr(user, "base_empresa", None) or "").strip()
    if not base:
        base = (getattr(settings, "DEFAULT_BASE_EMPRESA", None) or "").strip()
    return base


def _filtros_desde_payload(payload: Dict) -> HistorialPreciosFiltros:
    filters = payload.get("filters") or payload
    lista = to_int_or_none(filters.get("lista")) or 1
    limit = to_int_or_none(filters.get("limit")) or 50
    solo_synap = str(filters.get("solo_synap") or "").strip().lower() in ("1", "true", "si", "sí")

    def _ints(key: str) -> list:
        raw = filters.get(key)
        if raw is None:
            return []
        if isinstance(raw, list):
            vals = raw
        else:
            vals = [raw]
        out = []
        for v in vals:
            n = to_int_or_none(v)
            if n is not None and n not in out:
                out.append(n)
        return out

    return HistorialPreciosFiltros(
        lista=lista,
        fecha_desde=to_date_or_none(filters.get("fecha_desde")),
        fecha_hasta=to_date_or_none(filters.get("fecha_hasta")),
        rubros_incluidos=_ints("rubros_incluidos"),
        marcas_incluidos=_ints("marcas_incluidos"),
        proveedores_incluidos=_ints("proveedores_incluidos"),
        solo_synap=solo_synap,
        tipo_modificacion=(filters.get("tipo_modificacion") or "").strip() or None,
        limit=limit,
    )


def run_evolucion_precios(report, payload: Dict, user) -> QueryResult:
    """Ejecuta informe evolucion-precios (ranking variación % neto)."""
    base_empresa = _base_empresa_from_payload(payload, user)
    filtros = _filtros_desde_payload(payload)
    meta_base = {
        "slug": report.slug,
        "name": report.name,
        "category": report.category,
        "base_empresa": base_empresa or "",
    }
    if not base_empresa:
        return QueryResult(
            meta=meta_base,
            data=[],
            totals={},
            notes=["Indique base empresa para consultar el histórico de precios."],
        )

    resultado = ranking_variaciones_precios(base_empresa, filtros)
    if resultado.get("error"):
        return QueryResult(
            meta={**meta_base, **{k: resultado[k] for k in ("fecha_desde", "fecha_hasta", "lista") if k in resultado}},
            data=[],
            totals={},
            notes=[f"Error: {resultado['error']}"],
        )

    filas = resultado.get("filas") or []
    data = [
        {
            "id_articulo": r.get("id_articulo"),
            "id_manual": r.get("id_manual"),
            "nombre_articulo": r.get("nombre_articulo"),
            "nombre_rubro": r.get("nombre_rubro"),
            "nombre_marca": r.get("nombre_marca"),
            "neto_inicial": r.get("neto_inicial"),
            "neto_final": r.get("neto_final"),
            "variacion_pct": r.get("variacion_pct"),
            "cantidad_registros": r.get("cantidad_registros"),
            "ultimo_tipo_modificacion": r.get("ultimo_tipo_modificacion"),
        }
        for r in filas
    ]
    totals = resultado.get("totals") or {}
    notes = [
        f"Período {resultado.get('fecha_desde')} — {resultado.get('fecha_hasta')}",
        f"Lista {resultado.get('lista')}",
        "Variación % = (último neto − primer neto) / primer neto en el rango.",
    ]
    return QueryResult(
        meta={
            **meta_base,
            "fecha_desde": resultado.get("fecha_desde"),
            "fecha_hasta": resultado.get("fecha_hasta"),
            "lista": resultado.get("lista"),
        },
        data=data,
        totals={k: float(v) if v is not None else 0.0 for k, v in totals.items()},
        notes=notes,
    )
