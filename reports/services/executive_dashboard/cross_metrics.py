"""KPIs cruzados — agregados backorder y facturación sin detalle masivo."""
from __future__ import annotations

from typing import Any, List, Optional

from reports.services.query_runner import parse_fecha_bo_yyyymmdd

from .base import DashboardFilters, build_meta, build_paginated_response, round_money
from .ventas_metrics import get_ventas_netas_total


def _sucursal_clause(sucursales: Optional[List[int]], alias: str) -> tuple[str, list]:
    if not sucursales:
        return "", []
    ph = ",".join(["%s"] * len(sucursales))
    return f" AND {alias}.CodSucursal IN ({ph})", list(sucursales)


def fetch_cruzados_resumen(cursor, filters: DashboardFilters) -> dict[str, Any]:
    fi, ff = filters.fecha_inicio_str, filters.fecha_fin_str
    fecha_inicio_bo, fecha_fin_bo = parse_fecha_bo_yyyymmdd(fi, ff)
    suc = filters.sucursales
    suc_bo, params_suc = _sucursal_clause(suc, "cp")

    sql_bo = f"""
        SELECT
            COALESCE(SUM(sp.PrecioNetoxR), 0) AS backorder_importe,
            COALESCE(SUM(sp.Cantidad), 0) AS backorder_unidades
        FROM stockp sp
        INNER JOIN comp_ped cp ON cp.CodigoMovimiento = sp.CodigoMovimiento
        LEFT JOIN articulo a ON a.IDArt = sp.IDArt
        WHERE cp.TipoComprobante = 'PED'
            AND (sp.Comprobante = 'PED' OR sp.Comprobante IS NULL)
            AND cp.Anulado = 'No'
            AND (sp.anulado IS NULL OR sp.anulado = 'No')
            AND cp.Estado IN ('Pendiente')
            AND sp.CodigoMovimiento IS NOT NULL
            AND sp.Fecha >= %s AND sp.Fecha <= %s
            {suc_bo}
            AND (a.IDArt IS NULL OR a.tipo_art IS NULL OR a.tipo_art <> 'Gasto')
    """
    params_bo = [fecha_inicio_bo, fecha_fin_bo] + params_suc
    cursor.execute(sql_bo, params_bo)
    row_bo = cursor.fetchone()
    backorder_importe = float(row_bo[0] or 0) if row_bo else 0.0
    backorder_unidades = float(row_bo[1] or 0) if row_bo else 0.0

    suc_res, params_res = _sucursal_clause(suc, "cp_res")
    sql_res = f"""
        SELECT COALESCE(SUM(
            COALESCE(sp_res.cantidad_pendiente,
                sp_res.Cantidad - COALESCE(sp_res.cantidad_entregada, 0))
        ), 0) AS stock_reservado_unidades
        FROM stockp sp_res
        INNER JOIN comp_ped cp_res ON cp_res.CodigoMovimiento = sp_res.CodigoMovimiento
        WHERE cp_res.TipoComprobante = 'PED'
            AND (sp_res.Comprobante = 'PED' OR sp_res.Comprobante IS NULL)
            AND cp_res.Anulado = 'No'
            AND (sp_res.anulado IS NULL OR sp_res.anulado = 'No')
            AND cp_res.Estado IN ('En preparación', 'Preparado')
            AND (COALESCE(sp_res.cantidad_pendiente,
                sp_res.Cantidad - COALESCE(sp_res.cantidad_entregada, 0)) > 0)
            {suc_res}
    """
    cursor.execute(sql_res, params_res)
    row_res = cursor.fetchone()
    stock_reservado = float(row_res[0] or 0) if row_res else 0.0

    facturacion = get_ventas_netas_total(cursor, fi, ff, sucursales=suc)

    demand_coverage_pct = None
    if backorder_importe > 0:
        denom = facturacion + backorder_importe
        if denom > 0:
            demand_coverage_pct = round(100.0 * facturacion / denom, 2)

    notas = [
        "Backorder: PED Pendiente en stockp.Fecha (YYYYMMDD) del período.",
        "demand_coverage_pct v1: proxy facturación / (facturación + backorder_importe).",
    ]
    return {
        "backorder_importe": round_money(backorder_importe),
        "backorder_unidades": round(backorder_unidades, 2),
        "stock_reservado_unidades": round(stock_reservado, 2),
        "facturacion_periodo": round_money(facturacion),
        "demand_coverage_pct": demand_coverage_pct,
        "disponible": True,
        "meta": build_meta(filters, notas_semanticas=notas),
    }


def _enrich_bo_item(
    id_art,
    codigo,
    articulo,
    categoria,
    bo_qty,
    bo_importe,
    stock_actual,
    stock_reservado,
    disponible,
    oc_pendiente,
) -> dict:
    faltante_reservado = max(0.0, stock_reservado - stock_actual)
    oc_para_reservado = min(oc_pendiente, faltante_reservado)
    oc_restante_bo = max(0.0, oc_pendiente - oc_para_reservado)
    con_stock_qty = min(bo_qty, disponible)
    rest = bo_qty - con_stock_qty
    con_ingreso_qty = min(rest, oc_restante_bo)
    sin_stock_qty = rest - con_ingreso_qty
    if bo_qty > 0:
        con_stock_importe = bo_importe * (con_stock_qty / bo_qty)
        con_ingreso_importe = bo_importe * (con_ingreso_qty / bo_qty)
        sin_stock_importe = bo_importe * (sin_stock_qty / bo_qty)
    else:
        con_stock_importe = con_ingreso_importe = sin_stock_importe = 0.0
    return {
        "id_art": int(id_art) if id_art is not None else None,
        "codigo": codigo or "",
        "articulo": articulo or "",
        "categoria": categoria or "Sin Rubro",
        "bo_qty": round(bo_qty, 2),
        "bo_importe": round_money(bo_importe),
        "stock_actual": round(stock_actual, 2),
        "stock_reservado": round(stock_reservado, 2),
        "disponible": round(disponible, 2),
        "oc_pendiente": round(oc_pendiente, 2),
        "con_stock_qty": round(con_stock_qty, 2),
        "con_stock_importe": round_money(con_stock_importe),
        "con_ingreso_qty": round(con_ingreso_qty, 2),
        "con_ingreso_importe": round_money(con_ingreso_importe),
        "sin_stock_qty": round(sin_stock_qty, 2),
        "sin_stock_importe": round_money(sin_stock_importe),
    }


def list_backorder_detalle(cursor, filters: DashboardFilters) -> dict[str, Any]:
    """Detalle BO por artículo paginado — paridad informe bo-stock-facturacion."""
    fi, ff = filters.fecha_inicio_str, filters.fecha_fin_str
    fecha_inicio_bo, fecha_fin_bo = parse_fecha_bo_yyyymmdd(fi, ff)
    suc = filters.sucursales
    suc_bo, params_suc = _sucursal_clause(suc, "cp")
    precio_sql = "a.Precio1V"

    bo_core = f"""
        FROM stockp sp
        INNER JOIN comp_ped cp ON cp.CodigoMovimiento = sp.CodigoMovimiento
        LEFT JOIN articulo a ON a.IDArt = sp.IDArt
        LEFT JOIN rubro r ON r.CodigoRubro = a.CodigoRubro
        LEFT JOIN (
            SELECT id_articulo, SUM(saldo) AS stock_total
            FROM stock_deposito
            GROUP BY id_articulo
        ) sd ON sd.id_articulo = sp.IDArt
        LEFT JOIN (
            SELECT sp_oc.IDArt AS id_articulo,
                SUM(COALESCE(sp_oc.cantidad_pendiente,
                    sp_oc.Cantidad - COALESCE(sp_oc.cantidad_entregada, 0))) AS oc_pendiente
            FROM stockp sp_oc
            INNER JOIN cuentaproveedor cp_oc ON cp_oc.CodigoMovimiento = sp_oc.CodigoMovimiento
            WHERE cp_oc.TipoComprobante = 'OC'
                AND (sp_oc.Comprobante = 'OC' OR sp_oc.Comprobante IS NULL)
                AND cp_oc.Estado = 'Pendiente'
                AND cp_oc.Anulado = 'No'
                AND (sp_oc.anulado IS NULL OR sp_oc.anulado = 'No')
                AND (COALESCE(sp_oc.cantidad_pendiente,
                    sp_oc.Cantidad - COALESCE(sp_oc.cantidad_entregada, 0)) > 0)
            GROUP BY sp_oc.IDArt
        ) oc_pendiente_sub ON oc_pendiente_sub.id_articulo = sp.IDArt
        LEFT JOIN (
            SELECT sp_res.IDArt AS id_articulo,
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
            GROUP BY sp_res.IDArt
        ) reservado_sub ON reservado_sub.id_articulo = sp.IDArt
        WHERE cp.TipoComprobante = 'PED'
            AND (sp.Comprobante = 'PED' OR sp.Comprobante IS NULL)
            AND cp.Anulado = 'No'
            AND (sp.anulado IS NULL OR sp.anulado = 'No')
            AND cp.Estado IN ('Pendiente')
            AND sp.CodigoMovimiento IS NOT NULL
            {suc_bo}
            AND sp.Fecha >= %s AND sp.Fecha <= %s
            AND (a.IDArt IS NULL OR a.tipo_art IS NULL OR a.tipo_art <> 'Gasto')
    """
    params_base = params_suc + [fecha_inicio_bo, fecha_fin_bo]

    sql_count = f"""
        SELECT COUNT(*) FROM (
            SELECT sp.IDArt
            {bo_core}
            GROUP BY sp.IDArt
            HAVING SUM(sp.Cantidad) > 0
        ) cnt
    """
    cursor.execute(sql_count, params_base)
    row_count = cursor.fetchone()
    total_registros = int(row_count[0] or 0) if row_count else 0

    sql_sum = f"""
        SELECT COALESCE(SUM(bo_importe), 0) FROM (
            SELECT SUM(sp.PrecioNetoxR) AS bo_importe
            {bo_core}
            GROUP BY sp.IDArt, a.id_manual, a.NombreArticulo, r.NombreRubro,
                sd.stock_total, oc_pendiente_sub.oc_pendiente, reservado_sub.reservado
            HAVING SUM(sp.Cantidad) > 0
        ) t
    """
    cursor.execute(sql_sum, params_base)
    row_sum = cursor.fetchone()
    total_monto = float(row_sum[0] or 0) if row_sum else 0.0

    sql_page = f"""
        SELECT
            sp.IDArt AS id_art,
            a.id_manual AS codigo,
            a.NombreArticulo AS articulo,
            COALESCE(r.NombreRubro, 'Sin Rubro') AS categoria,
            SUM(sp.Cantidad) AS bo_qty,
            SUM(sp.PrecioNetoxR) AS bo_importe,
            COALESCE(sd.stock_total, 0) AS stock_actual,
            COALESCE(reservado_sub.reservado, 0) AS stock_reservado,
            GREATEST(0, COALESCE(sd.stock_total, 0) - COALESCE(reservado_sub.reservado, 0)) AS disponible,
            GREATEST(0, COALESCE(oc_pendiente_sub.oc_pendiente, 0)) AS oc_pendiente
        {bo_core}
        GROUP BY sp.IDArt, a.id_manual, a.NombreArticulo, r.NombreRubro,
            sd.stock_total, oc_pendiente_sub.oc_pendiente, reservado_sub.reservado
        HAVING SUM(sp.Cantidad) > 0
        ORDER BY bo_importe DESC
        LIMIT %s OFFSET %s
    """
    cursor.execute(sql_page, params_base + [filters.limit, filters.offset])
    filas = []
    for row in cursor.fetchall():
        filas.append(
            _enrich_bo_item(
                row[0],
                row[1],
                row[2],
                row[3],
                float(row[4] or 0),
                float(row[5] or 0),
                float(row[6] or 0),
                float(row[7] or 0),
                float(row[8] or 0),
                float(row[9] or 0),
            )
        )

    notas = [
        "Backorder por artículo; PED Pendiente en stockp.Fecha del período.",
        "Cobertura con/sin stock alineada al informe bo-stock-facturacion.",
    ]
    return build_paginated_response(
        filters, filas, total_registros, total_monto, notas_semanticas=notas
    )
