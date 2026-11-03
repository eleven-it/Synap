# -*- coding: utf-8 -*-
"""Runner informe Stock en consignación."""
from __future__ import annotations

import logging
from datetime import date
from typing import Dict

from django.conf import settings

from reports.services.consignacion_stock_presentacion import (
    nest_consignacion_cliente_marca,
    totales_marca_consignacion,
)
from reports.services.consignacion_stock_query import consultar_consignacion_stock
from reports.services.fabricados_superart_calcs import parse_filters_from_payload
from reports.services.query_runner import QueryResult

logger = logging.getLogger(__name__)


def run_consignacion_stock(report, payload: Dict, user) -> QueryResult:
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
    corte = (filters.get("corte_facturas") or filtros.get("hasta_iso") or "").strip()
    if not corte:
        corte = date.today().isoformat()

    try:
        raw = consultar_consignacion_stock(
            base_empresa,
            remito_desde_iso=filtros.get("desde_iso"),
            remito_hasta_iso=filtros.get("hasta_iso"),
            corte_facturas_iso=corte,
        )
    except Exception as exc:
        logger.warning("run_consignacion_stock %s: %s", base_empresa, exc, exc_info=True)
        return QueryResult(
            meta=meta_base,
            data=[],
            totals={},
            notes=[f"Error al consultar consignación: {exc}"],
        )

    filas = raw.get("filas_articulo") or []
    jerarquia = nest_consignacion_cliente_marca(filas)
    tot_marca = totales_marca_consignacion(filas)
    tot = raw.get("totales") or {}

    return QueryResult(
        meta={
            **meta_base,
            "extra": {
                "tabs": {
                    "consignacion_jerarquia": jerarquia,
                    "totales_por_marca": tot_marca,
                    "remitos": raw.get("remitos") or [],
                },
                "totales_generales": tot,
                "filtros": {**filtros, "corte_facturas": corte},
            },
            "filters_applied": {**filtros, "corte_facturas": corte},
        },
        data=[],
        totals=tot,
        notes=[],
    )
