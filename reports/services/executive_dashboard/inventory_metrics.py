"""Métricas inventario agregadas — alineado a stock-existencias / BO reservado."""
from __future__ import annotations

import logging
from typing import Any

from core.utils.administranet_types import to_int_or_none

from .base import DashboardFilters, build_meta, build_paginated_response, round_money, sql_fecha_en_periodo

logger = logging.getLogger(__name__)

_BUSQUEDA_MIN_LEN = 2

# Orden de filas en el desglose del Command Center (etapas productivas + resto).
_ORDEN_TIPO_MPR_CC: tuple[str, ...] = (
    "Produccion",
    "SemiElaborado",
    "2daSeleccion",
    "Terminado",
)

_SQL_DEPOSITO_SUMA_STOCK = """
    UPPER(COALESCE(dep.anulado, 'NO')) <> 'SI'
    AND UPPER(TRIM(COALESCE(dep.suma_stock, 'NO'))) = 'SI'
"""

_SQL_ARTICULO_VENDIBLE = """
    UPPER(COALESCE(a.tipo_art, 'ARTICULO')) NOT IN ('GASTO','SERVICIO')
    AND UPPER(COALESCE(a.Discontinuo, 'NO')) <> 'SI'
"""


def _deposito_where(filters: DashboardFilters, alias: str = "dep") -> tuple[str, list[int]]:
    if not filters.depositos_filtro:
        return "", []
    placeholders = ",".join(["%s"] * len(filters.depositos_filtro))
    return f" AND {alias}.CodDeposito IN ({placeholders})", list(filters.depositos_filtro)


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


def _order_tipo_mpr_sql(alias: str = "dep") -> str:
    """CASE para ordenar depósitos por etapa MPR canónica del CC."""
    parts = [
        f"WHEN TRIM(COALESCE({alias}.tipo_mpr, '')) = '{tipo}' THEN {idx}"
        for idx, tipo in enumerate(_ORDEN_TIPO_MPR_CC)
    ]
    return "CASE " + " ".join(parts) + f" ELSE {len(_ORDEN_TIPO_MPR_CC)} END"


def _count_productos_bajo_minimo(cursor, filters: DashboardFilters) -> int | None:
    """V45: cuenta pares artículo-depósito según deposito_reposicion."""
    dep_sql, dep_params = _deposito_where(filters)
    sql_bajo_min = f"""
        SELECT COUNT(DISTINCT IF(lim.stock_minimo > 0
            AND COALESCE(sd.saldo,0) <= lim.stock_minimo,
            CONCAT(lim.id_articulo,'|',lim.id_deposito),NULL)) AS bajo_minimo
        FROM (
            SELECT id_articulo,id_deposito,MAX(stock_minimo) AS stock_minimo
            FROM deposito_reposicion GROUP BY id_articulo,id_deposito
        ) lim
        INNER JOIN articulo a ON a.IDArt = lim.id_articulo
        INNER JOIN deposito dep ON dep.CodDeposito = lim.id_deposito
        LEFT JOIN (
            SELECT id_articulo,id_deposito,SUM(saldo) AS saldo
            FROM stock_deposito GROUP BY id_articulo,id_deposito
        ) sd ON sd.id_articulo = lim.id_articulo AND sd.id_deposito = lim.id_deposito
        WHERE {_SQL_ARTICULO_VENDIBLE.strip()}
          AND {_SQL_DEPOSITO_SUMA_STOCK.strip()}
          {dep_sql}
    """
    try:
        cursor.execute(sql_bajo_min, dep_params)
        row_bm = cursor.fetchone()
        return int(row_bm[0] or 0) if row_bm else 0
    except Exception as exc:
        logger.warning("productos_bajo_minimo no calculado: %s", exc)
        return None


def _list_depositos_suma_stock(cursor, filters: DashboardFilters) -> list[dict[str, Any]]:
    """Una fila por depósito Stock=Sí; existencias positivas disponibles."""
    order_sql = _order_tipo_mpr_sql("dep")
    dep_sql, dep_params = _deposito_where(filters)
    sql = f"""
        SELECT
            dep.CodDeposito AS id_deposito,
            IFNULL(dep.NombreDeposito, CONCAT('Depósito ', dep.CodDeposito)) AS nombre,
            NULLIF(TRIM(COALESCE(dep.tipo_mpr, '')), '') AS tipo_mpr,
            COALESCE(SUM(
                CASE WHEN a.IDArt IS NOT NULL THEN GREATEST(0, COALESCE(sd.saldo, 0)) ELSE 0 END
            ), 0) AS unidades
        FROM deposito dep
        LEFT JOIN stock_deposito sd ON sd.id_deposito = dep.CodDeposito
        LEFT JOIN articulo a ON a.IDArt = sd.id_articulo
            AND UPPER(COALESCE(a.tipo_art, 'ARTICULO')) NOT IN ('GASTO','SERVICIO')
            AND UPPER(COALESCE(a.Discontinuo, 'NO')) <> 'SI'
        WHERE {_SQL_DEPOSITO_SUMA_STOCK.strip()}
          {dep_sql}
        GROUP BY dep.CodDeposito, dep.NombreDeposito, dep.tipo_mpr
        ORDER BY {order_sql} ASC, IFNULL(dep.NombreDeposito, '') ASC, dep.CodDeposito ASC
    """
    cursor.execute(sql, dep_params)
    rows = cursor.fetchall() or []
    cols = [d[0] for d in cursor.description] if cursor.description else []
    out: list[dict[str, Any]] = []
    for row in rows:
        item = {cols[i]: row[i] for i in range(len(cols))}
        id_dep = to_int_or_none(item.get("id_deposito"))
        if id_dep is None:
            continue
        unidades = to_int_or_none(item.get("unidades")) or 0
        if unidades < 0:
            unidades = 0
        tipo = item.get("tipo_mpr")
        tipo_str = str(tipo).strip() if tipo else None
        nombre = item.get("nombre")
        out.append(
            {
                "id_deposito": id_dep,
                "nombre": str(nombre).strip() if nombre else f"Depósito {id_dep}",
                "tipo_mpr": tipo_str or None,
                "unidades": unidades,
                "docenas": unidades // 12,
            }
        )
    return out


def fetch_inventario_resumen(cursor, filters: DashboardFilters) -> dict[str, Any]:
    notas = [
        "Valor stock: saldos positivos agrupados por artículo × PrecioCosto convertido a unidad, según modCM_StockDatos.bas/V45.",
        "Solo depósitos con Stock=Sí (suma_stock) y no anulados.",
        "Desglose por depósito: unidades = SUM(saldos positivos); docenas = unidades // 12.",
        "Bajo mínimo: pares artículo-depósito con saldo <= stock_minimo de deposito_reposicion (V45).",
        "Filtro sucursal no aplica a inventario en v1.",
    ]
    dep_sql, dep_params = _deposito_where(filters)
    factor_display = "IF(COALESCE(ap.cantidad_unidad_display,0)>0,ap.cantidad_unidad_display,1)"
    bulto = "COALESCE(NULLIF(ap.multiplicador_comp,0),NULLIF(ap.cantidad_display_bulto,0),0)"
    factor_bulto = (
        "IF(COALESCE(ap.cantidad_unidad_display,0)>0 AND "
        f"({bulto})>0,ap.cantidad_unidad_display*({bulto}),1)"
    )
    factor_costo = (
        "CASE UPPER(TRIM(COALESCE(ap.precio_unidad,'UNIDAD'))) "
        f"WHEN 'DISPLAY' THEN {factor_display} "
        f"WHEN 'BULTO' THEN {factor_bulto} "
        f"WHEN 'BULTO/PALLET' THEN {factor_bulto} ELSE 1 END"
    )
    sql = f"""
        SELECT
            COALESCE(SUM(IF(x.saldo > 0, x.saldo * x.costo_base, 0)), 0) AS valor_stock,
            COALESCE(SUM(x.saldo > 0), 0) AS productos_con_stock,
            COALESCE(SUM(x.saldo = 0), 0) AS productos_sin_stock
        FROM (
            SELECT a.IDArt,
                COALESCE(a.PrecioCosto,0) / NULLIF(MAX({factor_costo}),0) AS costo_base,
                COALESCE(SUM(sd.saldo),0) AS saldo
            FROM stock_deposito sd
            INNER JOIN articulo a ON a.IDArt = sd.id_articulo
            INNER JOIN deposito dep ON dep.CodDeposito = sd.id_deposito
            LEFT JOIN articulo_prov ap ON ap.id_articulo_prov = (
                SELECT ap0.id_articulo_prov FROM articulo_prov ap0
                WHERE ap0.IDArt = a.IDArt
                ORDER BY CASE WHEN ap0.CodProveedor = a.CodigoProveedor THEN 0 ELSE 1 END,
                    ap0.CodProveedor, ap0.id_articulo_prov LIMIT 1
            )
            WHERE UPPER(COALESCE(a.tipo_art,'ARTICULO')) NOT IN ('GASTO','SERVICIO')
              AND UPPER(COALESCE(a.Discontinuo,'NO')) <> 'SI'
              AND {_SQL_DEPOSITO_SUMA_STOCK.strip()}
              {dep_sql}
            GROUP BY a.IDArt, a.PrecioCosto
        ) x
    """
    cursor.execute(sql, dep_params)
    row = cursor.fetchone()
    valor_stock = float(row[0] or 0) if row else 0.0
    productos_con_stock = int(row[1] or 0) if row else 0
    productos_sin_stock = int(row[2] or 0) if row else 0

    productos_bajo_minimo = _count_productos_bajo_minimo(cursor, filters)
    if productos_bajo_minimo is None:
        notas.append("productos_bajo_minimo: no disponible (deposito_reposicion).")

    depositos = _list_depositos_suma_stock(cursor, filters)

    return {
        "valor_stock": round_money(valor_stock),
        "productos_con_stock": productos_con_stock,
        "productos_bajo_minimo": productos_bajo_minimo,
        "productos_sin_stock": productos_sin_stock,
        "depositos": depositos,
        "disponible": True,
        "meta": build_meta(filters, notas_semanticas=notas),
    }


def list_existencias(cursor, filters: DashboardFilters) -> dict[str, Any]:
    """Detalle paginado existencias — depósitos Stock=Sí; búsqueda opcional vía `busqueda`."""
    notas = [
        "Solo artículos no discontinuados, no Gasto/Servicio y depósitos Stock=Sí no anulados.",
        "Filtro sucursal no aplica en v1.",
    ]
    if filters.busqueda:
        notas.append(
            f"Búsqueda predictiva (mín. {_BUSQUEDA_MIN_LEN} caracteres): artículo, código, depósito, marca, rubro."
        )
    reservado_join_sql = _reservado_join_sql(filters)
    _, reservado_params = sql_fecha_en_periodo("cp_res", filters)
    dep_sql, dep_params = _deposito_where(filters)
    where_art = f"""
        {_SQL_ARTICULO_VENDIBLE.strip()}
        AND {_SQL_DEPOSITO_SUMA_STOCK.strip()}
        AND COALESCE(sd.saldo, 0) > 0
        {dep_sql}
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
    cursor.execute(sql_count, reservado_params + dep_params + search_params)
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
    cursor.execute(sql, reservado_params + dep_params + search_params + [filters.limit, filters.offset])
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
