# -*- coding: utf-8 -*-
"""Runner informe Compras por marca y SuperArtículo (reports app)."""
from __future__ import annotations

import logging
from typing import Any, Dict

from django.conf import settings

from reports.services.compras_marca_superart_calcs import (
    build_totals_planos,
    flatten_filas_superart_por_marca,
    parse_filters_from_payload,
    preparar_compras_marca_superart_presentacion,
)
from reports.services.compras_marca_superart_query import reporte_compras_marca_superart
from reports.services.query_runner import QueryResult

logger = logging.getLogger(__name__)


def run_compras_marca_superart(report, payload: Dict, user) -> QueryResult:
    meta_base = {
        "slug": report.slug,
        "name": report.name,
        "category": report.category,
        "version": report.version,
    }
    filters = payload.get("filters") or {}
    base_empresa = filters.get("base_empresa") or getattr(user, "base_empresa", None)
    if not base_empresa:
        base_empresa = getattr(settings, "DEFAULT_BASE_EMPRESA", None)
    if not base_empresa:
        return QueryResult(
            meta=meta_base,
            data=[],
            totals={},
            notes=["No se pudo determinar la base de datos de la empresa."],
        )

    filtros = parse_filters_from_payload(filters)

    try:
        raw = reporte_compras_marca_superart(
            base_empresa,
            meses=filtros["meses"],
            desde_iso=filtros["desde_iso"],
            hasta_iso=filtros["hasta_iso"],
            marcas_incluidos=filtros["marcas_incluidos"] or None,
            marcas_excluidos=filtros.get("marcas_excluidos") or None,
            superarts_incluidos=filtros["superarts_incluidos"] or None,
            superarts_excluidos=filtros.get("superarts_excluidos") or None,
        )
    except Exception as exc:
        logger.warning("run_compras_marca_superart %s: %s", base_empresa, exc, exc_info=True)
        return QueryResult(
            meta=meta_base,
            data=[],
            totals={},
            notes=[f"Error al consultar compras: {exc}"],
        )

    ctx = preparar_compras_marca_superart_presentacion(raw)
    totals = build_totals_planos(raw)
    filas_planas = flatten_filas_superart_por_marca(ctx.get("filas_marca") or [])

    notes = [
        "Compras: facturas FA/FC/FM y remitos de proveedor con entrada a stock, más ajustes MSTOCK en Terminado.",
        f"Período: {filtros.get('desde_iso')} — {filtros.get('hasta_iso')}.",
        f"Meses en columnas: {', '.join(filtros.get('meses') or [])}.",
        "Marcas: LB, PUS, PUW, RW (por CodigoMarca del artículo). Prendas = packs × unidades nU del nombre.",
    ]

    return QueryResult(
        meta={
            **meta_base,
            "extra": {
                "compras_marca_superart": ctx,
                "filtros_compras_marca_superart": filtros,
            },
            "filters_applied": {
                "desde": filtros.get("desde_iso"),
                "hasta": filtros.get("hasta_iso"),
                "marcas_incluidos": filtros.get("marcas_incluidos"),
                "superarts_incluidos": filtros.get("superarts_incluidos"),
                "marcas_excluidos": filtros.get("marcas_excluidos"),
                "superarts_excluidos": filtros.get("superarts_excluidos"),
            },
        },
        data=filas_planas,
        totals=totals,
        notes=notes,
    )
