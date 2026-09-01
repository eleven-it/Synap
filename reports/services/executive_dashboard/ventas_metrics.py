"""Métricas ventas período — paridad query_runner._get_*_total."""
from __future__ import annotations

from typing import Any, List, Optional

from .base import DashboardFilters, build_meta, build_paginated_response, round_money


def _clientes_vals(clientes_excluidos: Optional[List]) -> list:
    if not clientes_excluidos:
        return []
    out = []
    for c in clientes_excluidos:
        try:
            c_str = str(c).strip()
            if c_str:
                out.append(int(c_str) if c_str.isdigit() else c_str)
        except (ValueError, TypeError):
            continue
    return out


def get_ventas_netas_total(
    cursor,
    fecha_inicio: str,
    fecha_fin: str,
    sucursales: Optional[List[int]] = None,
    puntos_venta: Optional[List[int]] = None,
    clientes_excluidos: Optional[List] = None,
) -> float:
    """@legacy-parity: query_runner.QueryRunnerService._get_ventas_netas_total"""
    where_conditions = [
        "cc.Fecha >= %s",
        "cc.Fecha <= %s",
        "cc.Anulado = 'No'",
        "cc.CodigoMovimiento <> 0",
        "cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM', 'NCA', 'NCB', 'NCC', 'NCE', 'NCM')",
    ]
    params: list = [fecha_inicio, fecha_fin]
    if puntos_venta:
        placeholders = ",".join(["%s"] * len(puntos_venta))
        where_conditions.append(f"cc.id_pv IN ({placeholders})")
        params.extend(puntos_venta)
    if sucursales:
        placeholders = ",".join(["%s"] * len(sucursales))
        where_conditions.append(f"cc.CodSucursal IN ({placeholders})")
        params.extend(sucursales)
    clientes_vals = _clientes_vals(clientes_excluidos)
    if clientes_vals:
        placeholders = ",".join(["%s"] * len(clientes_vals))
        where_conditions.append(f"cc.Codigo NOT IN ({placeholders})")
        params.extend(clientes_vals)
    sql = f"""
        SELECT SUM(CASE
            WHEN cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM') THEN COALESCE(cc.SubtotalDesc, 0)
            WHEN cc.TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM') THEN -COALESCE(cc.SubtotalDesc, 0)
            ELSE 0
        END) AS ventas_netas
        FROM cuentacliente cc
        WHERE {" AND ".join(where_conditions)}
    """
    cursor.execute(sql, params)
    row = cursor.fetchone()
    return float(row[0] or 0) if row else 0.0


def get_remitos_no_facturados_total(
    cursor,
    fecha_inicio: str,
    fecha_fin: str,
    sucursales: Optional[List[int]] = None,
    puntos_venta: Optional[List[int]] = None,
    clientes_excluidos: Optional[List] = None,
) -> float:
    """@legacy-parity: query_runner.QueryRunnerService._get_remitos_no_facturados_total"""
    where_conditions = [
        "cp.Fecha >= %s",
        "cp.Fecha <= %s",
        "cp.TipoComprobante = 'REM'",
        "cp.Anulado = 'No'",
        "cp.Estado = 'Pendiente'",
    ]
    params: list = [fecha_inicio, fecha_fin]
    if puntos_venta:
        placeholders = ",".join(["%s"] * len(puntos_venta))
        where_conditions.append(f"cp.id_pv IN ({placeholders})")
        params.extend(puntos_venta)
    if sucursales:
        placeholders = ",".join(["%s"] * len(sucursales))
        where_conditions.append(f"cp.CodSucursal IN ({placeholders})")
        params.extend(sucursales)
    clientes_vals = _clientes_vals(clientes_excluidos)
    if clientes_vals:
        placeholders = ",".join(["%s"] * len(clientes_vals))
        where_conditions.append(f"cp.Codigo NOT IN ({placeholders})")
        params.extend(clientes_vals)
    sql = f"""
        SELECT SUM(COALESCE(cp.SubtotalDesc, 0)) AS total_remitos
        FROM comp_ped cp
        WHERE {" AND ".join(where_conditions)}
    """
    cursor.execute(sql, params)
    row = cursor.fetchone()
    return float(row[0] or 0) if row else 0.0


def get_pedidos_pendientes_total(
    cursor,
    fecha_inicio: str,
    fecha_fin: str,
    sucursales: Optional[List[int]] = None,
    puntos_venta: Optional[List[int]] = None,
    clientes_excluidos: Optional[List] = None,
    filtrar_por_fecha: bool = True,
) -> float:
    """@legacy-parity: query_runner.QueryRunnerService._get_pedidos_pendientes_total"""
    where_conditions = [
        "cp.TipoComprobante = 'PED'",
        "cp.Anulado = 'No'",
        "cp.Estado IN ('En preparación', 'Preparado')",
    ]
    params: list = []
    if filtrar_por_fecha:
        where_conditions.extend(["cp.Fecha >= %s", "cp.Fecha <= %s"])
        params.extend([fecha_inicio, fecha_fin])
    if puntos_venta:
        placeholders = ",".join(["%s"] * len(puntos_venta))
        where_conditions.append(f"cp.id_pv IN ({placeholders})")
        params.extend(puntos_venta)
    if sucursales:
        placeholders = ",".join(["%s"] * len(sucursales))
        where_conditions.append(f"cp.CodSucursal IN ({placeholders})")
        params.extend(sucursales)
    clientes_vals = _clientes_vals(clientes_excluidos)
    if clientes_vals:
        placeholders = ",".join(["%s"] * len(clientes_vals))
        where_conditions.append(f"cp.Codigo NOT IN ({placeholders})")
        params.extend(clientes_vals)
    sql = f"""
        SELECT SUM(COALESCE(cp.SubtotalDesc, 0)) AS total_pedidos
        FROM comp_ped cp
        WHERE {" AND ".join(where_conditions)}
    """
    cursor.execute(sql, params)
    row = cursor.fetchone()
    return float(row[0] or 0) if row else 0.0


def _where_pedidos_pendientes(filters: DashboardFilters) -> tuple[str, list]:
    where_conditions = [
        "cp.Fecha >= %s",
        "cp.Fecha <= %s",
        "cp.TipoComprobante = 'PED'",
        "cp.Anulado = 'No'",
        "cp.Estado IN ('En preparación', 'Preparado')",
    ]
    params: list = [filters.fecha_inicio_str, filters.fecha_fin_str]
    if filters.sucursales:
        ph = ",".join(["%s"] * len(filters.sucursales))
        where_conditions.append(f"cp.CodSucursal IN ({ph})")
        params.extend(filters.sucursales)
    if filters.puntos_venta:
        ph_pv = ",".join(["%s"] * len(filters.puntos_venta))
        where_conditions.append(f"cp.id_pv IN ({ph_pv})")
        params.extend(filters.puntos_venta)
    return " AND ".join(where_conditions), params


def _where_remitos_no_facturados(filters: DashboardFilters) -> tuple[str, list]:
    where_conditions = [
        "cp.Fecha >= %s",
        "cp.Fecha <= %s",
        "cp.TipoComprobante = 'REM'",
        "cp.Anulado = 'No'",
        "cp.Estado = 'Pendiente'",
    ]
    params: list = [filters.fecha_inicio_str, filters.fecha_fin_str]
    if filters.sucursales:
        ph = ",".join(["%s"] * len(filters.sucursales))
        where_conditions.append(f"cp.CodSucursal IN ({ph})")
        params.extend(filters.sucursales)
    if filters.puntos_venta:
        ph_pv = ",".join(["%s"] * len(filters.puntos_venta))
        where_conditions.append(f"cp.id_pv IN ({ph_pv})")
        params.extend(filters.puntos_venta)
    return " AND ".join(where_conditions), params


def _row_to_comp_ped_dict(columns: list[str], row: tuple) -> dict:
    d = dict(zip(columns, row))
    if "subtotal_desc" in d:
        d["subtotal_desc"] = round_money(float(d.get("subtotal_desc") or 0))
    if "codigo_movimiento" in d and d["codigo_movimiento"] is not None:
        d["codigo_movimiento"] = int(d["codigo_movimiento"])
    if "codigo_cliente" in d and d["codigo_cliente"] is not None:
        try:
            d["codigo_cliente"] = int(d["codigo_cliente"])
        except (TypeError, ValueError):
            pass
    return d


def list_pedidos_pendientes(cursor, filters: DashboardFilters) -> dict[str, Any]:
    """Detalle paginado PED En preparación/Preparado en período."""
    where_clause, params = _where_pedidos_pendientes(filters)
    sql_count = f"""
        SELECT COUNT(*), COALESCE(SUM(COALESCE(cp.SubtotalDesc, 0)), 0)
        FROM comp_ped cp
        WHERE {where_clause}
    """
    cursor.execute(sql_count, params)
    row_count = cursor.fetchone()
    total_registros = int(row_count[0] or 0) if row_count else 0
    total_monto = float(row_count[1] or 0) if row_count else 0.0

    sql = f"""
        SELECT
            cp.CodigoMovimiento AS codigo_movimiento,
            cp.NroComprobante AS nro_comprobante,
            DATE_FORMAT(cp.Fecha, '%%d/%%m/%%Y') AS fecha,
            cp.Codigo AS codigo_cliente,
            COALESCE(cli.nombre_cliente, '') AS nombre_cliente,
            cp.Estado AS estado,
            COALESCE(cp.SubtotalDesc, 0) AS subtotal_desc
        FROM comp_ped cp
        LEFT JOIN cliente cli ON cli.codigo = cp.Codigo
        WHERE {where_clause}
        ORDER BY cp.Fecha DESC, cp.NroComprobante ASC
        LIMIT %s OFFSET %s
    """
    cursor.execute(sql, params + [filters.limit, filters.offset])
    cols = [d[0] for d in cursor.description]
    filas = [_row_to_comp_ped_dict(cols, r) for r in cursor.fetchall()]
    notas = [
        "Pedidos PED En preparación/Preparado filtrados por fecha del período.",
    ]
    return build_paginated_response(
        filters, filas, total_registros, total_monto, notas_semanticas=notas
    )


def list_remitos_no_facturados(cursor, filters: DashboardFilters) -> dict[str, Any]:
    """Detalle paginado REM Pendiente en período."""
    where_clause, params = _where_remitos_no_facturados(filters)
    sql_count = f"""
        SELECT COUNT(*), COALESCE(SUM(COALESCE(cp.SubtotalDesc, 0)), 0)
        FROM comp_ped cp
        WHERE {where_clause}
    """
    cursor.execute(sql_count, params)
    row_count = cursor.fetchone()
    total_registros = int(row_count[0] or 0) if row_count else 0
    total_monto = float(row_count[1] or 0) if row_count else 0.0

    sql = f"""
        SELECT
            cp.CodigoMovimiento AS codigo_movimiento,
            cp.NroComprobante AS nro_comprobante,
            DATE_FORMAT(cp.Fecha, '%%d/%%m/%%Y') AS fecha,
            cp.Codigo AS codigo_cliente,
            COALESCE(cli.nombre_cliente, '') AS nombre_cliente,
            cp.Estado AS estado,
            COALESCE(cp.SubtotalDesc, 0) AS subtotal_desc
        FROM comp_ped cp
        LEFT JOIN cliente cli ON cli.codigo = cp.Codigo
        WHERE {where_clause}
        ORDER BY cp.Fecha DESC, cp.NroComprobante ASC
        LIMIT %s OFFSET %s
    """
    cursor.execute(sql, params + [filters.limit, filters.offset])
    cols = [d[0] for d in cursor.description]
    filas = [_row_to_comp_ped_dict(cols, r) for r in cursor.fetchall()]
    notas = ["Remitos REM con Estado=Pendiente en el período."]
    return build_paginated_response(
        filters, filas, total_registros, total_monto, notas_semanticas=notas
    )


def fetch_ventas_resumen(cursor, filters: DashboardFilters) -> dict[str, Any]:
    suc = filters.sucursales
    pv = list(filters.puntos_venta) if filters.puntos_venta else None
    fi, ff = filters.fecha_inicio_str, filters.fecha_fin_str
    ventas_netas = get_ventas_netas_total(cursor, fi, ff, sucursales=suc, puntos_venta=pv)
    remitos = get_remitos_no_facturados_total(cursor, fi, ff, sucursales=suc, puntos_venta=pv)
    pedidos = get_pedidos_pendientes_total(
        cursor, fi, ff, sucursales=suc, puntos_venta=pv, filtrar_por_fecha=True
    )
    total_operativo = ventas_netas + remitos + pedidos
    notas = [
        "Ventas netas: facturación FA–NC (SubtotalDesc) en el período.",
        "Pedidos pendientes: PED En preparación/Preparado filtrados por fecha del período.",
        "Para ventas intradía, series y margen use GET /api/reports/executive-summary/.",
    ]
    return {
        "ventas_netas": round_money(ventas_netas),
        "remitos_no_facturados_monto": round_money(remitos),
        "pedidos_pendientes_monto": round_money(pedidos),
        "total_operativo": round_money(total_operativo),
        "pedidos_pendientes_cantidad": None,
        "disponible": True,
        "meta": build_meta(filters, notas_semanticas=notas),
    }
