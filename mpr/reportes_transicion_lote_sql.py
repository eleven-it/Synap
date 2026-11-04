# -*- coding: utf-8 -*-
"""Consultas reutilizables sobre mpr_transicion_lote (sin alterar reportes existentes)."""
from __future__ import annotations

import re
from calendar import monthrange
from datetime import date
from typing import Any, Dict, List, Optional, Sequence, Tuple

from mpr.services import TIPO_MPR_PRODUCCION, TIPO_MPR_SEMI_ELABORADO

# Fasón Tejeduría S y M: ingreso por mov. interno al depósito semi elaborado (sin transición MPR).
FASON_DEPOSITO_DESTINO_SEMI_ELABORADO = 3
FASON_MOTIVO_MOVIMIENTO = "Mov. Interno Entrada"
FASON_STOCK_TIPO_COMP = "Mov. Interno Entrada"
FASON_MOVIMIENTO_ANULADO_NO = "No"
# Parche operativo: no hay flag dedicado en movimiento_stock; el prefijo distingue fasón de ajustes.
FASON_DETALLE_LIKE_PREFIX = "INGRESO%"

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


def _rango_fecha_ms_desde_meses(meses_yyyy_mm: Sequence[str]) -> Tuple[date, date]:
    """Rango [desde, hasta) sobre ms.fecha que cubre los meses AAAA-MM indicados."""
    meses = normalizar_meses_yyyy_mm(meses_yyyy_mm)
    if not meses:
        hoy = date.today()
        return hoy.replace(day=1), hoy.replace(day=monthrange(hoy.year, hoy.month)[1] + 1)
    y0, m0 = (int(p) for p in meses[0].split("-", 1))
    y1, m1 = (int(p) for p in meses[-1].split("-", 1))
    desde = date(y0, m0, 1)
    if m1 == 12:
        hasta_ex = date(y1 + 1, 1, 1)
    else:
        hasta_ex = date(y1, m1 + 1, 1)
    return desde, hasta_ex


def _marca_filtro_sql_params(
    marcas_ids: Optional[Sequence[int]] = None,
    marcas_excluidos_ids: Optional[Sequence[int]] = None,
) -> Tuple[str, List[Any]]:
    marca_sql = ""
    params: List[Any] = []
    if marcas_ids:
        ids = [int(m) for m in marcas_ids]
        if ids:
            ph_m = ",".join(["%s"] * len(ids))
            marca_sql = f" AND a.CodigoMarca IN ({ph_m})"
            params.extend(ids)
    if marcas_excluidos_ids:
        ids_ex = [int(m) for m in marcas_excluidos_ids]
        if ids_ex:
            ph_ex = ",".join(["%s"] * len(ids_ex))
            marca_sql += f" AND (a.CodigoMarca IS NULL OR a.CodigoMarca NOT IN ({ph_ex}))"
            params.extend(ids_ex)
    return marca_sql, params


def _rows_desde_cursor(cursor) -> List[Dict[str, Any]]:
    rows = cursor.fetchall() or []
    if rows and not isinstance(rows[0], dict):
        cols = [d[0] for d in cursor.description] if cursor.description else []
        return [dict(zip(cols, r)) for r in rows]
    return list(rows)


def fetch_fabricado_primera_por_articulo_mes(
    cursor,
    meses_yyyy_mm: Sequence[str],
    *,
    marcas_ids: Optional[Sequence[int]] = None,
    marcas_excluidos_ids: Optional[Sequence[int]] = None,
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
    marca_sql, marca_params = _marca_filtro_sql_params(marcas_ids, marcas_excluidos_ids)
    params.extend(marca_params)
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
    return _rows_desde_cursor(cursor)


def fetch_fason_tejeduria_por_articulo_mes(
    cursor,
    meses_yyyy_mm: Sequence[str],
    *,
    marcas_ids: Optional[Sequence[int]] = None,
    marcas_excluidos_ids: Optional[Sequence[int]] = None,
) -> List[Dict[str, Any]]:
    """
    Pares de fasón Tejeduría S y M por artículo y mes (fecha del movimiento).
    Mov. interno de entrada al depósito semi elaborado con detalle INGRESO*.
    """
    meses = normalizar_meses_yyyy_mm(meses_yyyy_mm)
    if not meses:
        return []
    ph_meses = ",".join(["%s"] * len(meses))
    desde, hasta_ex = _rango_fecha_ms_desde_meses(meses)
    marca_sql, marca_params = _marca_filtro_sql_params(marcas_ids, marcas_excluidos_ids)
    params: List[Any] = [
        FASON_STOCK_TIPO_COMP,
        FASON_MOTIVO_MOVIMIENTO,
        FASON_DEPOSITO_DESTINO_SEMI_ELABORADO,
        FASON_MOVIMIENTO_ANULADO_NO,
        FASON_DETALLE_LIKE_PREFIX,
        desde.isoformat(),
        hasta_ex.isoformat(),
        *meses,
        *marca_params,
    ]
    cursor.execute(
        f"""
        SELECT s.IDArt AS id_articulo,
               COALESCE(a.id_manual, '') AS id_manual,
               DATE_FORMAT(ms.fecha, '%%Y-%%m') AS ym,
               COALESCE(SUM(s.Entrada), 0) AS cantidad
        FROM movimiento_stock ms
        INNER JOIN stock s
                ON s.CodigoMovimiento = ms.codigo_movimiento
               AND s.TipoComp = %s
        INNER JOIN articulo a ON a.IDArt = s.IDArt
        WHERE ms.motivo_movimiento = %s
          AND ms.deposito_destino = %s
          AND ms.anulado = %s
          AND ms.detalle LIKE %s
          AND ms.fecha >= %s
          AND ms.fecha < %s
          AND DATE_FORMAT(ms.fecha, '%%Y-%%m') IN ({ph_meses})
          {marca_sql}
        GROUP BY s.IDArt, COALESCE(a.id_manual, ''), ym
        """,
        params,
    )
    return _rows_desde_cursor(cursor)
