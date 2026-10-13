"""Aperturas documentales fiscales V45 con el mismo alcance que los KPI."""
from __future__ import annotations

from .base import DashboardFilters, build_paginated_response
from .impositivo_v45 import SALES_TYPES, PURCHASE_TYPES, NC_TYPES, _dates
from .resumen_v45 import _table_exists


IMPOSITIVO_V45_VIEWS = frozenset({"ventas", "compras", "percepciones", "retenciones", "determinados", "pagados"})


def _scope(filters, *, sales=False, purchase=False, expense=False):
    alias = "cc" if sales else "cp" if purchase else "oe"
    field = "id_pv" if sales else "CodSucursal" if purchase else "id_sucursal"
    clauses, values = [], []
    if filters.puntos_venta:
        if sales:
            clauses.append(f"{alias}.{field} IN ({','.join(['%s'] * len(filters.puntos_venta))})")
        else:
            clauses.append(f"{alias}.{field} IN (SELECT id_sucursal FROM punto_venta WHERE id_punto_venta IN ({','.join(['%s'] * len(filters.puntos_venta))}))")
        values += list(filters.puntos_venta)
    if filters.sucursales_filtro:
        if sales:
            clauses.append(f"{alias}.{field} IN (SELECT id_punto_venta FROM punto_venta WHERE id_sucursal IN ({','.join(['%s'] * len(filters.sucursales_filtro))}))")
        else:
            clauses.append(f"{alias}.{field} IN ({','.join(['%s'] * len(filters.sucursales_filtro))})")
        values += list(filters.sucursales_filtro)
    return (" AND " + " AND ".join(clauses) if clauses else ""), values


def _source(filters, view):
    nc = ",".join(["%s"] * len(NC_TYPES))
    if view == "ventas":
        scope, values = _scope(filters, sales=True)
        types = ",".join(["%s"] * len(SALES_TYPES))
        sql = (
            "SELECT cc.Fecha fecha,cc.CodigoMovimiento movimiento,cc.TipoComprobante tipo,"
            "cc.NroComprobante comprobante,COALESCE(c.nombre_cliente,'') entidad,"
            f"IF(cc.TipoComprobante IN ({nc}),-1,1)*(COALESCE(cc.IVA1,0)+COALESCE(cc.IVA2,0)) importe,"
            f"IF(cc.TipoComprobante IN ({nc}),-1,1)*(COALESCE(cc.IG1,0)+COALESCE(cc.IG2,0)) iibb,"
            "COALESCE(cc.SubtotalDesc,0) neto,COALESCE(cc.Exento,0) exento "
            "FROM cuentacliente cc LEFT JOIN cliente c ON c.Codigo=cc.Codigo "
            f"WHERE cc.Fecha >= %s AND cc.Fecha < %s AND cc.TipoComprobante IN ({types}) "
            f"AND COALESCE(cc.CodigoMovimiento,0)<>0 AND UPPER(COALESCE(cc.Anulado,'NO'))<>'SI'{scope}"
        )
        return sql, list(NC_TYPES) * 2 + _dates(filters) + list(SALES_TYPES) + values
    if view == "compras":
        scope, values = _scope(filters, purchase=True)
        types = ",".join(["%s"] * len(PURCHASE_TYPES))
        sql = (
            "SELECT cp.FechaRegistro fecha,cp.CodigoMovimiento movimiento,cp.TipoComprobante tipo,"
            "cp.NroComprobante comprobante,COALESCE(p.Nombre,'') entidad,"
            f"IF(cp.TipoComprobante IN ({nc}),-1,1)*(COALESCE(cp.IVA1,0)+COALESCE(cp.IVA2,0)+COALESCE(cp.IVA3,0)+COALESCE(cp.sobretasa_iva,0)) importe,"
            f"IF(cp.TipoComprobante IN ({nc}),-1,1)*COALESCE(cp.PercepIVA,0) percepcion_iva,"
            f"IF(cp.TipoComprobante IN ({nc}),-1,1)*(COALESCE(cp.PercepIB,0)+COALESCE(cp.PercepIB_Prov,0)) percepcion_iibb,"
            "COALESCE(cp.SubtotalDesc,0) neto,COALESCE(cp.Exento,0) exento "
            "FROM cuentaproveedor cp LEFT JOIN proveedor p ON p.Codigo=cp.Codigo "
            f"WHERE cp.FechaRegistro >= %s AND cp.FechaRegistro < %s AND cp.TipoComprobante IN ({types}) "
            "AND COALESCE(cp.CodigoMovimiento,0)<>0 AND UPPER(COALESCE(cp.Anulado,'NO'))<>'SI' "
            f"AND UPPER(COALESCE(cp.motivo_nd,''))<>'CHEQUE RECHAZADO' AND UPPER(COALESCE(p.Tipo,''))<>'PROFESIONAL'{scope}"
        )
        return sql, list(NC_TYPES) * 3 + _dates(filters) + list(PURCHASE_TYPES) + values
    if view == "percepciones":
        scope, values = _scope(filters, sales=True)
        types = ",".join(["%s"] * len(SALES_TYPES))
        sql = (
            "SELECT cc.Fecha fecha,cc.CodigoMovimiento movimiento,cc.TipoComprobante tipo,"
            "cc.NroComprobante comprobante,COALESCE(c.nombre_cliente,'') entidad,"
            "ab.id_percep_cli_abm impuesto,"
            f"IF(cc.TipoComprobante IN ({nc}),-1,1)*COALESCE(pc.importe_percep_cli,0) importe "
            "FROM percep_cli pc JOIN percep_cli_tipo pt ON pt.id_percep_cli_tipo=pc.id_percep_cli_tipo "
            "JOIN percep_cli_abm ab ON ab.id_percep_cli_abm=pt.id_percep_cli_abm "
            "JOIN cuentacliente cc ON cc.CodigoMovimiento=pc.codigo_movimiento "
            "LEFT JOIN cliente c ON c.Codigo=cc.Codigo "
            f"WHERE cc.Fecha >= %s AND cc.Fecha < %s AND cc.TipoComprobante IN ({types}) "
            "AND COALESCE(cc.CodigoMovimiento,0)<>0 AND UPPER(COALESCE(cc.Anulado,'NO'))<>'SI' "
            "AND UPPER(COALESCE(pc.anulado,'NO'))<>'SI' "
            f"AND UPPER(COALESCE(pc.tipo_comp,'')) NOT IN ('PED','PRE'){scope}"
        )
        return sql, list(NC_TYPES) + _dates(filters) + list(SALES_TYPES) + values
    if view == "retenciones":
        joins, scope, values = "", "", []
        if filters.puntos_venta or filters.sucursales_filtro:
            joins = " JOIN cuentacliente cc ON cc.CodigoMovimiento=r.codigo_movimiento"
            scope, values = _scope(filters, sales=True)
        sql = (
            "SELECT r.Fecha fecha,r.codigo_movimiento movimiento,r.tipo_retencion tipo,"
            "CAST(r.NroCertificado AS CHAR) comprobante,COALESCE(c.nombre_cliente,'') entidad,"
            "tr.id_impuesto impuesto,COALESCE(r.Importe,0) importe "
            "FROM retenciones r LEFT JOIN tipo_retencion_cli tr ON tr.CodRetencion=r.CodRetencion "
            "LEFT JOIN cliente c ON c.Codigo=r.CodCliente"
            f"{joins} WHERE r.Fecha >= %s AND r.Fecha < %s "
            f"AND UPPER(COALESCE(r.Anulado,'NO'))<>'SI'{scope}"
        )
        return sql, _dates(filters) + values
    if view == "determinados":
        return (
            "SELECT d.fechasta_impdetalle fecha,d.id_impuesto_detalle movimiento,"
            "COALESCE(d.Tipo_saldo,'') tipo,CAST(d.id_periodo AS CHAR) comprobante,"
            "COALESCE(d.detalle_impdetalle,'') entidad,d.id_impuesto impuesto,"
            "COALESCE(d.estado_impdetalle,'') estado,d.vencimiento_impdetalle vencimiento,"
            "COALESCE(d.importe_impdetalle,0) importe FROM impuesto_detalle d "
            "WHERE d.fechasta_impdetalle >= %s AND d.fechasta_impdetalle < %s "
            "AND UPPER(COALESCE(d.anulado,'NO'))<>'SI'",
            _dates(filters),
        )
    scope, values = _scope(filters, expense=True)
    return (
        "SELECT oe.fecha_oe fecha,oe.id_oe movimiento,COALESCE(oe.tipo_oe,'') tipo,"
        "COALESCE(oe.tipo_comp,'') comprobante,COALESCE(oe.nombre_oe,'') entidad,"
        "oe.id_impuesto impuesto,COALESCE(oe.detalle_oe,'') detalle,"
        "COALESCE(oe.importe_oe,0) importe FROM otro_egreso oe "
        "WHERE oe.fecha_oe >= %s AND oe.fecha_oe < %s "
        "AND UPPER(COALESCE(oe.anulado,'NO'))<>'SI' "
        "AND (COALESCE(oe.id_impuesto,0)<>0 OR COALESCE(oe.id_impuesto_detalle,0)<>0 "
        f"OR UPPER(TRIM(COALESCE(oe.tipo_oe,''))) IN ('IMPUESTO','IMPUESTOS')){scope}",
        _dates(filters) + values,
    )


def list_impositivo_v45_detail(cursor, filters: DashboardFilters, *, view: str) -> dict:
    if view not in IMPOSITIVO_V45_VIEWS:
        raise ValueError("Vista fiscal inválida")
    if view == "determinados" and (filters.puntos_venta or filters.sucursales_filtro):
        return {"disponible": False, "motivo": "sin_alcance_territorial", "filas": []}
    required = {
        "ventas": ("cuentacliente", "cliente"),
        "compras": ("cuentaproveedor", "proveedor"),
        "percepciones": ("percep_cli", "percep_cli_tipo", "percep_cli_abm", "cuentacliente"),
        "retenciones": ("retenciones", "tipo_retencion_cli"),
        "determinados": ("impuesto_detalle",),
        "pagados": ("otro_egreso",),
    }[view]
    missing = [name for name in required if not _table_exists(cursor, name)]
    if missing:
        return {"disponible": False, "motivo": "tablas_faltantes", "tablas_faltantes": missing, "filas": []}
    source, params = _source(filters, view)
    search = ""
    if filters.busqueda:
        search = " WHERE (q.entidad LIKE %s OR CAST(q.comprobante AS CHAR) LIKE %s)"
        params += [f"%{filters.busqueda}%"] * 2
    cursor.execute(f"SELECT COUNT(*),COALESCE(SUM(q.importe),0) FROM ({source}) q{search}", params)
    total = cursor.fetchone() or (0, 0)
    cursor.execute(
        f"SELECT * FROM ({source}) q{search} ORDER BY q.fecha DESC,q.movimiento DESC LIMIT %s OFFSET %s",
        params + [filters.limit, filters.offset],
    )
    keys = [col[0] for col in cursor.description]
    rows = [dict(zip(keys, row)) for row in cursor.fetchall() or []]
    payload = build_paginated_response(filters, rows, int(total[0] or 0), total[1])
    payload["vista"] = view
    return payload
