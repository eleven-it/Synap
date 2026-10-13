"""Detalle normalizado de gastos V45 con filtros de fuente y sucursal."""
from __future__ import annotations

from .base import DashboardFilters, build_paginated_response, round_money
from .gastos_v45 import _base


GASTOS_V45_VIEWS = frozenset({"documentos", "grupo", "gasto", "fuente", "sucursal", "dia", "mes"})


def _query(cursor, filters, fuente, view):
    base, params, _ = _base(cursor, filters, fuente)
    if not base:
        return None, [], "", ""
    if view == "documentos":
        sql = (
            "SELECT DATE_FORMAT(x.fecha,'%%Y-%%m-%%d') fecha,x.fuente,x.origen,"
            "x.id_origen,x.grupo,x.gasto,x.sucursal,x.id_pc cuenta_contable,"
            "x.bruto gasto_bruto,x.ajuste nc_ajuste,x.importe gasto_neto "
            f"FROM ({base}) x"
        )
        search_columns = "q.fuente,q.origen,q.grupo,q.gasto,q.sucursal"
        order = "fecha DESC,id_origen DESC"
    else:
        expr = {
            "grupo": "x.grupo", "gasto": "x.gasto", "fuente": "x.fuente",
            "sucursal": "x.sucursal", "dia": "DATE_FORMAT(x.fecha,'%%Y-%%m-%%d')",
            "mes": "DATE_FORMAT(x.fecha,'%%Y-%%m')",
        }[view]
        sql = (
            f"SELECT {expr} agrupacion,COALESCE(SUM(x.importe),0) gasto_neto,"
            "COUNT(DISTINCT CONCAT(x.origen,'|',x.id_origen)) documentos "
            f"FROM ({base}) x GROUP BY {expr}"
        )
        search_columns = "q.agrupacion"
        order = "ABS(q.gasto_neto) DESC,q.agrupacion"
    return sql, params, search_columns, order


def list_gastos_v45_detail(cursor, filters: DashboardFilters, *, fuente: int, view: str) -> dict:
    if fuente not in (0, 1, 2, 3) or view not in GASTOS_V45_VIEWS:
        raise ValueError("Vista o fuente de gastos inválida")
    source, params, search_columns, order = _query(cursor, filters, fuente, view)
    if not source:
        payload = build_paginated_response(filters, [], 0)
        payload["vista"] = view
        return payload
    term = filters.busqueda
    search = ""
    if term:
        fields = search_columns.split(",")
        search = " WHERE (" + " OR ".join(f"CAST({field} AS CHAR) LIKE %s" for field in fields) + ")"
        params += [f"%{term}%"] * len(fields)
    cursor.execute(
        f"SELECT COUNT(*),COALESCE(SUM(q.gasto_neto),0) FROM ({source}) q{search}",
        params,
    )
    row = cursor.fetchone() or (0, 0)
    count, total = int(row[0] or 0), round_money(row[1])
    cursor.execute(
        f"SELECT * FROM ({source}) q{search} ORDER BY {order} LIMIT %s OFFSET %s",
        params + [filters.limit, filters.offset],
    )
    keys = [col[0] for col in cursor.description]
    rows = [dict(zip(keys, row)) for row in cursor.fetchall() or []]
    payload = build_paginated_response(filters, rows, count, total)
    payload["vista"] = view
    return payload
