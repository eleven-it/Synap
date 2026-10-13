"""Posiciones fiscales V45, de modCM_ImpositivoDatos.bas."""
from __future__ import annotations

from datetime import timedelta

from .base import DashboardFilters, build_meta, comparison_filters, round_money
from .resumen_v45 import _table_exists


TAX_V45_KEYS = (
    "posicion_iva", "iva_debito", "iva_credito", "percep_iva_ventas",
    "percep_iva_compras", "retenciones_iva", "libro_ventas", "libro_compras",
    "iibb_ventas", "percep_iibb_ventas", "percep_iibb_compras",
    "retenciones_iibb", "impuestos_determinados", "impuestos_pagados",
)
SALES_TYPES = ("FA", "FB", "FC", "FE", "FM", "NC", "NCA", "NCB", "NCC", "NCE", "NCM", "ND", "NDA", "NDB", "NDC", "NDE", "NDM")
PURCHASE_TYPES = SALES_TYPES + ("EB",)
NC_TYPES = ("NC", "NCA", "NCB", "NCC", "NCE", "NCM")


def _dates(filters):
    return [filters.fecha_inicio_str, (filters.fecha_fin + timedelta(days=1)).isoformat()]


def _in(column, values):
    return f"{column} IN ({','.join(['%s'] * len(values))})", list(values)


def _sales(cursor, filters):
    types_sql, types = _in("cc.TipoComprobante", SALES_TYPES)
    scope = ""
    pv = []
    if filters.puntos_venta:
        predicate, pv = _in("cc.id_pv", filters.puntos_venta)
        scope += f" AND {predicate}"
    if filters.sucursales_filtro:
        predicate, branch = _in("pv.id_sucursal", filters.sucursales_filtro)
        scope += f" AND {predicate}"
        pv += branch
    source = f"cuentacliente cc {'JOIN punto_venta pv ON pv.id_punto_venta=cc.id_pv' if filters.sucursales_filtro else ''}"
    where = f"cc.Fecha >= %s AND cc.Fecha < %s AND {types_sql} AND COALESCE(cc.CodigoMovimiento,0)<>0 AND UPPER(COALESCE(cc.Anulado,'NO'))<>'SI'{scope}"
    params = _dates(filters) + types + pv
    sign = f"IF(cc.TipoComprobante IN ({','.join(['%s']*len(NC_TYPES))}),-1,1)"
    cursor.execute(
        f"SELECT COALESCE(SUM({sign}*(COALESCE(cc.IVA1,0)+COALESCE(cc.IVA2,0))),0),"
        f"COALESCE(SUM({sign}*(COALESCE(cc.IG1,0)+COALESCE(cc.IG2,0))),0),COUNT(*) "
        f"FROM {source} WHERE {where}", list(NC_TYPES) * 2 + params,
    )
    iva, iibb, count = cursor.fetchone() or (0, 0, 0)
    return {"iva_debito": round_money(iva), "iibb_ventas": round_money(iibb), "libro_ventas": int(count)}, where, params, sign


def _purchases(cursor, filters):
    types_sql, types = _in("cp.TipoComprobante", PURCHASE_TYPES)
    scope, branch = "", []
    if filters.sucursales_filtro:
        predicate, branch = _in("cp.CodSucursal", filters.sucursales_filtro)
        scope += f" AND {predicate}"
    if filters.puntos_venta:
        predicate, pv = _in("id_punto_venta", filters.puntos_venta)
        scope += f" AND cp.CodSucursal IN (SELECT id_sucursal FROM punto_venta WHERE {predicate})"
        branch += pv
    where = f"cp.FechaRegistro >= %s AND cp.FechaRegistro < %s AND {types_sql} AND COALESCE(cp.CodigoMovimiento,0)<>0 AND UPPER(COALESCE(cp.Anulado,'NO'))<>'SI' AND UPPER(COALESCE(cp.motivo_nd,''))<>'CHEQUE RECHAZADO' AND UPPER(COALESCE(p.Tipo,''))<>'PROFESIONAL'{scope}"
    params = _dates(filters) + types + branch
    sign = f"IF(cp.TipoComprobante IN ({','.join(['%s']*len(NC_TYPES))}),-1,1)"
    cursor.execute(
        f"SELECT COALESCE(SUM({sign}*(COALESCE(cp.IVA1,0)+COALESCE(cp.IVA2,0)+COALESCE(cp.IVA3,0)+COALESCE(cp.sobretasa_iva,0))),0),"
        f"COALESCE(SUM({sign}*COALESCE(cp.PercepIVA,0)),0),"
        f"COALESCE(SUM({sign}*(COALESCE(cp.PercepIB,0)+COALESCE(cp.PercepIB_Prov,0))),0),COUNT(*) "
        f"FROM cuentaproveedor cp LEFT JOIN proveedor p ON p.Codigo=cp.Codigo WHERE {where}",
        list(NC_TYPES) * 3 + params,
    )
    credit, iva_perception, iibb_perception, count = cursor.fetchone() or (0, 0, 0, 0)
    return {
        "iva_credito": round_money(credit), "percep_iva_compras": round_money(iva_perception),
        "percep_iibb_compras": round_money(iibb_perception), "libro_compras": int(count),
    }


def _perceptions(cursor, filters, sales_where, sales_params, sign):
    branch_join = "JOIN punto_venta pv ON pv.id_punto_venta=cc.id_pv " if filters.sucursales_filtro else ""
    cursor.execute(
        f"SELECT COALESCE(SUM(IF(ab.id_percep_cli_abm=2,{sign}*pc.importe_percep_cli,0)),0),"
        f"COALESCE(SUM(IF(ab.id_percep_cli_abm IN (1,3),{sign}*pc.importe_percep_cli,0)),0) "
        "FROM percep_cli pc JOIN percep_cli_tipo pt ON pt.id_percep_cli_tipo=pc.id_percep_cli_tipo "
        "JOIN percep_cli_abm ab ON ab.id_percep_cli_abm=pt.id_percep_cli_abm "
        "JOIN cuentacliente cc ON cc.CodigoMovimiento=pc.codigo_movimiento "
        f"{branch_join}"
        f"WHERE {sales_where} AND UPPER(COALESCE(pc.anulado,'NO'))<>'SI' "
        "AND UPPER(COALESCE(pc.tipo_comp,'')) NOT IN ('PED','PRE')",
        list(NC_TYPES) * 2 + sales_params,
    )
    iva, iibb = cursor.fetchone() or (0, 0)
    return {"percep_iva_ventas": round_money(iva), "percep_iibb_ventas": round_money(iibb)}


def _retentions(cursor, filters):
    # V45 derives territorial scope via codigo_movimiento. Restrict through
    # the original document; do not expose global retentions under a filter.
    joins, scope, params = "", "", []
    if filters.puntos_venta or filters.sucursales_filtro:
        joins = " JOIN cuentacliente cc ON cc.CodigoMovimiento=r.codigo_movimiento"
        if filters.sucursales_filtro:
            joins += " JOIN punto_venta pv ON pv.id_punto_venta=cc.id_pv"
        if filters.puntos_venta:
            pred, values = _in("cc.id_pv", filters.puntos_venta)
            scope += f" AND {pred}"
            params += values
        if filters.sucursales_filtro:
            pred, values = _in("pv.id_sucursal", filters.sucursales_filtro)
            scope += f" AND {pred}"
            params += values
    cursor.execute(
        "SELECT COALESCE(SUM(IF(tr.id_impuesto=1,r.Importe,0)),0),"
        "COALESCE(SUM(IF(tr.id_impuesto IN (4,8,9,10,11,12,13),r.Importe,0)),0) "
        "FROM retenciones r LEFT JOIN tipo_retencion_cli tr ON tr.CodRetencion=r.CodRetencion "
        f"{joins} WHERE r.Fecha >= %s AND r.Fecha < %s "
        f"AND UPPER(COALESCE(r.Anulado,'NO'))<>'SI'{scope}", _dates(filters) + params,
    )
    iva, iibb = cursor.fetchone() or (0, 0)
    return {"retenciones_iva": round_money(iva), "retenciones_iibb": round_money(iibb)}


def _determined(cursor, filters):
    if filters.puntos_venta or filters.sucursales_filtro:
        return None
    cursor.execute(
        "SELECT COALESCE(SUM(d.importe_impdetalle),0) FROM impuesto_detalle d "
        "WHERE UPPER(COALESCE(d.anulado,'NO'))<>'SI' "
        "AND d.fechasta_impdetalle >= %s AND d.fechasta_impdetalle < %s", _dates(filters),
    )
    row = cursor.fetchone()
    return round_money(row[0] if row else 0)


def _paid(cursor, filters):
    scope, branch = "", []
    if filters.sucursales_filtro:
        pred, branch = _in("oe.id_sucursal", filters.sucursales_filtro)
        scope += f" AND {pred}"
    if filters.puntos_venta:
        pred, pv = _in("id_punto_venta", filters.puntos_venta)
        scope += f" AND oe.id_sucursal IN (SELECT id_sucursal FROM punto_venta WHERE {pred})"
        branch += pv
    cursor.execute(
        "SELECT COALESCE(SUM(oe.importe_oe),0) FROM otro_egreso oe "
        "WHERE oe.fecha_oe >= %s AND oe.fecha_oe < %s "
        "AND UPPER(COALESCE(oe.anulado,'NO'))<>'SI' "
        "AND (COALESCE(oe.id_impuesto,0)<>0 OR COALESCE(oe.id_impuesto_detalle,0)<>0 "
        f"OR UPPER(TRIM(COALESCE(oe.tipo_oe,''))) IN ('IMPUESTO','IMPUESTOS')){scope}",
        _dates(filters) + branch,
    )
    row = cursor.fetchone()
    return round_money(row[0] if row else 0)


def _metrics(cursor, filters: DashboardFilters) -> dict:
    sales, where, params, sign = _sales(cursor, filters)
    purchase = _purchases(cursor, filters)
    perceptions = _perceptions(cursor, filters, where, params, sign)
    retentions = _retentions(cursor, filters)
    iva_position = round_money(
        sales["iva_debito"] + perceptions["percep_iva_ventas"]
        - purchase["iva_credito"] - purchase["percep_iva_compras"]
        - retentions["retenciones_iva"]
    )
    return {
        "posicion_iva": iva_position, **sales, **purchase, **perceptions, **retentions,
        "impuestos_determinados": _determined(cursor, filters),
        "impuestos_pagados": _paid(cursor, filters),
    }


def _monthly_series(cursor, filters: DashboardFilters) -> dict:
    """Series IVA/IIBB de V45, con los mismos documentos y filtros que los KPI."""
    # El import local evita un ciclo: el detalle utiliza los tipos fiscales definidos aquí.
    from .impositivo_v45_detail import _source

    parts = []
    params = []
    for view, debit_iva, credit_iva, debit_iibb, credit_iibb, condition in (
        ("ventas", "q.importe", "0", "q.iibb", "0", ""),
        (
            "percepciones", "q.importe", "0", "0", "0",
            " WHERE q.impuesto=2",
        ),
        (
            "percepciones", "0", "0", "q.importe", "0",
            " WHERE q.impuesto IN (1,3)",
        ),
        (
            "compras", "0", "q.importe+q.percepcion_iva",
            "0", "q.percepcion_iibb", "",
        ),
        (
            "retenciones", "0", "q.importe", "0", "0",
            " WHERE q.impuesto=1",
        ),
        (
            "retenciones", "0", "0", "0", "q.importe",
            " WHERE q.impuesto IN (4,8,9,10,11,12,13)",
        ),
    ):
        source, source_params = _source(filters, view)
        parts.append(
            "SELECT DATE_FORMAT(q.fecha,'%%Y-%%m-01') mes,"
            f"{debit_iva} iva_debito,{credit_iva} iva_credito,"
            f"{debit_iibb} iibb_debito,{credit_iibb} iibb_credito "
            f"FROM ({source}) q{condition}"
        )
        params.extend(source_params)
    cursor.execute(
        "SELECT x.mes,COALESCE(SUM(x.iva_debito),0),"
        "COALESCE(SUM(x.iva_credito),0),"
        "COALESCE(SUM(x.iibb_debito),0),"
        "COALESCE(SUM(x.iibb_credito),0) FROM ("
        + " UNION ALL ".join(parts)
        + ") x GROUP BY x.mes ORDER BY x.mes",
        params,
    )
    rows = []
    for month, iva_debit, iva_credit, iibb_debit, iibb_credit in cursor.fetchall() or []:
        iva_debit = round_money(iva_debit)
        iva_credit = round_money(iva_credit)
        iibb_debit = round_money(iibb_debit)
        iibb_credit = round_money(iibb_credit)
        rows.append({
            "fecha": str(month),
            "iva_debito": iva_debit,
            "iva_credito": iva_credit,
            "iva_posicion": round_money(iva_debit - iva_credit),
            "iibb_debito": iibb_debit,
            "iibb_credito": iibb_credit,
            "iibb_posicion": round_money(iibb_debit - iibb_credit),
        })
    return {"agrupacion": "mes", "filas": rows}


def fetch_impositivo_v45(cursor, filters: DashboardFilters) -> dict:
    required = ("cuentacliente", "cuentaproveedor", "percep_cli", "retenciones", "impuesto_detalle", "otro_egreso")
    missing = [table for table in required if not _table_exists(cursor, table)]
    if missing:
        return {"disponible": False, "motivo": "tablas_faltantes", "tablas_faltantes": missing, "kpis": {}}
    kpis = _metrics(cursor, filters)
    prior = comparison_filters(filters)
    previous = _metrics(cursor, prior)
    monthly = _monthly_series(cursor, filters)
    monthly_previous = _monthly_series(cursor, prior)
    return {
        "disponible": True, "kpis": kpis,
        "serie_mensual": monthly,
        "serie_mensual_comparacion": monthly_previous,
        "comparacion": {
            "periodo": {"inicio": prior.fecha_inicio_str, "fin": prior.fecha_fin_str},
            "kpis": previous,
            "diferencias": {
                key: round_money(value - previous[key])
                for key, value in kpis.items()
                if value is not None and previous.get(key) is not None
            },
        },
        "alcance": {"impuestos_determinados": "general" if kpis["impuestos_determinados"] is not None else "no disponible con filtro territorial"},
        "meta": build_meta(filters, fuente="modCM_ImpositivoDatos.bas/V45"),
    }
