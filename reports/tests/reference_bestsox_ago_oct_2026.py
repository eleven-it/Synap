# -*- coding: utf-8 -*-
"""Carga totales de referencia (Excel Ago–Oct 2026) para tests de paridad."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from mpr.services_fabricados_superart import etiqueta_mes

_FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "bestsox_ago_oct_2026_reference.json"


@lru_cache(maxsize=1)
def load_reference() -> Dict[str, Any]:
    with _FIXTURE_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def periodo_filtros() -> Dict[str, str]:
    p = load_reference()["periodo"]
    return {
        "desde": p["desde"],
        "hasta": p["hasta"],
        "corte_facturas": p.get("corte_facturas") or p["hasta"],
    }


def meses_periodo() -> List[str]:
    return ["2026-08", "2026-09", "2026-10"]


def mes_label(ym: str) -> str:
    return etiqueta_mes(ym).split(" ", 1)[0]


def metric_key(prefix: str, ym: str) -> str:
    return f"{prefix}_{mes_label(ym)}"


def filas_sql_produccion() -> List[Dict[str, Any]]:
    return list(load_reference()["produccion"]["filas_sql"])


def filas_sql_compras() -> List[Dict[str, Any]]:
    return list(load_reference()["compras"]["filas_sql"])


def filas_sql_consignacion() -> List[Dict[str, Any]]:
    return list(load_reference()["consignacion"]["filas_sql"])
