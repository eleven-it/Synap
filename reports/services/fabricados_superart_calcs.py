# -*- coding: utf-8 -*-
"""Parseo de filtros del informe fabricados-superart (sin MySQL)."""
from __future__ import annotations

from typing import Any, Dict, List, Sequence

from django.http import QueryDict

from mpr.services_fabricados_superart import (
    parse_filtros_fabricados_superart,
    parse_superarts_incluidos_desde_get,
)


def _as_list(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw] if raw.strip() else []
    if isinstance(raw, (list, tuple)):
        return [str(x) for x in raw if str(x).strip()]
    return [str(raw)]


def parse_filters_from_payload(filters: Dict[str, Any]) -> Dict[str, Any]:
    """Convierte filtros del dashboard API a shape de parse_filtros_fabricados_superart."""
    qd = QueryDict(mutable=True)
    desde = (filters.get("desde") or filters.get("fecha_inicio") or filters.get("fecha_desde") or "").strip()
    hasta = (filters.get("hasta") or filters.get("fecha_fin") or filters.get("fecha_hasta") or "").strip()
    if desde:
        qd["desde"] = desde
    if hasta:
        qd["hasta"] = hasta
    marcas = filters.get("marcas_incluidos") or []
    for m in _as_list(marcas):
        qd.appendlist("marcas_incluidos", m)
    superarts = filters.get("q_superart") or filters.get("superarts_incluidos") or []
    for s in _as_list(superarts):
        for part in str(s).split(","):
            part = part.strip()
            if part:
                qd.appendlist("q_superart", part)
    for m in _as_list(filters.get("marcas_excluidos") or []):
        qd.appendlist("marcas_excluidos", m)
    for s in _as_list(filters.get("superarts_excluidos") or []):
        qd.appendlist("superarts_excluidos", s)
    return parse_filtros_fabricados_superart(
        qd,
        marcas_getlist=qd.getlist("marcas_incluidos"),
    )


def parse_superarts_from_query_params(get_params) -> List[str]:
    return parse_superarts_incluidos_desde_get(get_params)
