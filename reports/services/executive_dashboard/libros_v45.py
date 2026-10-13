"""Libros y estados V45 según modCM_AnalisisContableDatos.bas."""
from __future__ import annotations

from .base import DashboardFilters, build_meta, round_money
from .resumen_v45 import _table_exists
from .contable_v45 import _scope, _period


LIBROS_V45_KEYS = (
    "asientos", "total_debe", "total_haber", "diferencia", "cuentas_movimiento",
    "saldo_neto_mayor", "saldo_deudor", "saldo_acreedor", "resultado_periodo",
    "ingresos", "egresos", "activo", "pasivo", "sin_clasificar_conflicto",
)


def _main(cursor, filters, group):
    scope, params = _scope(filters, grupo_contable=group)
    cursor.execute(
        "SELECT COUNT(DISTINCT CONCAT(COALESCE(a.id_ejercicio,0),'-',COALESCE(a.nro_asiento,0))),"
        "COALESCE(SUM(a.debe_asiento),0),COALESCE(SUM(a.haber_asiento),0),"
        "COUNT(DISTINCT a.id_pc) FROM cont_asiento a "
        f"WHERE a.fecha_asiento >= %s AND a.fecha_asiento < %s{scope}",
        _period(filters) + params,
    )
    seats, debit, credit, accounts = cursor.fetchone() or (0, 0, 0, 0)
    debit, credit = round_money(debit), round_money(credit)
    return {
        "asientos": int(seats), "total_debe": debit, "total_haber": credit,
        "diferencia": round_money(debit - credit), "cuentas_movimiento": int(accounts),
    }


def _balances(cursor, filters, group):
    scope, params = _scope(filters, grupo_contable=group)
    cursor.execute(
        "SELECT COALESCE(SUM(IF(saldo>0,saldo,0)),0),"
        "COALESCE(SUM(IF(saldo<0,-saldo,0)),0) FROM ("
        "SELECT a.id_pc,SUM(COALESCE(a.debe_asiento,0)-COALESCE(a.haber_asiento,0)) saldo "
        "FROM cont_asiento a "
        f"WHERE a.fecha_asiento >= %s AND a.fecha_asiento < %s{scope} "
        "GROUP BY a.id_pc) q", _period(filters) + params,
    )
    debtor, creditor = cursor.fetchone() or (0, 0)
    debtor, creditor = round_money(debtor), round_money(creditor)
    return {
        "saldo_neto_mayor": round_money(debtor - creditor),
        "saldo_deudor": debtor, "saldo_acreedor": creditor,
    }


def _results(cursor, filters, group):
    scope, params = _scope(filters, grupo_contable=group)
    cursor.execute(
        "SELECT COALESCE(SUM(IF(UPPER(COALESCE(pc.tipo_cuenta_pc,''))='GANANCIA',a.haber_asiento-a.debe_asiento,0)),0),"
        "COALESCE(SUM(IF(UPPER(COALESCE(pc.tipo_cuenta_pc,''))='PERDIDA',a.debe_asiento-a.haber_asiento,0)),0),"
        "COALESCE(SUM(IF(UPPER(COALESCE(pc.tipo_cuenta_pc,''))='ACTIVO',a.debe_asiento-a.haber_asiento,0)),0),"
        "COALESCE(SUM(IF(UPPER(COALESCE(pc.tipo_cuenta_pc,''))='PASIVO',a.haber_asiento-a.debe_asiento,0)),0) "
        "FROM cont_asiento a LEFT JOIN cont_pc pc ON pc.id_pc=a.id_pc "
        f"WHERE a.fecha_asiento >= %s AND a.fecha_asiento < %s{scope} "
        "AND UPPER(COALESCE(pc.anulado,'NO'))<>'SI'", _period(filters) + params,
    )
    income, expense, asset, liability = cursor.fetchone() or (0, 0, 0, 0)
    income, expense = round_money(income), round_money(expense)
    return {
        "resultado_periodo": round_money(income - expense),
        "ingresos": income, "egresos": expense,
        "activo": round_money(asset), "pasivo": round_money(liability),
    }


def _audit(cursor, filters, group):
    scope, params = _scope(filters, grupo_contable=group)
    cursor.execute(
        "SELECT COALESCE(SUM(q.sin_clasificar),0),COALESCE(SUM(q.conflicto),0) FROM ("
        "SELECT a.codigo_movimiento,MAX(CASE WHEN COALESCE(a.id_sucursal,0)=0 OR "
        "COALESCE(a.id_grupo_contable,0)=0 THEN 1 ELSE 0 END) sin_clasificar,"
        "CASE WHEN COUNT(DISTINCT COALESCE(a.id_sucursal,0))>1 OR "
        "COUNT(DISTINCT COALESCE(a.id_grupo_contable,0))>1 THEN 1 ELSE 0 END conflicto "
        "FROM cont_asiento a "
        f"WHERE a.fecha_asiento >= %s AND a.fecha_asiento < %s{scope} "
        "GROUP BY a.codigo_movimiento) q", _period(filters) + params,
    )
    unclassified, conflict = cursor.fetchone() or (0, 0)
    # KPI 14 is a grouped card with two independently auditable counts.
    return {"sin_clasificar_conflicto": {"sin_clasificar": int(unclassified), "conflictos": int(conflict)}}


def _series(cursor, filters, group):
    days = (filters.fecha_fin - filters.fecha_inicio).days + 1
    if days <= 45:
        bucket, expr = "dia", "DATE_FORMAT(a.fecha_asiento,'%%Y-%%m-%%d')"
    elif days <= 180:
        bucket, expr = "semana", "DATE_FORMAT(DATE_SUB(a.fecha_asiento,INTERVAL WEEKDAY(a.fecha_asiento) DAY),'%%Y-%%m-%%d')"
    else:
        bucket, expr = "mes", "DATE_FORMAT(a.fecha_asiento,'%%Y-%%m-01')"
    scope, params = _scope(filters, grupo_contable=group)
    cursor.execute(
        f"SELECT {expr},COALESCE(SUM(a.debe_asiento),0),COALESCE(SUM(a.haber_asiento),0),"
        "COALESCE(SUM(IF(UPPER(COALESCE(pc.tipo_cuenta_pc,''))='GANANCIA',a.haber_asiento-a.debe_asiento,0)),0),"
        "COALESCE(SUM(IF(UPPER(COALESCE(pc.tipo_cuenta_pc,''))='PERDIDA',a.debe_asiento-a.haber_asiento,0)),0) "
        "FROM cont_asiento a LEFT JOIN cont_pc pc ON pc.id_pc=a.id_pc "
        f"WHERE a.fecha_asiento >= %s AND a.fecha_asiento < %s{scope} "
        f"GROUP BY {expr} ORDER BY {expr}", _period(filters) + params,
    )
    return {
        "agrupacion": bucket,
        "filas": [
            {"fecha": str(day), "debe": round_money(debit), "haber": round_money(credit),
             "ingresos": round_money(income), "egresos": round_money(expense)}
            for day, debit, credit, income, expense in cursor.fetchall() or []
        ],
    }


def fetch_libros_v45(cursor, filters: DashboardFilters, *, grupo_contable: int | None = None) -> dict:
    if not _table_exists(cursor, "cont_asiento") or not _table_exists(cursor, "cont_pc"):
        return {"disponible": False, "motivo": "sin_contabilidad", "kpis": {}}
    kpis = {
        **_main(cursor, filters, grupo_contable),
        **_balances(cursor, filters, grupo_contable),
        **_results(cursor, filters, grupo_contable),
        **_audit(cursor, filters, grupo_contable),
    }
    return {
        "disponible": True, "kpis": kpis,
        "series": _series(cursor, filters, grupo_contable),
        "meta": build_meta(filters, fuente="modCM_AnalisisContableDatos.bas/V45"),
    }
