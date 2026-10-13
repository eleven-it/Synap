"""Hojas y comprobantes de ruta V45 con filtro territorial obligatorio."""
from __future__ import annotations

from .base import DashboardFilters, build_paginated_response
from .logistica_v45 import _route_date, _range, _scope, POSITIVE_TYPES, CREDIT_TYPES
from .resumen_v45 import _table_exists


LOGISTICA_V45_VIEWS = frozenset({"rutas", "documentos", "por_ruta"})


def _doc_source(filters, date_expr):
    scope, scope_params = _scope(filters)
    positive = ",".join(["%s"] * len(POSITIVE_TYPES))
    credit = ",".join(["%s"] * len(CREDIT_TYPES))
    pv_filter, pv_params = "", []
    if filters.puntos_venta:
        pv_filter += f" AND cc.id_pv IN ({','.join(['%s'] * len(filters.puntos_venta))})"
        pv_params += list(filters.puntos_venta)
    if filters.sucursales_filtro:
        pv_filter += f" AND cc.id_pv IN (SELECT id_punto_venta FROM punto_venta WHERE id_sucursal IN ({','.join(['%s'] * len(filters.sucursales_filtro))}))"
        pv_params += list(filters.sucursales_filtro)
    sql = (
        "SELECT r.id_ruta ruta,COALESCE(r.desc_ruta,'') descripcion_ruta,"
        "UPPER(cc.TipoComprobante) tipo,cc.CodigoMovimiento movimiento,"
        "MAX(cc.Fecha) fecha,MAX(cc.NroComprobante) comprobante,"
        "MAX(COALESCE(c.nombre_cliente,'')) cliente,"
        f"MAX(CASE WHEN UPPER(cc.TipoComprobante) IN ({positive}) THEN COALESCE(cc.ImporteVenta,0) "
        f"WHEN UPPER(cc.TipoComprobante) IN ({credit}) THEN -COALESCE(cc.ImporteVenta,0) ELSE 0 END) importe "
        "FROM (SELECT CodigoMovimiento,MAX(id_ruta) id_ruta FROM cliente_datos_adicionales "
        "WHERE id_ruta IS NOT NULL AND COALESCE(CodigoMovimiento,0)<>0 GROUP BY CodigoMovimiento) d "
        "JOIN logi_hoja_ruta r ON r.id_ruta=d.id_ruta "
        "JOIN cuentacliente cc ON cc.CodigoMovimiento=d.CodigoMovimiento "
        "LEFT JOIN cliente c ON c.Codigo=cc.Codigo "
        f"WHERE {date_expr} >= %s AND {date_expr} < %s "
        "AND UPPER(COALESCE(r.anulado,'NO'))<>'SI' "
        "AND UPPER(COALESCE(cc.Anulado,'NO'))<>'SI' "
        f"AND UPPER(cc.TipoComprobante) IN ({positive},{credit}){pv_filter}{scope} "
        "GROUP BY r.id_ruta,r.desc_ruta,cc.CodigoMovimiento,UPPER(cc.TipoComprobante)"
    )
    params = list(POSITIVE_TYPES) + list(CREDIT_TYPES) + _range(filters)
    params += list(POSITIVE_TYPES) + list(CREDIT_TYPES) + pv_params + scope_params
    return sql, params


def list_logistica_v45_detail(cursor, filters: DashboardFilters, *, view: str) -> dict:
    if view not in LOGISTICA_V45_VIEWS:
        raise ValueError("Vista logística inválida")
    if not _table_exists(cursor, "logi_hoja_ruta"):
        return {"disponible": False, "motivo": "sin_logistica", "filas": []}
    date_expr = _route_date(cursor)
    if not date_expr:
        return {"disponible": False, "motivo": "sin_fecha_ruta", "filas": []}
    if view == "rutas":
        scope, scope_params = _scope(filters)
        source = (
            f"SELECT r.id_ruta ruta,{date_expr} fecha,COALESCE(r.desc_ruta,'') descripcion_ruta,"
            "COALESCE(r.estado_ruta,'') estado,COALESCE(r.rendida,'') rendida,"
            "r.id_chofer chofer,r.id_unidad unidad,"
            "ABS(COALESCE(r.diferencia_rendicion,0)) importe "
            "FROM logi_hoja_ruta r "
            f"WHERE {date_expr} >= %s AND {date_expr} < %s "
            f"AND UPPER(COALESCE(r.anulado,'NO'))<>'SI'{scope}"
        )
        params = _range(filters) + scope_params
        search_fields = ("descripcion_ruta", "estado")
        order = "q.fecha DESC,q.ruta DESC"
    else:
        docs, params = _doc_source(filters, date_expr)
        if view == "documentos":
            source = f"SELECT * FROM ({docs}) d"
            search_fields = ("cliente", "comprobante", "descripcion_ruta")
            order = "q.fecha DESC,q.movimiento DESC"
        else:
            source = (
                "SELECT d.ruta,d.descripcion_ruta,COUNT(*) documentos,"
                f"COALESCE(SUM(d.importe),0) importe FROM ({docs}) d "
                "GROUP BY d.ruta,d.descripcion_ruta"
            )
            search_fields = ("descripcion_ruta",)
            order = "ABS(q.importe) DESC,q.ruta"
    search = ""
    if filters.busqueda:
        search = " WHERE (" + " OR ".join(f"CAST(q.{field} AS CHAR) LIKE %s" for field in search_fields) + ")"
        params += [f"%{filters.busqueda}%"] * len(search_fields)
    cursor.execute(f"SELECT COUNT(*),COALESCE(SUM(q.importe),0) FROM ({source}) q{search}", params)
    count, total = cursor.fetchone() or (0, 0)
    cursor.execute(
        f"SELECT * FROM ({source}) q{search} ORDER BY {order} LIMIT %s OFFSET %s",
        params + [filters.limit, filters.offset],
    )
    fields = [col[0] for col in cursor.description]
    rows = [dict(zip(fields, row)) for row in cursor.fetchall() or []]
    payload = build_paginated_response(filters, rows, int(count or 0), total)
    payload["vista"] = view
    return payload
