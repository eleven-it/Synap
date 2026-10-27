# -*- coding: utf-8 -*-
"""Consultas reutilizables sobre mpr_transicion_lote (sin alterar reportes existentes)."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence

from mpr.services import TIPO_MPR_PRODUCCION, TIPO_MPR_SEMI_ELABORADO

_YM_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def normalizar_meses_yyyy_mm(raw_meses: Optional[Sequence[str]]) -> List[str]:
    """Filtra y ordena meses válidos AAAA-MM."""
    out: List[str] = []
    seen: set[str] = set()
    for raw in raw_meses or []:
        part = str(raw or "").strip()
        if not part or not _YM_RE.match(part):
            continue
        if part not in seen:
            seen.add(part)
            out.append(part)
    return sorted(out)


def fetch_fabricado_primera_por_articulo_mes(
    cursor,
    meses_yyyy_mm: Sequence[str],
    *,
    marcas_ids: Optional[Sequence[int]] = None,
) -> List[Dict[str, Any]]:
    """
    Fabricado de 1ra selección: Produccion → SemiElaborado por mes de DATE(creado_en).
    Excluye 2da selección (otro tipo_destino).
    """
    meses = normalizar_meses_yyyy_mm(meses_yyyy_mm)
    if not meses:
        return []
    ph_meses = ",".join(["%s"] * len(meses))
    params: List[Any] = [TIPO_MPR_PRODUCCION, TIPO_MPR_SEMI_ELABORADO, *meses]
    marca_sql = ""
    if marcas_ids:
        ids = [int(m) for m in marcas_ids]
        if ids:
            ph_m = ",".join(["%s"] * len(ids))
            marca_sql = f" AND a.CodigoMarca IN ({ph_m})"
            params.extend(ids)
    cursor.execute(
        f"""
        SELECT t.id_articulo,
               COALESCE(a.id_manual, '') AS id_manual,
               DATE_FORMAT(t.creado_en, '%%Y-%%m') AS ym,
               COALESCE(SUM(t.cantidad), 0) AS cantidad
        FROM mpr_transicion_lote t
        INNER JOIN articulo a ON a.IDArt = t.id_articulo
        WHERE t.tipo_origen = %s
          AND t.tipo_destino = %s
          AND DATE_FORMAT(t.creado_en, '%%Y-%%m') IN ({ph_meses})
          {marca_sql}
        GROUP BY t.id_articulo, COALESCE(a.id_manual, ''), ym
        """,
        params,
    )
    rows = cursor.fetchall() or []
    if rows and not isinstance(rows[0], dict):
        cols = [d[0] for d in cursor.description] if cursor.description else []
        return [dict(zip(cols, r)) for r in rows]
    return list(rows)
