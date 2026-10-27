# -*- coding: utf-8 -*-
"""Runner informe Fabricados por superartículo (reports app)."""
from __future__ import annotations

import logging
from typing import Any, Dict

from django.conf import settings

from reports.services.fabricados_superart_calcs import parse_filters_from_payload
from reports.services.query_runner import QueryResult

logger = logging.getLogger(__name__)


def run_fabricados_superart(report, payload: Dict, user) -> QueryResult:
    from mpr.reportes_presentacion import preparar_fabricados_superart_presentacion
    from mpr.services_fabricados_superart import reporte_mpr_fabricados_superart

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
    modo = (filters.get("presentacion") or "docenas").strip() or "docenas"
    if modo not in ("docenas", "pares"):
        modo = "docenas"

    try:
        raw = reporte_mpr_fabricados_superart(
            base_empresa,
            meses=filtros["meses"],
            marcas_incluidos=filtros["marcas_incluidos"] or None,
            superarts_incluidos=filtros["superarts_incluidos"] or None,
        )
    except Exception as exc:
        logger.warning("run_fabricados_superart %s: %s", base_empresa, exc, exc_info=True)
        return QueryResult(
            meta=meta_base,
            data=[],
            totals={},
            notes=[f"Error al consultar fabricados: {exc}"],
        )

    fab_ctx = preparar_fabricados_superart_presentacion(raw, modo)
    kpis = fab_ctx.get("kpis") or {}
    filas = fab_ctx.get("filas_superart") or []

    return QueryResult(
        meta={
            **meta_base,
            "extra": {
                "fabricados": fab_ctx,
                "filtros_fabricados_superart": filtros,
                "modo_presentacion": modo,
            },
            "filters_applied": {
                "desde": filtros.get("desde_iso"),
                "hasta": filtros.get("hasta_iso"),
                "marcas_incluidos": filtros.get("marcas_incluidos"),
                "superarts_incluidos": filtros.get("superarts_incluidos"),
                "presentacion": modo,
            },
        },
        data=filas,
        totals={
            "total_general": fab_ctx.get("total_general", 0),
            "kpis": kpis,
        },
        notes=[
            "Fabricado de 1ra selección: transición Producción → Semi elaborado.",
            f"Período: {filtros.get('desde_iso')} — {filtros.get('hasta_iso')}.",
            f"Meses en columnas: {', '.join(filtros.get('meses') or [])}.",
        ],
    )
