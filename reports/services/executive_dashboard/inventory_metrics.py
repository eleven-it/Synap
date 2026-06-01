"""Métricas inventario agregadas — alineado a stock-existencias / BO reservado."""
from __future__ import annotations

import logging
from typing import Any

from .base import DashboardFilters, build_meta, build_paginated_response, round_money, sql_fecha_en_periodo

logger = logging.getLogger(__name__)

_BUSQUEDA_MIN_LEN = 2


def _like_pattern(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _search_where_sql(busqueda: str | None) -> tuple[str, list]:
    """Filtro predictivo: artículo, código, manual, depósito, marca, rubro, subrubro."""
    if not busqueda or len(busqueda.strip()) < _BUSQUEDA_MIN_LEN:
        return "", []
    pattern = _like_pattern(busqueda.strip())
    clause = """
        AND (
            a.NombreArticulo LIKE %s ESCAPE '\\\\'
            OR CAST(a.CodigoArticulo AS CHAR) LIKE %s ESCAPE '\\\\'
            OR IFNULL(a.id_manual, '') LIKE %s ESCAPE '\\\\'
            OR IFNULL(dep.NombreDeposito, '') LIKE %s ESCAPE '\\\\'
            OR IFNULL(ma.NombreMarca, '') LIKE %s ESCAPE '\\\\'
            OR IFNULL(ru.NombreRubro, '') LIKE %s ESCAPE '\\\\'
            OR IFNULL(su.NombreSubRubro, '') LIKE %s ESCAPE '\\\\'
        )
    """
    params = [pattern] * 7
    return clause, params


def _reservado_join_sql(filters: DashboardFilters) -> str:
    """Subconsulta reservado PED; filtra cp_res.Fecha al período del dashboard."""
    fecha_sql, _ = sql_fecha_en_periodo("cp_res", filters)
    return f"""
    LEFT JOIN (
        SELECT sp_res.IDArt AS id_articulo,
            sp_res.CodDeposito AS id_deposito,
            SUM(COALESCE(sp_res.cantidad_pendiente,
                sp_res.Cantidad - COALESCE(sp_res.cantidad_entregada, 0))) AS reservado
        FROM stockp sp_res
        INNER JOIN comp_ped cp_res ON cp_res.CodigoMovimiento = sp_res.CodigoMovimiento
        WHERE cp_res.TipoComprobante = 'PED'
            AND (sp_res.Comprobante = 'PED' OR sp_res.Comprobante IS NULL)
            AND cp_res.Anulado = 'No'
            AND (sp_res.anulado IS NULL OR sp_res.anulado = 'No')
            AND cp_res.Estado IN ('En preparación', 'Preparado')
            AND (COALESCE(sp_res.cantidad_pendiente,
                sp_res.Cantidad - COALESCE(sp_res.cantidad_entregada, 0)) > 0)
            {fecha_sql}
        GROUP BY sp_res.IDArt, sp_res.CodDeposito
    ) res ON res.id_articulo = a.IDArt AND res.id_deposito = sd.id_deposito
"""


def _count_productos_bajo_minimo(cursor, filters: DashboardFilters) -> int | None:
    """Umbral: articulo.stock_min o punto_pedido (legacy AdministraNET)."""
    sql_bajo_min = f"""
        SELECT COUNT(*) FROM (
            SELECT a.IDArt,
                SUM(GREATEST(0, COALESCE(sd.saldo, 0) - COALESCE(res.reservado, 0))) AS disp,
                GREATEST(COALESCE(a.stock_min, 0), COALESCE(a.punto_pedido, 0)) AS umbral
            FROM articulo a
            INNER JOIN stock_deposito sd ON sd.id_articulo = a.IDArt
            {_reservado_join_sql(filters)}
            WHERE a.Discontinuo = 'No'
              AND a.disponible_vta = 'Si'
              AND a.tipo_art = 'Articulo'
            GROUP BY a.IDArt
            HAVING umbral > 0 AND disp < umbral
        ) sub
    """
    try:
        _, reservado_params = sql_fecha_en_periodo("cp_res", filters)
        cursor.execute(sql_bajo_min, reservado_params)
        row_bm = cursor.fetchone()
        return int(row_bm[0] or 0) if row_bm else 0
    except Exception as exc:
        logger.warning("productos_bajo_minimo no calculado: %s", exc)
        return None


def fetch_inventario_resumen(cursor, filters: DashboardFilters) -> dict[str, Any]:
    notas = [
        "Valor stock: saldo depósito × PrecioCosto (costo); paridad Info_Stock lista_precio=0; snapshot actual.",
        "Reservado y bajo mínimo: PED En preparación/Preparado filtrados por cp_res.Fecha en el período.",
        "Filtro sucursal no aplica a inventario en v1.",
    ]
    sql = """
        SELECT
            COALESCE(SUM(COALESCE(sd.saldo, 0) * COALESCE(a.PrecioCosto, 0)), 0) AS valor_stock,
            COUNT(DISTINCT CASE WHEN COALESCE(sd.saldo, 0) > 0 THEN a.IDArt END) AS productos_con_stock,
            COUNT(DISTINCT CASE WHEN COALESCE(sd.saldo, 0) = 0 THEN a.IDArt END) AS productos_sin_stock
        FROM stock_deposito sd
        INNER JOIN articulo a ON a.IDArt = sd.id_articulo
        WHERE a.Discontinuo = 'No'
          AND a.disponible_vta = 'Si'
          AND a.tipo_art = 'Articulo'
    """
    cursor.execute(sql)
    row = cursor.fetchone()
    valor_stock = float(row[0] or 0) if row else 0.0
    productos_con_stock = int(row[1] or 0) if row else 0
    productos_sin_stock = int(row[2] or 0) if row else 0

    productos_bajo_minimo = _count_productos_bajo_minimo(cursor, filters)
    if productos_bajo_minimo is None:
        notas.append("productos_bajo_minimo: no disponible (columnas stock_min/punto_pedido).")

    return {
        "valor_stock": round_money(valor_stock),
        "productos_con_stock": productos_con_stock,
        "productos_bajo_minimo": productos_bajo_minimo if productos_bajo_minimo is not None else 0,
        "productos_sin_stock": productos_sin_stock,
        "disponible": True,
        "meta": build_meta(filters, notas_semanticas=notas),
    }


def list_existencias(cursor, filters: DashboardFilters) -> dict[str, Any]:
    """Detalle paginado existencias — criterios stock-existencias; búsqueda opcional vía `busqueda`."""
    notas = [
        "Paridad informe stock-existencias; solo artículos Discontinuo=No, disponible_vta=Si.",
        "Filtro sucursal no aplica en v1.",
    ]
    if filters.busqueda:
        notas.append(
            f"Búsqueda predictiva (mín. {_BUSQUEDA_MIN_LEN} caracteres): artículo, código, depósito, marca, rubro."
        )
    reservado_join_sql = _reservado_join_sql(filters)
    _, reservado_params = sql_fecha_en_periodo("cp_res", filters)
    where_art = """
        a.Discontinuo = 'No'
        AND a.disponible_vta = 'Si'
        AND a.tipo_art = 'Articulo'
        AND COALESCE(sd.saldo, 0) > 0
    """
    search_sql, search_params = _search_where_sql(filters.busqueda)
    where_art += search_sql
    from_clause = f"""
        FROM stock_deposito sd
        INNER JOIN articulo a ON a.IDArt = sd.id_articulo
        INNER JOIN deposito dep ON dep.CodDeposito = sd.id_deposito
        LEFT JOIN marca ma ON ma.CodMarca = a.CodigoMarca
        LEFT JOIN rubro ru ON ru.CodigoRubro = a.CodigoRubro
        LEFT JOIN subrubro su ON su.IDSubRubro = a.IDSubRubro
        {reservado_join_sql}
        WHERE {where_art}
    """
    notas.append("Reservado: PED en período (cp_res.Fecha entre fecha_inicio y fecha_fin).")
    sql_count = f"SELECT COUNT(*) {from_clause}"
    cursor.execute(sql_count, reservado_params + search_params)
    row_count = cursor.fetchone()
    total_registros = int(row_count[0] or 0) if row_count else 0

    sql = f"""
        SELECT
            a.IDArt AS id_art,
            COALESCE(a.CodigoArticulo, 0) AS codigo_articulo,
            a.id_manual AS id_manual,
            a.NombreArticulo AS nombre,
            sd.id_deposito AS id_deposito,
            IFNULL(dep.NombreDeposito, CONCAT('Depósito ', sd.id_deposito)) AS deposito_nombre,
            IFNULL(ma.NombreMarca, '') AS marca_nombre,
            IFNULL(ru.NombreRubro, '') AS rubro_nombre,
            IFNULL(su.NombreSubRubro, '') AS subrubro_nombre,
            COALESCE(sd.saldo, 0) AS stock,
            COALESCE(res.reservado, 0) AS reservado,
            GREATEST(0, COALESCE(sd.saldo, 0) - COALESCE(res.reservado, 0)) AS disponible
        {from_clause}
        ORDER BY a.NombreArticulo ASC, sd.id_deposito ASC
        LIMIT %s OFFSET %s
    """
    cursor.execute(sql, reservado_params + search_params + [filters.limit, filters.offset])
    cols = [d[0] for d in cursor.description]
    filas = []
    for row in cursor.fetchall():
        item = {}
        for i, c in enumerate(cols):
            v = row[i]
            if c in ("stock", "reservado", "disponible") and v is not None:
                item[c] = float(v)
            elif c in ("id_art", "codigo_articulo", "id_deposito") and v is not None:
                item[c] = int(v) if str(v).replace("-", "").isdigit() else v
            else:
                item[c] = "" if v is None else str(v).strip() if c in ("marca_nombre", "rubro_nombre", "subrubro_nombre", "nombre", "deposito_nombre") else v
        filas.append(item)

    return build_paginated_response(
        filters, filas, total_registros, total_monto=None, notas_semanticas=notas
    )
