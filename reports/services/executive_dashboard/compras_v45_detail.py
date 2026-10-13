"""Aperturas documentales de Compras V45, con la misma base que sus KPI."""
from __future__ import annotations

from .base import DashboardFilters, build_paginated_response, round_money
from .compras_v45 import _dates, _has, _scope


COMPRAS_V45_VIEWS = frozenset({
    "comprobantes", "proveedores", "ordenes", "ordenes_abiertas", "remitos",
})


def _source(filters: DashboardFilters, view: str) -> tuple[str, list, tuple[str, ...], str]:
    scope, scope_params = _scope("cp", filters)
    period = view != "ordenes_abiertas"
    dates = _dates(filters) if period else []
    where_date = "cp.Fecha >= %s AND cp.Fecha < %s AND " if period else ""
    kinds = {
        "comprobantes": "'FA','FB','FC','FE','FM','NC','ND'",
        "proveedores": "'FA','FB','FC','FE','FM','NC','ND'",
        "ordenes": "'OC'",
        "ordenes_abiertas": "'OC'",
        "remitos": "'REM'",
    }[view]
    state = (
        " AND UPPER(COALESCE(cp.Estado,'')) IN ('PENDIENTE','PARCIAL','EN REMITO')"
        if view == "ordenes_abiertas" else ""
    )
    base = (
        " FROM cuentaproveedor cp LEFT JOIN proveedor p ON p.Codigo=cp.Codigo "
        f"WHERE {where_date}cp.CodigoMovimiento<>0 AND cp.Anulado='No' "
        f"AND cp.TipoComprobante IN ({kinds}){state}{scope}"
    )
    net = (
        "CASE WHEN cp.TipoComprobante='NC' THEN -COALESCE(cp.SubtotalDesc,0) "
        "ELSE COALESCE(cp.SubtotalDesc,0) END"
    )
    if view == "proveedores":
        query = (
            "SELECT cp.Codigo codigo_proveedor,COALESCE(p.Nombre,'') proveedor,"
            f"COUNT(*) comprobantes,COALESCE(SUM({net}),0) importe_neto"
            + base + " GROUP BY cp.Codigo,p.Nombre"
        )
        search = ("q.proveedor", "q.codigo_proveedor")
        order = "ABS(q.importe_neto) DESC,q.proveedor"
    else:
        query = (
            "SELECT DATE_FORMAT(cp.Fecha,'%%Y-%%m-%%d') fecha,"
            "cp.CodigoMovimiento movimiento,cp.TipoComprobante tipo,"
            "COALESCE(cp.NroComprobante,'') comprobante,"
            "cp.Codigo codigo_proveedor,COALESCE(p.Nombre,'') proveedor,"
            "cp.CodSucursal sucursal,COALESCE(cp.Estado,'') estado,"
            "DATE_FORMAT(cp.fecha_entrega_oc,'%%Y-%%m-%%d') entrega_oc,"
            f"{net} importe_neto"
            + base
        )
        search = ("q.comprobante", "q.proveedor", "q.movimiento", "q.estado")
        order = "q.fecha DESC,q.movimiento DESC"
    return query, dates + scope_params, search, order


def list_compras_v45_detail(cursor, filters: DashboardFilters, *, view: str) -> dict:
    if view not in COMPRAS_V45_VIEWS:
        raise ValueError("Vista de compras inválida")
    if not _has(cursor, "cuentaproveedor") or not _has(cursor, "proveedor"):
        payload = build_paginated_response(filters, [], 0)
        payload["vista"] = view
        payload["disponible"] = False
        return payload
    source, params, columns, order = _source(filters, view)
    search = ""
    if filters.busqueda:
        search = " WHERE (" + " OR ".join(
            f"CAST({column} AS CHAR) LIKE %s" for column in columns
        ) + ")"
        params += [f"%{filters.busqueda}%"] * len(columns)
    cursor.execute(
        f"SELECT COUNT(*),COALESCE(SUM(q.importe_neto),0) FROM ({source}) q{search}",
        params,
    )
    count, amount = cursor.fetchone() or (0, 0)
    cursor.execute(
        f"SELECT * FROM ({source}) q{search} ORDER BY {order} LIMIT %s OFFSET %s",
        params + [filters.limit, filters.offset],
    )
    columns = [field[0] for field in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall() or []]
    payload = build_paginated_response(filters, rows, int(count or 0), round_money(amount))
    payload["vista"] = view
    payload.setdefault("meta", {})["alcance"] = (
        "Todas las OC abiertas" if view == "ordenes_abiertas" else "Período seleccionado"
    )
    return payload
