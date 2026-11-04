# -*- coding: utf-8 -*-
"""SQL helpers para reglas de compras de terceros (stock + movimiento_stock)."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Sequence

from reports.services.articulo_venta_sql import sql_excluir_tipo_art_gasto
from reports.services.compras_terceros_config import get_compras_terceros_reglas


def sql_marca_join() -> str:
    return "LEFT JOIN marca m ON m.CodMarca = a.CodigoMarca"


def _marca_filter_sql(
    marcas_ids: Optional[Sequence[int]],
    marcas_excluidos_ids: Optional[Sequence[int]],
    params: List[Any],
) -> str:
    sql = ""
    if marcas_ids:
        ids = [int(m) for m in marcas_ids if m is not None]
        if ids:
            ph = ",".join(["%s"] * len(ids))
            sql += f" AND a.CodigoMarca IN ({ph})"
            params.extend(ids)
    if marcas_excluidos_ids:
        ids_ex = [int(m) for m in marcas_excluidos_ids if m is not None]
        if ids_ex:
            ph_ex = ",".join(["%s"] * len(ids_ex))
            sql += f" AND (a.CodigoMarca IS NULL OR a.CodigoMarca NOT IN ({ph_ex}))"
            params.extend(ids_ex)
    return sql


def _finished_product_sql(alias: str = "a") -> str:
    a = alias.strip() or "a"
    return (
        f"({a}.tipo_art_fab IS NULL OR TRIM({a}.tipo_art_fab) = '' "
        f"OR {a}.tipo_art_fab IN ('Terminado', 'Tercero'))"
    )


def _append_regla_predicates(
    regla: Dict[str, Any],
    params: List[Any],
    *,
    ms_alias: str = "ms",
    s_alias: str = "s",
) -> str:
    """Fragmento AND … para una regla (sin fecha ni marca). Solo detalle + depósito + TipoComp opcional."""
    match = regla.get("match") or {}
    sql_parts: List[str] = []
    deposito = regla.get("deposito_id")
    if deposito is not None:
        sql_parts.append(f" AND {s_alias}.CodDeposito = %s")
        params.append(int(deposito))
    require_tipo = (regla.get("require_tipo_comp") or "").strip()
    if require_tipo:
        sql_parts.append(f" AND {s_alias}.TipoComp = %s")
        params.append(require_tipo)
    detalle_kw = (match.get("detalle_contains") or "").strip()
    if detalle_kw:
        sql_parts.append(f" AND UPPER(COALESCE({ms_alias}.detalle, '')) LIKE %s")
        params.append(f"%{detalle_kw.upper()}%")
    return "".join(sql_parts)


def regla_has_match_criteria(regla: Dict[str, Any]) -> bool:
    match = regla.get("match") or {}
    return bool((match.get("detalle_contains") or "").strip())


def fetch_compras_regla_filas(
    cursor,
    regla: Dict[str, Any],
    *,
    desde: date,
    hasta: date,
    marcas_ids: Optional[Sequence[int]] = None,
    marcas_excluidos_ids: Optional[Sequence[int]] = None,
) -> List[Dict[str, Any]]:
    """Líneas stock (id_stock) que cumplen una regla de terceros en el rango de fechas."""
    if not regla_has_match_criteria(regla):
        return []

    hasta_excl = hasta + timedelta(days=1)
    params: List[Any] = [desde.isoformat(), hasta_excl.isoformat()]
    regla_sql = _append_regla_predicates(regla, params)
    if not regla_sql.strip():
        return []
    marca_sql = _marca_filter_sql(marcas_ids, marcas_excluidos_ids, params)
    gasto_sql = sql_excluir_tipo_art_gasto("a")
    finished_sql = _finished_product_sql("a")

    cursor.execute(
        f"""
        SELECT s.id_stock,
               s.IDArt AS id_articulo,
               COALESCE(a.id_manual, '') AS id_manual,
               COALESCE(a.CodigoMarca, 0) AS codigo_marca,
               COALESCE(m.NombreMarca, '') AS nombre_marca,
               COALESCE(a.IDArt, s.IDArt) AS codigo_articulo,
               COALESCE(a.NombreArticulo, '') AS nombre_articulo,
               COALESCE(um.nombre_unimed, '') AS nombre_unimed,
               DATE_FORMAT(ms.Fecha, '%%Y-%%m') AS ym,
               COALESCE(s.Cantidad, 0) AS packs,
               %s AS regla_id
        FROM stock s
        INNER JOIN movimiento_stock ms ON ms.codigo_movimiento = s.CodigoMovimiento
        INNER JOIN articulo a ON a.IDArt = s.IDArt
        {sql_marca_join()}
        LEFT JOIN unidmed um ON um.id_unimed = a.id_unimed
        WHERE IFNULL(s.Anulado, 'No') = 'No'
          AND IFNULL(ms.anulado, 'No') = 'No'
          AND ms.Fecha >= %s AND ms.Fecha < %s
          AND {finished_sql}
          AND {gasto_sql}
          {regla_sql}
          {marca_sql}
        """,
        [str(regla.get("id") or ""), *params],
    )
    rows = cursor.fetchall() or []
    if rows and not isinstance(rows[0], dict):
        cols = [d[0] for d in cursor.description] if cursor.description else []
        rows = [dict(zip(cols, r)) for r in rows]
    return list(rows)


def fetch_all_compras_reglas_extra_filas(
    cursor,
    *,
    desde: date,
    hasta: date,
    marcas_ids: Optional[Sequence[int]] = None,
    marcas_excluidos_ids: Optional[Sequence[int]] = None,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for regla in get_compras_terceros_reglas():
        out.extend(
            fetch_compras_regla_filas(
                cursor,
                regla,
                desde=desde,
                hasta=hasta,
                marcas_ids=marcas_ids,
                marcas_excluidos_ids=marcas_excluidos_ids,
            )
        )
    return out


def sql_exclude_stock_matching_terceros_reglas(params: List[Any]) -> str:
    """
    NOT EXISTS por regla: evita que compra estándar duplique líneas capturadas por reglas extra.
    """
    clauses: List[str] = []
    for regla in get_compras_terceros_reglas():
        if not regla_has_match_criteria(regla):
            continue
        regla_sql = _append_regla_predicates(
            regla,
            params,
            ms_alias="ms_ex",
            s_alias="s_ex",
        )
        if not regla_sql.strip():
            continue
        clauses.append(
            f"""
            NOT EXISTS (
                SELECT 1
                FROM movimiento_stock ms_ex
                INNER JOIN stock s_ex ON s_ex.CodigoMovimiento = ms_ex.codigo_movimiento
                WHERE s_ex.id_stock = s.id_stock
                  AND IFNULL(s_ex.Anulado, 'No') = 'No'
                  AND IFNULL(ms_ex.anulado, 'No') = 'No'
                  {regla_sql}
            )
            """
        )
    if not clauses:
        return ""
    return " AND " + " AND ".join(clauses)
