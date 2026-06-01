"""KPIs tesorería (caja) — Command Center gerencial."""
from __future__ import annotations

from typing import Any

from .base import DashboardFilters, build_meta, round_money
from .caja_classification import (
    sql_es_flujo_operativo,
    sql_predicado_egresos_proveedores,
    sql_predicado_ingresos_cobranzas,
    sql_predicado_ingresos_ventas,
    sum_saldo_cajas,
)


def _where_caja(filters: DashboardFilters) -> tuple[str, list]:
    conds = [
        "c.fecha >= %s",
        "c.fecha <= %s",
        "c.anulado = 'No'",
    ]
    params: list = [filters.fecha_inicio_str, filters.fecha_fin_str]
    if filters.cod_sucursal is not None:
        conds.append("c.cod_sucursal = %s")
        params.append(filters.cod_sucursal)
    return " AND ".join(conds), params


def fetch_tesoreria_resumen(cursor, filters: DashboardFilters) -> dict[str, Any]:
    where_clause, params = _where_caja(filters)
    op = sql_es_flujo_operativo("c.tipo")
    ing_ventas = sql_predicado_ingresos_ventas()
    ing_cob = sql_predicado_ingresos_cobranzas()
    egr_prov = sql_predicado_egresos_proveedores()

    saldo_inicial_sistema = sum_saldo_cajas(
        cursor, filters.fecha_inicio_str, antes_de=True, cod_sucursal=filters.cod_sucursal
    )
    saldo_final_sistema = sum_saldo_cajas(
        cursor, filters.fecha_fin_str, antes_de=False, cod_sucursal=filters.cod_sucursal
    )

    sql_flujos = f"""
        SELECT
            SUM(CASE WHEN {op} = 1 THEN COALESCE(c.ingreso, 0) ELSE 0 END),
            SUM(CASE WHEN {op} = 1 THEN COALESCE(c.egreso, 0) ELSE 0 END),
            SUM(CASE WHEN {op} = 1 AND {ing_ventas}
                THEN COALESCE(c.ingreso, 0) ELSE 0 END),
            SUM(CASE WHEN {op} = 1 AND {ing_cob}
                THEN COALESCE(c.ingreso, 0) ELSE 0 END),
            SUM(CASE WHEN {op} = 1 AND {egr_prov}
                THEN COALESCE(c.egreso, 0) ELSE 0 END)
        FROM caja c
        WHERE {where_clause}
    """
    cursor.execute(sql_flujos, params)
    row = cursor.fetchone() or (0, 0, 0, 0, 0)
    ingresos_operativos = float(row[0] or 0)
    egresos_operativos = float(row[1] or 0)
    ingresos_ventas = float(row[2] or 0)
    ingresos_cobranzas = float(row[3] or 0)
    egresos_proveedores = float(row[4] or 0)
    variacion_neta = ingresos_operativos - egresos_operativos
    saldo_final_coherente = saldo_inicial_sistema + variacion_neta
    drift_sistema = saldo_final_sistema - saldo_final_coherente

    sql_tipo = f"""
        SELECT
            COALESCE(ca.tipo_caja, 'Sin tipo'),
            SUM(CASE WHEN {op} = 1 THEN COALESCE(c.ingreso, 0) ELSE 0 END),
            SUM(CASE WHEN {op} = 1 THEN COALESCE(c.egreso, 0) ELSE 0 END)
        FROM caja c
        LEFT JOIN caja_abm ca ON ca.id_caja = c.id_caja_abm_origen
        WHERE {where_clause}
        GROUP BY COALESCE(ca.tipo_caja, 'Sin tipo')
        HAVING SUM(COALESCE(c.ingreso, 0) + COALESCE(c.egreso, 0)) > 0
        ORDER BY SUM(COALESCE(c.ingreso, 0) - COALESCE(c.egreso, 0)) DESC
        LIMIT 8
    """
    cursor.execute(sql_tipo, params)
    por_tipo_caja = []
    for tr in cursor.fetchall():
        ing, egr = float(tr[1] or 0), float(tr[2] or 0)
        por_tipo_caja.append(
            {
                "tipo_caja": tr[0] or "Sin tipo",
                "ingresos": round_money(ing),
                "egresos": round_money(egr),
                "variacion": round_money(ing - egr),
            }
        )

    notas = [
        "Flujos y saldo final coherente alineados con cash_flow_waterfall (misma exclusión operativa).",
        "Saldo final coherente = saldo inicial + variación neta del período.",
        "Saldo final sistema = último caja.Saldo en BD (puede diferir por drift legacy).",
        "Vista consolidada: excluye cierres, transferencias entre cajas e inversión/financiamiento.",
        "No incluye libro banco (librobanco); endpoint tesoreria/banco previsto en P1.",
    ]
    if abs(drift_sistema) > 1.0:
        notas.append(
            f"Diferencia saldo sistema vs coherente: {round_money(drift_sistema)} "
            "(revisar caja.Saldo vs movimientos en cajas con histórico inconsistente)."
        )

    return {
        "saldo_inicial": round_money(saldo_inicial_sistema),
        "saldo_final": round_money(saldo_final_coherente),
        "saldo_final_sistema": round_money(saldo_final_sistema),
        "saldo_final_coherente": round_money(saldo_final_coherente),
        "drift_sistema": round_money(drift_sistema),
        "ingresos_operativos": round_money(ingresos_operativos),
        "egresos_operativos": round_money(egresos_operativos),
        "variacion_neta": round_money(variacion_neta),
        "ingresos_ventas": round_money(ingresos_ventas),
        "ingresos_cobranzas": round_money(ingresos_cobranzas),
        "egresos_proveedores": round_money(egresos_proveedores),
        "por_tipo_caja": por_tipo_caja,
        "banco_disponible": False,
        "disponible": True,
        "meta": build_meta(filters, notas_semanticas=notas),
    }


# Compatibilidad tests / imports legacy
_sum_saldo_cajas = sum_saldo_cajas
