"""Hojas de ruta V45 según modCM_LogisticaDatos.bas."""
from __future__ import annotations

from datetime import timedelta

from .base import DashboardFilters, build_meta, round_money
from .resumen_v45 import _table_exists


LOGISTICA_V45_KEYS = (
    "hojas_ruta", "rutas_abiertas", "rutas_cerradas", "rutas_rendidas",
    "pendientes_rendir", "documentos_valorizados", "facturas_ruta", "notas_credito",
    "facturacion_rutas", "promedio_ruta", "promedio_factura", "choferes",
    "unidades", "diferencia_rendicion",
)
POSITIVE_TYPES = ("FA", "FB", "FC", "FE", "FM", "ND", "NDA", "NDB", "NDC", "NDE", "NDM")
INVOICE_TYPES = ("FA", "FB", "FC", "FE", "FM")
CREDIT_TYPES = ("NC", "NCA", "NCB", "NCC", "NCE", "NCM")


def _column_exists(cursor, table, column):
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() "
        "AND table_name=%s AND column_name=%s", [table, column],
    )
    row = cursor.fetchone()
    return bool(row and row[0])


def _route_date(cursor):
    departure = _column_exists(cursor, "logi_hoja_ruta", "fecha_salida")
    creation = _column_exists(cursor, "logi_hoja_ruta", "fecha_hora_creac")
    if departure and creation:
        return "DATE(COALESCE(r.fecha_salida,r.fecha_hora_creac))"
    if departure:
        return "DATE(r.fecha_salida)"
    if creation:
        return "DATE(r.fecha_hora_creac)"
    return None


def _scope(filters):
    # A route may contain several documents. With a PV/branch filter it is
    # included only if at least one linked document belongs to that scope.
    if not filters.puntos_venta and not filters.sucursales_filtro:
        return "", []
    joins = ""
    clauses = []
    params = []
    if filters.puntos_venta:
        clauses.append(f"cc.id_pv IN ({','.join(['%s'] * len(filters.puntos_venta))})")
        params.extend(filters.puntos_venta)
    if filters.sucursales_filtro:
        joins = " JOIN punto_venta pv ON pv.id_punto_venta=cc.id_pv"
        clauses.append(f"pv.id_sucursal IN ({','.join(['%s'] * len(filters.sucursales_filtro))})")
        params.extend(filters.sucursales_filtro)
    return (
        " AND EXISTS (SELECT 1 FROM cliente_datos_adicionales d "
        "JOIN cuentacliente cc ON cc.CodigoMovimiento=d.CodigoMovimiento"
        f"{joins} WHERE d.id_ruta=r.id_ruta AND {' AND '.join(clauses)})",
        params,
    )


def _range(filters):
    return [filters.fecha_inicio_str, (filters.fecha_fin + timedelta(days=1)).isoformat()]


def _route_counts(cursor, filters, date_expr, *, previous=False):
    if previous:
        span = (filters.fecha_fin - filters.fecha_inicio).days + 1
        params = [(filters.fecha_inicio - timedelta(days=span)).isoformat(), filters.fecha_inicio_str]
    else:
        params = _range(filters)
    scope, scope_params = _scope(filters)
    open_state = "UPPER(TRIM(COALESCE(r.estado_ruta,''))) LIKE 'ABIER%'"
    closed = "UPPER(TRIM(COALESCE(r.estado_ruta,''))) IN ('CERRADO','CERRADA','FINALIZADO','FINALIZADA')"
    rendered = "UPPER(COALESCE(r.rendida,'NO'))='SI'"
    has_drivers = _table_exists(cursor, "logi_ruta_chofer")
    driver = "0" if has_drivers else "COUNT(DISTINCT NULLIF(UPPER(TRIM(r.descripcion_chofer)),''))"
    cursor.execute(
        "SELECT COUNT(*),"
        f"COALESCE(SUM(IF({open_state},1,0)),0),"
        f"COALESCE(SUM(IF({closed},1,0)),0),"
        f"COALESCE(SUM(IF({rendered},1,0)),0),"
        f"COALESCE(SUM(IF({closed} AND NOT({rendered}),1,0)),0),"
        f"{driver},COUNT(DISTINCT r.id_unidad),"
        "COALESCE(SUM(ABS(COALESCE(r.diferencia_rendicion,0))),0) "
        f"FROM logi_hoja_ruta r WHERE {date_expr} >= %s AND {date_expr} < %s "
        f"AND UPPER(COALESCE(r.anulado,'NO'))<>'SI'{scope}", params + scope_params,
    )
    count, opened, closed_count, rendered_count, pending, drivers, units, difference = cursor.fetchone() or (0,) * 8
    if has_drivers and not previous:
        cursor.execute(
            "SELECT COUNT(DISTINCT rc.id_chofer) FROM logi_ruta_chofer rc "
            "JOIN logi_hoja_ruta r ON r.id_ruta=rc.id_ruta "
            f"WHERE {date_expr} >= %s AND {date_expr} < %s "
            f"AND UPPER(COALESCE(r.anulado,'NO'))<>'SI' "
            f"AND rc.id_chofer IS NOT NULL AND COALESCE(rc.id_chofer,0)<>0{scope}",
            params + scope_params,
        )
        row = cursor.fetchone()
        drivers = row[0] if row else 0
    return {
        "hojas_ruta": int(count), "rutas_abiertas": int(opened),
        "rutas_cerradas": int(closed_count), "rutas_rendidas": int(rendered_count),
        "pendientes_rendir": int(pending), "choferes": int(drivers),
        "unidades": int(units), "diferencia_rendicion": round_money(difference),
    }


def _documents(cursor, filters, date_expr):
    if not _table_exists(cursor, "cliente_datos_adicionales") or not _table_exists(cursor, "cuentacliente"):
        return None
    scope, params = _scope(filters)
    positive = ",".join(["%s"] * len(POSITIVE_TYPES))
    invoice = ",".join(["%s"] * len(INVOICE_TYPES))
    credit = ",".join(["%s"] * len(CREDIT_TYPES))
    pv_scope = ""
    pv_params = []
    if filters.puntos_venta:
        pv_scope += f" AND cc.id_pv IN ({','.join(['%s'] * len(filters.puntos_venta))})"
        pv_params += list(filters.puntos_venta)
    if filters.sucursales_filtro:
        pv_scope += f" AND cc.id_pv IN (SELECT id_punto_venta FROM punto_venta WHERE id_sucursal IN ({','.join(['%s'] * len(filters.sucursales_filtro))}))"
        pv_params += list(filters.sucursales_filtro)
    cursor.execute(
        f"SELECT COUNT(*),COALESCE(SUM(IF(x.tipo IN ({invoice}),1,0)),0),"
        f"COALESCE(SUM(IF(x.tipo IN ({credit}),1,0)),0),"
        f"COALESCE(SUM(CASE WHEN x.tipo IN ({positive}) THEN x.importe "
        f"WHEN x.tipo IN ({credit}) THEN -x.importe ELSE 0 END),0) FROM ("
        "SELECT UPPER(cc.TipoComprobante) tipo,MAX(COALESCE(cc.ImporteVenta,0)) importe,cc.CodigoMovimiento "
        "FROM (SELECT CodigoMovimiento,MAX(id_ruta) id_ruta FROM cliente_datos_adicionales "
        "WHERE id_ruta IS NOT NULL AND COALESCE(CodigoMovimiento,0)<>0 GROUP BY CodigoMovimiento) d "
        "JOIN logi_hoja_ruta r ON r.id_ruta=d.id_ruta "
        "JOIN cuentacliente cc ON cc.CodigoMovimiento=d.CodigoMovimiento "
        f"WHERE {date_expr} >= %s AND {date_expr} < %s "
        "AND UPPER(COALESCE(r.anulado,'NO'))<>'SI' "
        "AND UPPER(COALESCE(cc.Anulado,'NO'))<>'SI' "
        f"AND UPPER(cc.TipoComprobante) IN ({positive},{credit}){pv_scope}{scope} "
        "GROUP BY cc.CodigoMovimiento,UPPER(cc.TipoComprobante)) x",
        list(INVOICE_TYPES) + list(CREDIT_TYPES) + list(POSITIVE_TYPES) + list(CREDIT_TYPES)
        + _range(filters) + list(POSITIVE_TYPES) + list(CREDIT_TYPES) + pv_params + params,
    )
    docs, invoices, credits, amount = cursor.fetchone() or (0, 0, 0, 0)
    return {"documentos_valorizados": int(docs), "facturas_ruta": int(invoices),
            "notas_credito": int(credits), "facturacion_rutas": round_money(amount)}


def fetch_logistica_v45(cursor, filters: DashboardFilters) -> dict:
    if not _table_exists(cursor, "logi_hoja_ruta"):
        return {"disponible": False, "motivo": "sin_logistica", "kpis": {}}
    date_expr = _route_date(cursor)
    if not date_expr:
        return {"disponible": False, "motivo": "sin_fecha_ruta", "kpis": {}}
    counts = _route_counts(cursor, filters, date_expr)
    previous = _route_counts(cursor, filters, date_expr, previous=True)
    docs = _documents(cursor, filters, date_expr)
    kpis = {**counts, **(docs or {key: None for key in ("documentos_valorizados", "facturas_ruta", "notas_credito", "facturacion_rutas")})}
    amount = kpis["facturacion_rutas"]
    kpis["promedio_ruta"] = round_money(amount / counts["hojas_ruta"]) if amount is not None and counts["hojas_ruta"] else None
    kpis["promedio_factura"] = round_money(amount / kpis["facturas_ruta"]) if amount is not None and kpis["facturas_ruta"] else None
    return {
        "disponible": True, "kpis": kpis,
        "comparacion": {key: previous[key] for key in ("hojas_ruta", "rutas_abiertas", "rutas_cerradas", "rutas_rendidas", "pendientes_rendir")},
        "meta": build_meta(filters, fuente="modCM_LogisticaDatos.bas/V45"),
    }
