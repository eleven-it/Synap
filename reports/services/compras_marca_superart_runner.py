# -*- coding: utf-8 -*-
"""Runner informe Compras por marca y SuperArtículo."""
from __future__ import annotations

import logging
from typing import Dict

from django.conf import settings

from reports.services.compras_marca_superart_query import consultar_compras_marca_superart
from reports.services.fabricados_superart_calcs import parse_filters_from_payload
from reports.services.informe_marca_superart_merge import merge_metric_prefixes
from reports.services.informe_marca_superart_periodo import (
    agregar_filas_marca_superart_periodo,
    totales_por_marca_tabla,
)
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
        filas = consultar_compras_marca_superart(
            base_empresa,
            meses=filtros["meses"],
            marcas_incluidos=filtros.get("marcas_incluidos") or None,
            marcas_excluidos=filtros.get("marcas_excluidos") or None,
            desde_iso=filtros.get("desde_iso"),
            hasta_iso=filtros.get("hasta_iso"),
        )
    except Exception as exc:
        logger.warning("run_compras_marca_superart %s: %s", base_empresa, exc, exc_info=True)
        return QueryResult(
            meta=meta_base,
            data=[],
            totals={},
            notes=[f"Error al consultar compras: {exc}"],
        )

    ctx_packs = agregar_filas_marca_superart_periodo(
        filas, filtros["meses"], metric_prefix="Packs", metric_field="packs"
    )
    ctx_prendas = agregar_filas_marca_superart_periodo(
        filas, filtros["meses"], metric_prefix="Prendas", metric_field="prendas"
    )
    ctx_doc = agregar_filas_marca_superart_periodo(
        filas, filtros["meses"], metric_prefix="Docenas", metric_field="docenas"
    )
    arbol = merge_metric_prefixes(
        ctx_packs.get("marca_superart_jerarquia") or [],
        [
            ("Prendas", ctx_prendas.get("marca_superart_jerarquia") or []),
            ("Docenas", ctx_doc.get("marca_superart_jerarquia") or []),
        ],
    )
    totales_marca = totales_por_marca_tabla(arbol, "Packs")
    tp = ctx_packs.get("totales_generales") or {}
    tpr = ctx_prendas.get("totales_generales") or {}
    td = ctx_doc.get("totales_generales") or {}

    return QueryResult(
        meta={
            **meta_base,
            "extra": {
                "tabs": {
                    "marca_superart_jerarquia": arbol,
                    "totales_por_marca": totales_marca,
                },
                "totales_generales": {**tp, **tpr, **td},
                "filtros": filtros,
            },
            "filters_applied": filtros,
        },
        data=[],
        totals={
            "packs_total": tp.get("Packs_Total", 0),
            "prendas_total": tpr.get("Prendas_Total", 0),
            "docenas_total": td.get("Docenas_Total", 0),
        },
        notes=[],
    )
