# -*- coding: utf-8 -*-
"""Consultas read-only MySQL — Compras por marca y SuperArtículo."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence

from core.utils.administranet_types import to_int_or_none
from reports.services.articulo_venta_sql import sql_excluir_tipo_art_gasto
from reports.services.compras_marca_superart_calcs import (
    DEPOSITO_TERMINADO,
    MOTIVOS_MSTOCK_EXCLUIDOS,
    MOTIVOS_MSTOCK_INCLUIDOS,
    agrupar_compras_marca_superart,
    sql_expresion_superart_compras,
    sql_marcas_compras_universo,
    sql_solo_terminados_terceros,
)
from reports.services.connection_pool import get_mysql_pool

logger = logging.getLogger(__name__)


def _ym_expr(fecha_col: str) -> str:
    return f"DATE_FORMAT({fecha_col}, '%Y-%m')"


def _fetch_via_proveedor(
    cursor,
    desde: str,
    hasta: str,
    marcas_incluidos: Optional[Sequence[int]],
    marcas_excluidos: Optional[Sequence[int]],
) -> List[Dict[str, Any]]:
    where = [
        "cp.Anulado = 'No'",
        "COALESCE(cp.CodigoMovimiento, 0) <> 0",
        "cp.Fecha >= %s",
        "cp.Fecha <= %s",
        "COALESCE(st.anulado, 'No') = 'No'",
        "COALESCE(st.CodDeposito, 0) <> 0",
        "COALESCE(st.Entrada, 0) > 0",
        sql_excluir_tipo_art_gasto("a"),
        sql_solo_terminados_terceros("a"),
        sql_marcas_compras_universo("m"),
        """(
            (
                cp.TipoComprobante IN ('FA', 'FC', 'FM')
                AND st.TipoComp = 'Compra'
                AND st.Comprobante IN ('FA', 'FC', 'FM')
            )
            OR (
                cp.TipoComprobante = 'REM'
                AND st.TipoComp = 'Remito Entrada'
            )
        )""",
    ]
    params: List[Any] = [desde, hasta]
    if marcas_incluidos:
        ph = ",".join(["%s"] * len(marcas_incluidos))
        where.append(f"a.CodigoMarca IN ({ph})")
        params.extend(list(marcas_incluidos))
    if marcas_excluidos:
        ph = ",".join(["%s"] * len(marcas_excluidos))
        where.append(f"(a.CodigoMarca IS NULL OR a.CodigoMarca NOT IN ({ph}))")
        params.extend(list(marcas_excluidos))

    sql = f"""
        SELECT
            a.IDArt AS id_articulo,
            TRIM(COALESCE(a.id_manual, '')) AS id_manual,
            COALESCE(a.NombreArticulo, '') AS nombre_articulo,
            COALESCE(a.CodigoArticulo, '') AS codigo_articulo,
            COALESCE(a.CodigoMarca, 0) AS codigo_marca,
            COALESCE(MAX(m.NombreMarca), '') AS nombre_marca,
            UPPER(TRIM(COALESCE(m.NombreMarca, ''))) AS marca_codigo,
            {_ym_expr("cp.Fecha")} AS ym,
            SUM(COALESCE(st.Entrada, 0)) AS packs
        FROM stock st
        INNER JOIN cuentaproveedor cp ON cp.CodigoMovimiento = st.CodigoMovimiento
        INNER JOIN articulo a ON a.IDArt = st.IDArt
        LEFT JOIN marca m ON m.CodMarca = a.CodigoMarca
        WHERE {" AND ".join(where)}
        GROUP BY a.IDArt, a.id_manual, a.NombreArticulo, a.CodigoArticulo, a.CodigoMarca,
                 m.NombreMarca, {_ym_expr("cp.Fecha")}
        HAVING SUM(COALESCE(st.Entrada, 0)) > 0
    """
    cursor.execute(sql, params)
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def _fetch_via_mstock(
    cursor,
    desde: str,
    hasta: str,
    marcas_incluidos: Optional[Sequence[int]],
    marcas_excluidos: Optional[Sequence[int]],
) -> List[Dict[str, Any]]:
    motivos_in = ",".join(f"'{m}'" for m in MOTIVOS_MSTOCK_INCLUIDOS)
    motivos_ex = ",".join(f"'{m}'" for m in MOTIVOS_MSTOCK_EXCLUIDOS)
    where = [
        "COALESCE(st.anulado, 'No') = 'No'",
        "st.Comprobante = 'MSTOCK'",
        f"st.CodDeposito = {DEPOSITO_TERMINADO}",
        "COALESCE(st.Entrada, 0) > 0",
        "st.Fecha >= %s",
        "st.Fecha <= %s",
        f"COALESCE(ms.motivo_movimiento, st.TipoComp) IN ({motivos_in})",
        f"COALESCE(ms.motivo_movimiento, st.TipoComp) NOT IN ({motivos_ex})",
        f"COALESCE(ms.deposito_origen, 0) = {DEPOSITO_TERMINADO}",
        f"COALESCE(ms.deposito_destino, 0) = {DEPOSITO_TERMINADO}",
        "COALESCE(ms.anulado, 'No') = 'No'",
        """NOT (
            COALESCE(ms.motivo_movimiento, st.TipoComp) = 'Ajuste'
            AND (
                LOWER(COALESCE(ms.detalle, '')) LIKE '%cutover%'
                OR COALESCE(ms.detalle, '') LIKE '%Ajuste de saldo%'
            )
        )""",
        sql_excluir_tipo_art_gasto("a"),
        sql_solo_terminados_terceros("a"),
        sql_marcas_compras_universo("m"),
    ]
    params: List[Any] = [desde, hasta]
    if marcas_incluidos:
        ph = ",".join(["%s"] * len(marcas_incluidos))
        where.append(f"a.CodigoMarca IN ({ph})")
        params.extend(list(marcas_incluidos))
    if marcas_excluidos:
        ph = ",".join(["%s"] * len(marcas_excluidos))
        where.append(f"(a.CodigoMarca IS NULL OR a.CodigoMarca NOT IN ({ph}))")
        params.extend(list(marcas_excluidos))

    sql = f"""
        SELECT
            a.IDArt AS id_articulo,
            TRIM(COALESCE(a.id_manual, '')) AS id_manual,
            COALESCE(a.NombreArticulo, '') AS nombre_articulo,
            COALESCE(a.CodigoArticulo, '') AS codigo_articulo,
            COALESCE(a.CodigoMarca, 0) AS codigo_marca,
            COALESCE(MAX(m.NombreMarca), '') AS nombre_marca,
            UPPER(TRIM(COALESCE(m.NombreMarca, ''))) AS marca_codigo,
            {_ym_expr("st.Fecha")} AS ym,
            SUM(COALESCE(st.Entrada, 0)) AS packs
        FROM stock st
        INNER JOIN movimiento_stock ms ON ms.codigo_movimiento = st.CodigoMovimiento
        INNER JOIN articulo a ON a.IDArt = st.IDArt
        LEFT JOIN marca m ON m.CodMarca = a.CodigoMarca
        WHERE {" AND ".join(where)}
        GROUP BY a.IDArt, a.id_manual, a.NombreArticulo, a.CodigoArticulo, a.CodigoMarca,
                 m.NombreMarca, {_ym_expr("st.Fecha")}
        HAVING SUM(COALESCE(st.Entrada, 0)) > 0
    """
    cursor.execute(sql, params)
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def _merge_filas(
    filas_a: Sequence[Dict[str, Any]],
    filas_b: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    merged: Dict[tuple, Dict[str, Any]] = {}
    for row in list(filas_a or []) + list(filas_b or []):
        aid = to_int_or_none(row.get("id_articulo"))
        ym = str(row.get("ym") or "").strip()
        if aid is None or not ym:
            continue
        key = (int(aid), ym)
        try:
            qty = float(row.get("packs") or 0)
        except (TypeError, ValueError):
            qty = 0.0
        if key not in merged:
            merged[key] = dict(row)
            merged[key]["packs"] = qty
        else:
            merged[key]["packs"] = round(float(merged[key].get("packs") or 0) + qty, 4)
            if row.get("id_manual") and not merged[key].get("id_manual"):
                merged[key]["id_manual"] = row.get("id_manual")
    return list(merged.values())


def reporte_compras_marca_superart(
    base_empresa: str,
    *,
    meses: Sequence[str],
    desde_iso: str,
    hasta_iso: str,
    marcas_incluidos: Optional[Sequence[int]] = None,
    marcas_excluidos: Optional[Sequence[int]] = None,
    superarts_incluidos: Optional[Sequence[str]] = None,
    superarts_excluidos: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    pool = get_mysql_pool()
    with pool.get_connection(str(base_empresa).strip()) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SET SESSION max_execution_time = 120000")
        except Exception:
            pass
        marcas_ids = list(marcas_incluidos or [])
        marcas_ex = [x for x in (marcas_excluidos or []) if x not in set(marcas_ids)]
        via1 = _fetch_via_proveedor(
            cursor,
            desde_iso,
            hasta_iso,
            marcas_ids or None,
            marcas_ex or None,
        )
        via2 = _fetch_via_mstock(
            cursor,
            desde_iso,
            hasta_iso,
            marcas_ids or None,
            marcas_ex or None,
        )
    filas = _merge_filas(via1, via2)
    return agrupar_compras_marca_superart(
        filas,
        meses,
        superarts_incluidos=superarts_incluidos,
        superarts_excluidos=superarts_excluidos,
        marcas_incluidos_ids=marcas_ids,
        marcas_excluidos_ids=marcas_ex,
    )


def buscar_marcas_compras_predictivo(
    base_empresa: str,
    q: str,
    *,
    limit: int = 25,
) -> List[Dict[str, Any]]:
    from stock.services.inventario_tabla import listar_marcas_catalogo

    texto = (q or "").strip().lower()
    if not texto or not (base_empresa or "").strip():
        return []
    catalogo = listar_marcas_catalogo(base_empresa)
    out: List[Dict[str, Any]] = []
    for item in catalogo:
        label = str(item.get("label") or "")
        if texto in label.lower():
            cod = label.strip().upper().split()[0] if label else ""
            if cod not in {"LB", "PUS", "PUW", "RW"} and not any(
                c in label.upper() for c in ("LB", "PUS", "PUW", "RW")
            ):
                continue
            out.append({"value": item.get("value"), "label": label})
            if len(out) >= max(1, limit):
                break
    return out


def buscar_superart_compras_predictivo(
    base_empresa: str,
    q: str,
    *,
    limit: int = 25,
) -> List[Dict[str, str]]:
    texto = (q or "").strip()
    if len(texto) < 1 or not (base_empresa or "").strip():
        return []
    lim = max(1, min(int(limit or 25), 50))
    like = f"%{texto}%"
    superart_expr = sql_expresion_superart_compras("a")
    try:
        pool = get_mysql_pool()
        with pool.get_connection(str(base_empresa).strip()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT DISTINCT superart_calc AS codigo
                FROM (
                  SELECT {superart_expr} AS superart_calc
                  FROM articulo a
                  LEFT JOIN marca m ON m.CodMarca = a.CodigoMarca
                  WHERE {sql_solo_terminados_terceros("a")}
                    AND {sql_marcas_compras_universo("m")}
                ) AS derived
                WHERE superart_calc IS NOT NULL
                  AND superart_calc LIKE %s
                ORDER BY codigo
                LIMIT %s
                """,
                (like, lim),
            )
            rows = cursor.fetchall()
    except Exception as exc:
        logger.warning("buscar_superart_compras_predictivo %s: %s", base_empresa, exc)
        return []
    out: List[Dict[str, str]] = []
    for row in rows:
        codigo = str(row[0] or "").strip()
        if not codigo:
            continue
        out.append({"codigo": codigo, "descripcion": codigo})
    return out
