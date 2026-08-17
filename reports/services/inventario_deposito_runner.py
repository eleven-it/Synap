# -*- coding: utf-8 -*-
"""Runner Reports — Inventario por depósito (motor MPR)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from django.conf import settings

from core.utils.administranet_types import str_or_default, to_date_or_none
from mpr.services_inventario_deposito import (
    consultar_inventario_deposito,
    parse_filtros_inventario_deposito,
)

from .query_runner import QueryResult


class _FilterParams:
    """Adaptador dict → interfaz esperada por parse_filtros_inventario_deposito."""

    def __init__(self, data: Dict[str, Any]):
        self._data = data or {}

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def getlist(self, key: str) -> List[Any]:
        val = self._data.get(key)
        if val is None:
            return []
        if isinstance(val, list):
            return val
        return [val]


def _resolve_base_empresa(payload: Dict[str, Any], user=None) -> str:
    filters = payload.get("filters") or {}
    base = payload.get("base_empresa") or filters.get("base_empresa")
    if not base and user is not None and hasattr(user, "base_empresa"):
        base = getattr(user, "base_empresa", None)
    if not base:
        base = getattr(settings, "DEFAULT_BASE_EMPRESA", None)
    return str_or_default(base, "").strip()


def _normalize_filters_dict(filters: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza tipos del payload Reports antes de parse_filtros_inventario_deposito."""
    out = dict(filters or {})
    raw_fecha = out.get("fecha_corte")
    if raw_fecha:
        normalized = to_date_or_none(raw_fecha)
        if normalized:
            out["fecha_corte"] = normalized[:10]

    incluir = out.get("incluir_2da")
    if isinstance(incluir, bool):
        out["incluir_2da"] = "1" if incluir else "0"
    elif incluir is not None:
        out["incluir_2da"] = str(incluir).strip()

    q = out.get("q")
    if q is not None:
        out["q"] = str(q).strip()

    return out


def _marcas_getlist(filters: Dict[str, Any]) -> Optional[List[str]]:
    raw = filters.get("marcas_incluidos")
    if raw is None:
        return None
    if isinstance(raw, list):
        return [str(m) for m in raw]
    return [str(raw)]


def _parse_filtros_from_payload(payload: Dict[str, Any]):
    filters = _normalize_filters_dict(payload.get("filters") or {})
    return parse_filtros_inventario_deposito(
        _FilterParams(filters),
        marcas_getlist=_marcas_getlist(filters),
    )


def generar_inventario_deposito_xlsx_archivo(
    file_path: Path,
    filas: List[Dict[str, Any]],
    *,
    total_docenas: float,
    fecha_corte: Optional[date] = None,
    titulo: str = "Inventario por depósito",
) -> None:
    """Escribe Excel reutilizando la lógica MPR (exportar_inventario_deposito_xlsx)."""
    from mpr.export import exportar_inventario_deposito_xlsx

    response = exportar_inventario_deposito_xlsx(
        filas,
        total_docenas=total_docenas,
        fecha_corte=fecha_corte,
        titulo=titulo,
    )
    file_path.write_bytes(response.content)


def run_inventario_deposito(report, payload: Dict[str, Any], user=None) -> QueryResult:
    """Ejecuta consulta inventario-deposito-articulo vía motor MPR."""
    payload = payload if isinstance(payload, dict) else {}
    filtros = _parse_filtros_from_payload(payload)
    base_empresa = _resolve_base_empresa(payload, user)

    meta: Dict[str, Any] = {
        "slug": report.slug,
        "name": report.name,
        "category": getattr(report, "category", None),
        "version": getattr(report, "version", None),
        "fecha_corte": filtros.fecha_corte.isoformat(),
        "fecha_corte_display": filtros.fecha_corte.strftime("%d/%m/%Y"),
        "depositos_jerarquia": [],
        "usa_stock_deposito": True,
    }

    if not base_empresa:
        return QueryResult(
            meta=meta,
            data=[],
            totals={"total_docenas": 0.0, "depositos": 0, "filas": 0},
            notes=["No se pudo resolver base_empresa para consultar AdministraNET."],
        )

    resultado = consultar_inventario_deposito(base_empresa, filtros)
    filas = resultado.get("filas") or []
    kpis = resultado.get("kpis") or {}
    fecha_corte = resultado.get("fecha_corte") or filtros.fecha_corte

    meta["depositos_jerarquia"] = resultado.get("depositos_jerarquia") or []
    meta["usa_stock_deposito"] = bool(resultado.get("usa_stock_deposito", True))
    if isinstance(fecha_corte, date):
        meta["fecha_corte"] = fecha_corte.isoformat()
        meta["fecha_corte_display"] = fecha_corte.strftime("%d/%m/%Y")

    totals = {
        "total_docenas": float(kpis.get("total_docenas") or resultado.get("total_docenas") or 0),
        "depositos": int(kpis.get("depositos") or 0),
        "filas": int(kpis.get("filas") or len(filas)),
    }

    notes: List[str] = [f"Base: {base_empresa}"]
    if not meta["usa_stock_deposito"]:
        notes.append(
            "Fecha de corte distinta de hoy: stock calculado con saldos históricos."
        )

    return QueryResult(meta=meta, data=filas, totals=totals, notes=notes)
