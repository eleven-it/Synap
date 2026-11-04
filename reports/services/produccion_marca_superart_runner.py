# -*- coding: utf-8 -*-
"""Runner informe Producción por marca y SuperArtículo."""
from __future__ import annotations

import logging
from typing import Any, Dict

from django.conf import settings

from reports.services.fabricados_superart_calcs import parse_filters_from_payload
from reports.services.informe_marca_superart_merge import add_docenas_from_pares_arbol
from reports.services.informe_marca_superart_periodo import (
    agregar_filas_marca_superart_periodo,
    totales_por_marca_tabla,
)
from reports.services.produccion_marca_superart_query import consultar_produccion_marca_superart
from reports.services.query_runner import QueryResult

logger = logging.getLogger(__name__)


def run_produccion_marca_superart(report, payload: Dict, user) -> QueryResult:
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
        filas = consultar_produccion_marca_superart(
            base_empresa,
            meses=filtros["meses"],
            marcas_incluidos=filtros.get("marcas_incluidos") or None,
            marcas_excluidos=filtros.get("marcas_excluidos") or None,
            desde_iso=filtros.get("desde_iso"),
            hasta_iso=filtros.get("hasta_iso"),
        )
    except Exception as exc:
        logger.error(
            "run_produccion_marca_superart %s: %s",
            base_empresa,
            exc,
            exc_info=True,
        )
        return QueryResult(
            meta=meta_base,
            data=[],
            totals={},
            notes=[f"Error al consultar producción: {exc}"],
        )

    ctx = agregar_filas_marca_superart_periodo(
        filas,
        filtros["meses"],
        metric_prefix="Pares",
        metric_field="cantidad",
        fuente_field="fuente",
    )
    arbol = ctx.get("marca_superart_jerarquia") or []
    add_docenas_from_pares_arbol(arbol, ctx.get("meses") or [], ctx.get("mes_labels") or {})
    totales_marca = totales_por_marca_tabla(arbol, "Pares")
    tot_gen = ctx.get("totales_generales") or {}

    return QueryResult(
        meta={
            **meta_base,
            "extra": {
                "tabs": {
                    "marca_superart_jerarquia": arbol,
                    "totales_por_marca": totales_marca,
                },
                "totales_generales": tot_gen,
                "filtros": filtros,
            },
            "filters_applied": filtros,
        },
        data=[],
        totals={
            "pares_total": tot_gen.get("Pares_Total", 0),
            "docenas_total": round(float(tot_gen.get("Pares_Total", 0) or 0) / 12.0, 4),
        },
        notes=[],
    )
