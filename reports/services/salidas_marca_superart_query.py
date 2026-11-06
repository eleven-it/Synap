# -*- coding: utf-8 -*-
"""Consultas read-only MySQL — Salidas por marca y SuperArtículo."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence

from reports.services.articulo_venta_sql import sql_excluir_tipo_art_gasto
from reports.services.compras_marca_superart_query import (
    buscar_marcas_compras_predictivo,
    buscar_superart_compras_predictivo,
)
from reports.services.connection_pool import get_mysql_pool
from reports.services.salidas_marca_superart_calcs import (
    DEPOSITO_TERMINADO,
    agrupar_salidas_marca_superart,
    sql_packs_netos_salidas,
    sql_via_trazabilidad_salidas,
)
from reports.services.compras_marca_superart_calcs import sql_marcas_compras_universo

logger = logging.getLogger(__name__)


def _ym_expr(fecha_col: str) -> str:
    return f"DATE_FORMAT({fecha_col}, '%%Y-%%m')"


def _fetch_salidas_cliente_terminado(
    cursor,
    desde: str,
    hasta: str,
    marcas_incluidos: Optional[Sequence[int]],
    marcas_excluidos: Optional[Sequence[int]],
) -> List[Dict[str, Any]]:
    via_expr = sql_via_trazabilidad_salidas("st", "rem")
    packs_expr = sql_packs_netos_salidas("st")
    where = [
        "COALESCE(st.Tipo, '') = 'Cliente'",
        "COALESCE(st.anulado, 'No') = 'No'",
        f"st.CodDeposito = {DEPOSITO_TERMINADO}",
        "st.Fecha >= %s",
        "st.Fecha <= %s",
        "COALESCE(st.Comprobante, '') <> 'MSTOCK'",
        """COALESCE(st.TipoComp, '') NOT IN ('Anul Remito', 'Anul Venta')""",
        sql_excluir_tipo_art_gasto("a"),
        sql_marcas_compras_universo("m"),
        f"""(
            COALESCE(st.TipoComp, '') = 'Remito Salida'
            OR (
                COALESCE(st.TipoComp, '') = 'Venta'
                AND COALESCE(st.codmov_remito, 0) = 0
            )
            OR COALESCE(st.TipoComp, '') = 'Devol - Cliente'
        )""",
        f"({via_expr}) <> 'otro'",
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
            {via_expr} AS via_trazabilidad,
            SUM({packs_expr}) AS packs
        FROM stock st
        INNER JOIN articulo a ON a.IDArt = st.IDArt
        LEFT JOIN marca m ON m.CodMarca = a.CodigoMarca
        LEFT JOIN comp_ped rem ON rem.CodigoMovimiento = st.CodigoMovimiento
            AND rem.TipoComprobante = 'REM'
        WHERE {" AND ".join(where)}
        GROUP BY a.IDArt, a.id_manual, a.NombreArticulo, a.CodigoArticulo, a.CodigoMarca,
                 m.NombreMarca, {_ym_expr("st.Fecha")}, {via_expr}
        HAVING ABS(SUM({packs_expr})) > 0.0001
    """
    cursor.execute(sql, params)
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def _fetch_mstock_kpi_informativo(
    cursor,
    desde: str,
    hasta: str,
    marcas_incluidos: Optional[Sequence[int]],
    marcas_excluidos: Optional[Sequence[int]],
) -> float:
    """MSTOCK en Terminado, mismo universo de marcas Best Sox que el informe (no suma al total)."""
    where = [
        "COALESCE(st.anulado, 'No') = 'No'",
        "COALESCE(st.Comprobante, '') = 'MSTOCK'",
        f"st.CodDeposito = {DEPOSITO_TERMINADO}",
        "st.Fecha >= %s",
        "st.Fecha <= %s",
        sql_excluir_tipo_art_gasto("a"),
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
        SELECT COALESCE(SUM(COALESCE(st.Salida, 0) - COALESCE(st.Entrada, 0)), 0) AS packs_mstock
        FROM stock st
        INNER JOIN articulo a ON a.IDArt = st.IDArt
        LEFT JOIN marca m ON m.CodMarca = a.CodigoMarca
        WHERE {" AND ".join(where)}
    """
    try:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return float(row[0] or 0) if row else 0.0
    except Exception as exc:
        logger.debug("mstock kpi salidas: %s", exc)
        return 0.0


def reporte_salidas_marca_superart(
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
    mstock_kpi = 0.0
    with pool.get_connection(str(base_empresa).strip()) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SET SESSION max_execution_time = 120000")
        except Exception:
            pass
        marcas_ids = list(marcas_incluidos or [])
        marcas_ex = [x for x in (marcas_excluidos or []) if x not in set(marcas_ids)]
        filas = _fetch_salidas_cliente_terminado(
            cursor,
            desde_iso,
            hasta_iso,
            marcas_ids or None,
            marcas_ex or None,
        )
        mstock_kpi = _fetch_mstock_kpi_informativo(
            cursor,
            desde_iso,
            hasta_iso,
            marcas_ids or None,
            marcas_ex or None,
        )

    out = agrupar_salidas_marca_superart(
        filas,
        meses,
        superarts_incluidos=superarts_incluidos,
        superarts_excluidos=superarts_excluidos,
        marcas_incluidos_ids=marcas_ids,
        marcas_excluidos_ids=marcas_ex,
    )
    out["mstock_kpi_packs"] = round(mstock_kpi, 4)
    return out


def buscar_marcas_salidas_predictivo(
    base_empresa: str,
    q: str,
    *,
    limit: int = 25,
) -> List[Dict[str, Any]]:
    return buscar_marcas_compras_predictivo(base_empresa, q, limit=limit)


def buscar_superart_salidas_predictivo(
    base_empresa: str,
    q: str,
    *,
    limit: int = 25,
) -> List[Dict[str, str]]:
    return buscar_superart_compras_predictivo(base_empresa, q, limit=limit)
