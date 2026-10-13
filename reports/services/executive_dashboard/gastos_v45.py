"""Análisis de gastos V45 según CMGas_* en modCM_FinancieroDatos.bas."""
from __future__ import annotations

from datetime import timedelta

from .base import DashboardFilters, build_meta, comparison_filters, round_money
from .resumen_v45 import _table_exists


GASTOS_V45_KEYS = (
    "total_gastos", "operativos", "bancarios", "impuestos_pagados",
    "nc_ajustes", "documentos", "promedio_documento", "promedio_diario",
    "gastos_sobre_ventas", "variacion", "sin_grupo", "sin_cuenta",
    "grupo_principal", "gasto_principal", "sucursal_principal",
)
_TAX = "(COALESCE(oe.id_impuesto,0)<>0 OR COALESCE(oe.id_impuesto_detalle,0)<>0 OR UPPER(TRIM(COALESCE(oe.tipo_oe,''))) IN ('IMPUESTO','IMPUESTOS') OR UPPER(COALESCE(oe.tipo_comp,'')) LIKE '%%IMPUEST%%')"
_SIGNED = "IF(UPPER(COALESCE(oe.tipo_comp,'')) LIKE 'NC%%',-ABS(COALESCE(oe.importe_oe,0)),ABS(COALESCE(oe.importe_oe,0)))"
_BRUTO = "IF(UPPER(COALESCE(oe.tipo_comp,'')) LIKE 'NC%%',0,ABS(COALESCE(oe.importe_oe,0)))"
_AJUSTE = "IF(UPPER(COALESCE(oe.tipo_comp,'')) LIKE 'NC%%',ABS(COALESCE(oe.importe_oe,0)),0)"


def _dates(filters, previous=False):
    if previous:
        prior = comparison_filters(filters)
        return [prior.fecha_inicio_str, (prior.fecha_fin + timedelta(days=1)).isoformat()]
    return [filters.fecha_inicio_str, (filters.fecha_fin + timedelta(days=1)).isoformat()]


def _branch_scope(column, filters):
    clauses, values = [], []
    if filters.sucursales_filtro:
        clauses.append(f"{column} IN ({','.join(['%s'] * len(filters.sucursales_filtro))})")
        values += list(filters.sucursales_filtro)
    if filters.puntos_venta:
        clauses.append(f"{column} IN (SELECT id_sucursal FROM punto_venta WHERE id_punto_venta IN ({','.join(['%s'] * len(filters.puntos_venta))}))")
        values += list(filters.puntos_venta)
    return (" AND " + " AND ".join(clauses) if clauses else ""), values


def _operational(filters, previous=False):
    scope, branch = _branch_scope("oe.id_sucursal", filters)
    sql = (
        "SELECT oe.fecha_oe fecha,'Operativo' fuente,'OE' origen,oe.id_oe id_origen,"
        "COALESCE(NULLIF(TRIM(gg.nombre_gastos_grupo),''),'Sin grupo') grupo,"
        "COALESCE(NULLIF(TRIM(g.Nombre),''),NULLIF(TRIM(oe.nombre_oe),''),'Sin concepto') gasto,"
        "COALESCE(NULLIF(TRIM(su.nombre_sucursal),''),'Sin sucursal') sucursal,"
        "COALESCE(g.id_pc,0) id_pc,"
        f"{_BRUTO} bruto,{_AJUSTE} ajuste,{_SIGNED} importe "
        "FROM otro_egreso oe LEFT JOIN gastos g ON g.Codigo=oe.id_gasto "
        "LEFT JOIN gastos_grupo gg ON gg.id_gastos_grupo=g.id_gastos_grupo "
        "LEFT JOIN sucursales su ON su.id_sucursal=oe.id_sucursal "
        "WHERE oe.fecha_oe >= %s AND oe.fecha_oe < %s "
        "AND UPPER(COALESCE(oe.anulado,'NO'))<>'SI' "
        "AND (COALESCE(oe.id_gasto,0)<>0 OR UPPER(TRIM(COALESCE(oe.tipo_oe,''))) "
        "IN ('GASTO','GASTOS','OTROS EGRESOS') OR UPPER(COALESCE(oe.tipo_comp,'')) "
        "LIKE '%%GASTO%%' OR UPPER(COALESCE(oe.tipo_comp,'')) LIKE '%%EGRESO%%') "
        f"AND NOT {_TAX}{scope}"
    )
    return sql, _dates(filters, previous) + branch


def _taxes(filters, previous=False):
    scope, branch = _branch_scope("oe.id_sucursal", filters)
    sql = (
        "SELECT oe.fecha_oe fecha,'Impuesto' fuente,'OE' origen,oe.id_oe id_origen,"
        "'Impuestos' grupo,COALESCE(NULLIF(TRIM(oe.nombre_oe),''),'Sin impuesto') gasto,"
        "COALESCE(NULLIF(TRIM(su.nombre_sucursal),''),'Sin sucursal') sucursal,0 id_pc,"
        f"{_BRUTO} bruto,{_AJUSTE} ajuste,{_SIGNED} importe "
        "FROM otro_egreso oe LEFT JOIN sucursales su ON su.id_sucursal=oe.id_sucursal "
        "WHERE oe.fecha_oe >= %s AND oe.fecha_oe < %s "
        f"AND UPPER(COALESCE(oe.anulado,'NO'))<>'SI' AND {_TAX}{scope}"
    )
    return sql, _dates(filters, previous) + branch


def _banking(filters, previous=False):
    scope, branch = _branch_scope("lb.CodSucursal", filters)
    sql = (
        "SELECT lb.Fecha fecha,'Bancario' fuente,'LB' origen,lb.CodMov id_origen,"
        "'Gastos bancarios' grupo,"
        "COALESCE(NULLIF(TRIM(gb.NombreGasto),''),'Sin concepto') gasto,"
        "COALESCE(NULLIF(TRIM(su.nombre_sucursal),''),'Sin sucursal') sucursal,"
        "COALESCE(gb.id_pc,0) id_pc,ABS(COALESCE(lb.Debito,0)) bruto,0 ajuste,"
        "ABS(COALESCE(lb.Debito,0)) importe FROM librobanco lb "
        "JOIN gastosbancarios gb ON gb.CodGasto=lb.id_gastobancario "
        "LEFT JOIN sucursales su ON su.id_sucursal=lb.CodSucursal "
        "WHERE lb.Fecha >= %s AND lb.Fecha < %s "
        "AND UPPER(COALESCE(lb.Anulado,'NO'))<>'SI' "
        "AND COALESCE(lb.id_gastobancario,0)<>0 AND ABS(COALESCE(lb.Debito,0))>0 "
        "AND NOT EXISTS (SELECT 1 FROM otro_egreso oe2 "
        "WHERE UPPER(COALESCE(oe2.anulado,'NO'))<>'SI' "
        "AND COALESCE(oe2.codigo_movimiento_op,0)<>0 "
        "AND oe2.codigo_movimiento_op=COALESCE(NULLIF(lb.CodigoMovimientoOP,0),lb.CodigoMovimiento))"
        f"{scope}"
    )
    return sql, _dates(filters, previous) + branch


def _base(cursor, filters, source, previous=False):
    parts = []
    values = []
    available = {
        "operativos": all(_table_exists(cursor, table) for table in ("otro_egreso", "gastos", "gastos_grupo", "sucursales")),
        "bancarios": all(_table_exists(cursor, table) for table in ("librobanco", "gastosbancarios", "sucursales", "otro_egreso")),
        "impuestos": all(_table_exists(cursor, table) for table in ("otro_egreso", "sucursales")),
    }
    enabled = {
        0: ("operativos", "bancarios"), 1: ("operativos",),
        2: ("bancarios",), 3: ("impuestos",),
    }[source]
    builders = {"operativos": _operational, "bancarios": _banking, "impuestos": _taxes}
    for name in enabled:
        if available[name]:
            sql, params = builders[name](filters, previous)
            parts.append(sql)
            values += params
    return (" UNION ALL ".join(parts), values, available)


def _totals(cursor, sql, params):
    if not sql:
        return None
    cursor.execute(
        "SELECT COALESCE(SUM(x.importe),0),COALESCE(SUM(x.bruto),0),"
        "COALESCE(SUM(x.ajuste),0),COUNT(DISTINCT CONCAT(x.origen,'|',x.id_origen)),"
        "COALESCE(SUM(IF(x.fuente='Operativo' AND x.grupo='Sin grupo',x.importe,0)),0),"
        "COUNT(DISTINCT IF(x.fuente='Operativo' AND x.grupo='Sin grupo',CONCAT(x.origen,'|',x.id_origen),NULL)),"
        "COALESCE(SUM(IF(COALESCE(x.id_pc,0)=0,x.importe,0)),0),"
        "COUNT(DISTINCT IF(COALESCE(x.id_pc,0)=0,CONCAT(x.origen,'|',x.id_origen),NULL)) "
        f"FROM ({sql}) x", params,
    )
    amount, gross, adjustments, docs, ungrouped, ungrouped_count, no_account, no_account_count = cursor.fetchone() or (0,) * 8
    return {
        "total_gastos": round_money(amount), "gasto_bruto": round_money(gross),
        "nc_ajustes": round_money(adjustments), "documentos": int(docs),
        "sin_grupo": {"importe": round_money(ungrouped), "documentos": int(ungrouped_count)},
        "sin_cuenta": {"importe": round_money(no_account), "documentos": int(no_account_count)},
    }


def _main_group(cursor, sql, params, column):
    if not sql:
        return {"nombre": None, "importe": None}
    cursor.execute(
        f"SELECT x.{column},COALESCE(SUM(x.importe),0) valor FROM ({sql}) x "
        f"GROUP BY x.{column} ORDER BY ABS(SUM(x.importe)) DESC LIMIT 1", params,
    )
    row = cursor.fetchone()
    return {"nombre": str(row[0]) if row else None, "importe": round_money(row[1]) if row else None}


def _source_total(cursor, filters, source):
    sql, params, _ = _base(cursor, filters, source)
    total = _totals(cursor, sql, params)
    return total["total_gastos"] if total else None


def _sales_net(cursor, filters):
    if not _table_exists(cursor, "cuentacliente"):
        return None
    clauses, values = [], []
    if filters.puntos_venta:
        clauses.append(f"cc.id_pv IN ({','.join(['%s'] * len(filters.puntos_venta))})")
        values += list(filters.puntos_venta)
    if filters.sucursales_filtro:
        clauses.append(f"cc.id_pv IN (SELECT id_punto_venta FROM punto_venta WHERE id_sucursal IN ({','.join(['%s'] * len(filters.sucursales_filtro))}))")
        values += list(filters.sucursales_filtro)
    scope = " AND " + " AND ".join(clauses) if clauses else ""
    cursor.execute(
        "SELECT COALESCE(SUM(CASE WHEN cc.TipoComprobante IN ('NCA','NCB','NCC','NCE','NCM') "
        "THEN -COALESCE(cc.SubtotalDesc,0) WHEN cc.TipoComprobante IN "
        "('FA','FB','FC','FE','FM','NDA','NDB','NDC','NDE','NDM') "
        "THEN COALESCE(cc.SubtotalDesc,0) ELSE 0 END),0) "
        "FROM cuentacliente cc WHERE cc.Fecha >= %s AND cc.Fecha < %s "
        f"AND cc.CodigoMovimiento<>0 AND cc.Anulado='No'{scope}",
        _dates(filters) + values,
    )
    row = cursor.fetchone()
    return round_money(row[0] if row else 0)


def _series(cursor, sql, params, filters: DashboardFilters) -> dict:
    days = (filters.fecha_fin - filters.fecha_inicio).days + 1
    if days <= 45:
        bucket, expression = "dia", "DATE_FORMAT(x.fecha,'%%Y-%%m-%%d')"
    elif days <= 200:
        bucket = "semana"
        expression = "DATE_FORMAT(DATE_SUB(x.fecha,INTERVAL WEEKDAY(x.fecha) DAY),'%%Y-%%m-%%d')"
    else:
        bucket, expression = "mes", "DATE_FORMAT(x.fecha,'%%Y-%%m-01')"
    cursor.execute(
        f"SELECT {expression} fecha,COALESCE(SUM(x.importe),0) importe,"
        "COUNT(DISTINCT CONCAT(x.origen,'|',x.id_origen)) documentos "
        f"FROM ({sql}) x GROUP BY {expression} ORDER BY {expression}",
        params,
    )
    return {
        "agrupacion": bucket,
        "filas": [
            {"fecha": str(day), "importe": round_money(amount), "documentos": int(count or 0)}
            for day, amount, count in cursor.fetchall() or []
        ],
    }


def fetch_gastos_v45(cursor, filters: DashboardFilters, *, fuente: int = 0) -> dict:
    if fuente not in (0, 1, 2, 3):
        raise ValueError("Fuente de gastos inválida")
    sql, params, available = _base(cursor, filters, fuente)
    if not sql:
        return {"disponible": False, "motivo": "sin_fuentes_gasto", "kpis": {}}
    current = _totals(cursor, sql, params)
    previous_sql, previous_params, _ = _base(cursor, filters, fuente, previous=True)
    previous = _totals(cursor, previous_sql, previous_params)
    previous_period = comparison_filters(filters)
    amount = current["total_gastos"]
    days = (filters.fecha_fin - filters.fecha_inicio).days + 1
    past = previous["total_gastos"] if previous else None
    variation = round_money(amount - past) if past is not None else None
    sales = _sales_net(cursor, filters)
    kpis = {
        **current,
        "operativos": _source_total(cursor, filters, 1),
        "bancarios": _source_total(cursor, filters, 2),
        "impuestos_pagados": _source_total(cursor, filters, 3),
        "promedio_documento": round_money(amount / current["documentos"]) if current["documentos"] else None,
        "promedio_diario": round_money(amount / days),
        "gastos_sobre_ventas": round(amount / sales * 100, 2) if sales and abs(sales) > 0.0001 else None,
        "variacion": {"importe": variation, "porcentaje": round(variation / past * 100, 2) if past and variation is not None else None},
        "grupo_principal": _main_group(cursor, sql, params, "grupo"),
        "gasto_principal": _main_group(cursor, sql, params, "gasto"),
        "sucursal_principal": _main_group(cursor, sql, params, "sucursal"),
    }
    return {
        "disponible": True, "kpis": kpis, "fuente": fuente,
        "serie": _series(cursor, sql, params, filters),
        "serie_comparacion": _series(cursor, previous_sql, previous_params, previous_period),
        "comparacion": {
            "periodo": {"inicio": previous_period.fecha_inicio_str, "fin": previous_period.fecha_fin_str},
            "kpis": previous,
        },
        "fuentes_disponibles": available,
        "meta": build_meta(filters, fuente="modCM_FinancieroDatos.bas/CMGas/V45"),
    }
