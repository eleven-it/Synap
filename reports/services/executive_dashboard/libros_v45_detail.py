"""Vistas documentales contables de solo lectura para Libros y estados V45."""
from __future__ import annotations

from .base import DashboardFilters, build_paginated_response
from .contable_v45 import _period, _scope


LIBROS_V45_VIEWS = frozenset({"diario", "mayor", "balance", "resultados"})


def _source(filters, group, view):
    scope, params = _scope(filters, grupo_contable=group)
    if view in ("diario", "mayor"):
        sql = (
            "SELECT DATE_FORMAT(a.fecha_asiento,'%%Y-%%m-%%d') fecha,"
            "a.id_ejercicio ejercicio,a.nro_asiento asiento,"
            "COALESCE(pc.cod_pc,'') codigo_cuenta,COALESCE(pc.descrip_pc,'') cuenta,"
            "COALESCE(a.debe_asiento,0) debe,COALESCE(a.haber_asiento,0) haber,"
            "a.codigo_movimiento movimiento,a.id_sucursal sucursal,a.id_grupo_contable grupo "
            "FROM cont_asiento a LEFT JOIN cont_pc pc ON pc.id_pc=a.id_pc "
            f"WHERE a.fecha_asiento >= %s AND a.fecha_asiento < %s{scope}"
        )
        order = "codigo_cuenta,fecha,ejercicio,asiento" if view == "mayor" else "fecha,ejercicio,asiento,codigo_cuenta"
    elif view == "balance":
        sql = (
            "SELECT COALESCE(pc.cod_pc,'') codigo_cuenta,COALESCE(pc.descrip_pc,'') cuenta,"
            "COALESCE(pc.tipo_cuenta_pc,'') tipo_cuenta,"
            "COALESCE(SUM(a.debe_asiento),0) debe,COALESCE(SUM(a.haber_asiento),0) haber,"
            "GREATEST(COALESCE(SUM(a.debe_asiento-a.haber_asiento),0),0) saldo_deudor,"
            "GREATEST(COALESCE(SUM(a.haber_asiento-a.debe_asiento),0),0) saldo_acreedor "
            "FROM cont_asiento a LEFT JOIN cont_pc pc ON pc.id_pc=a.id_pc "
            f"WHERE a.fecha_asiento >= %s AND a.fecha_asiento < %s{scope} "
            "GROUP BY a.id_pc,pc.cod_pc,pc.descrip_pc,pc.tipo_cuenta_pc"
        )
        order = "codigo_cuenta"
    else:
        sql = (
            "SELECT COALESCE(pc.cod_pc,'') codigo_cuenta,COALESCE(pc.descrip_pc,'') cuenta,"
            "COALESCE(pc.tipo_cuenta_pc,'') tipo_cuenta,"
            "COALESCE(SUM(IF(UPPER(COALESCE(pc.tipo_cuenta_pc,''))='GANANCIA',a.haber_asiento-a.debe_asiento,0)),0) ingresos,"
            "COALESCE(SUM(IF(UPPER(COALESCE(pc.tipo_cuenta_pc,''))='PERDIDA',a.debe_asiento-a.haber_asiento,0)),0) egresos "
            "FROM cont_asiento a JOIN cont_pc pc ON pc.id_pc=a.id_pc "
            f"WHERE a.fecha_asiento >= %s AND a.fecha_asiento < %s{scope} "
            "AND UPPER(COALESCE(pc.anulado,'NO'))<>'SI' "
            "AND UPPER(COALESCE(pc.tipo_cuenta_pc,'')) IN ('GANANCIA','PERDIDA') "
            "GROUP BY a.id_pc,pc.cod_pc,pc.descrip_pc,pc.tipo_cuenta_pc"
        )
        order = "codigo_cuenta"
    return sql, _period(filters) + params, order


def list_libros_v45_detail(cursor, filters: DashboardFilters, *, view: str,
                           grupo_contable: int | None = None) -> dict:
    if view not in LIBROS_V45_VIEWS:
        raise ValueError("Vista contable inválida")
    source, params, order = _source(filters, grupo_contable, view)
    search = ""
    if filters.busqueda:
        search = " WHERE (CAST(q.codigo_cuenta AS CHAR) LIKE %s OR q.cuenta LIKE %s)"
        term = f"%{filters.busqueda}%"
        params += [term, term]
    cursor.execute(f"SELECT COUNT(*) FROM ({source}) q{search}", params)
    row = cursor.fetchone()
    count = int(row[0] or 0) if row else 0
    cursor.execute(
        f"SELECT * FROM ({source}) q{search} ORDER BY {order} LIMIT %s OFFSET %s",
        params + [filters.limit, filters.offset],
    )
    cols = [col[0] for col in cursor.description]
    rows = [dict(zip(cols, row)) for row in cursor.fetchall() or []]
    payload = build_paginated_response(filters, rows, count)
    payload["vista"] = view
    return payload
