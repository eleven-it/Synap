"""Hojas y comprobantes de ruta V45 con filtro territorial obligatorio."""
from __future__ import annotations

from .base import DashboardFilters, build_paginated_response
from .logistica_v45 import _route_date, _range, _scope, POSITIVE_TYPES, CREDIT_TYPES
from .resumen_v45 import _table_exists


LOGISTICA_V45_VIEWS = frozenset({
    "rutas", "documentos", "por_ruta", "por_chofer", "por_unidad", "por_zona",
})


def _route_dimension(cursor, filters, view, date_expr):
    scope, scope_params = _scope(filters)
    base = (
        f"SELECT r.id_ruta,r.id_chofer,r.id_unidad,r.id_zona,r.descripcion_chofer,r.descripcion_zona "
        f"FROM logi_hoja_ruta r WHERE {date_expr} >= %s AND {date_expr} < %s "
        f"AND UPPER(COALESCE(r.anulado,'NO'))<>'SI'{scope}"
    )
    params = _range(filters) + scope_params
    if view == "por_chofer":
        links = (
            "(SELECT id_ruta,id_chofer FROM logi_ruta_chofer WHERE COALESCE(id_chofer,0)<>0 "
            "UNION SELECT id_ruta,id_chofer FROM logi_hoja_ruta WHERE COALESCE(id_chofer,0)<>0)"
            if _table_exists(cursor, "logi_ruta_chofer")
            else "(SELECT id_ruta,id_chofer FROM logi_hoja_ruta WHERE COALESCE(id_chofer,0)<>0)"
        )
        source = (
            "SELECT l.id_chofer codigo,COALESCE(NULLIF(ch.nombre_chofer,''),"
            "NULLIF(MAX(r.descripcion_chofer),''),CONCAT('Chofer ',l.id_chofer)) nombre,"
            f"COUNT(DISTINCT r.id_ruta) rutas FROM ({base}) r "
            f"JOIN {links} l ON l.id_ruta=r.id_ruta "
            "LEFT JOIN logi_abm_chofer ch ON ch.id_chofer=l.id_chofer "
            "GROUP BY l.id_chofer,ch.nombre_chofer"
        )
    elif view == "por_unidad":
        source = (
            "SELECT r.id_unidad codigo,COALESCE(NULLIF(u.nombre_unidad,''),"
            "CONCAT('Unidad ',r.id_unidad)) nombre,"
            f"COUNT(DISTINCT r.id_ruta) rutas FROM ({base}) r "
            "LEFT JOIN logi_unidad u ON u.id_unidad=r.id_unidad "
            "WHERE COALESCE(r.id_unidad,0)<>0 GROUP BY r.id_unidad,u.nombre_unidad"
        )
    else:
        links = (
            "(SELECT id_ruta,id_zona FROM logi_ruta_zona WHERE COALESCE(id_zona,0)<>0 "
            "UNION SELECT id_ruta,id_zona FROM logi_hoja_ruta WHERE COALESCE(id_zona,0)<>0)"
            if _table_exists(cursor, "logi_ruta_zona")
            else "(SELECT id_ruta,id_zona FROM logi_hoja_ruta WHERE COALESCE(id_zona,0)<>0)"
        )
        source = (
            "SELECT l.id_zona codigo,COALESCE(NULLIF(z.nombre_zona,''),"
            "CONCAT('Zona ',l.id_zona)) nombre,"
            f"COUNT(DISTINCT r.id_ruta) rutas FROM ({base}) r "
            f"JOIN {links} l ON l.id_ruta=r.id_ruta "
            "LEFT JOIN logi_zona z ON z.id_zona=l.id_zona "
            "GROUP BY l.id_zona,z.nombre_zona"
        )
    return source, params


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
    if view in {"por_chofer", "por_unidad", "por_zona"}:
        catalog = {
            "por_chofer": "logi_abm_chofer",
            "por_unidad": "logi_unidad",
            "por_zona": "logi_zona",
        }[view]
        if not _table_exists(cursor, catalog):
            return {"disponible": False, "motivo": "tabla_faltante", "filas": []}
        source, params = _route_dimension(cursor, filters, view, date_expr)
        search_fields = ("nombre", "codigo")
        order = "q.rutas DESC,q.nombre"
    elif view == "rutas":
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
    amount = "COALESCE(SUM(q.importe),0)" if view not in {"por_chofer", "por_unidad", "por_zona"} else "NULL"
    cursor.execute(f"SELECT COUNT(*),{amount} FROM ({source}) q{search}", params)
    count, total = cursor.fetchone() or (0, 0)
    cursor.execute(
        f"SELECT * FROM ({source}) q{search} ORDER BY {order} LIMIT %s OFFSET %s",
        params + [filters.limit, filters.offset],
    )
    fields = [col[0] for col in cursor.description]
    rows = [dict(zip(fields, row)) for row in cursor.fetchall() or []]
    payload = build_paginated_response(filters, rows, int(count or 0), total)
    payload["vista"] = view
    if view in {"por_chofer", "por_unidad", "por_zona"}:
        payload["meta"]["alcance"] = (
            "Una ruta puede tener varios choferes o zonas; cada asignación cuenta "
            "en su dimensión y la suma de grupos puede superar las rutas únicas."
        )
    return payload
