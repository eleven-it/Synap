"""KPIs tesorería (caja) — Command Center gerencial."""
from __future__ import annotations

from typing import Any

from .base import DashboardFilters, build_meta, round_money
from .caja_classification import sql_excluir_interno_campo


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


def _sum_saldo_cajas(cursor, fecha_limite: str, *, antes_de: bool, cod_sucursal: int | None) -> float:
    """Suma último caja.Saldo por id_caja_abm_origen antes o hasta fecha_limite.

    Implementación con agregaciones (MAX fecha + MAX codigo_movimiento) compatible MySQL 5.7;
    evita subconsulta correlacionada por caja que escaneaba ~600k filas.
    """
    op = "<" if antes_de else "<="
    suc_sql = ""
    suc_params: list = []
    if cod_sucursal is not None:
        suc_sql = " AND cod_sucursal = %s"
        suc_params = [cod_sucursal]
    base_where = f"""
        anulado = 'No'
        AND id_caja_abm_origen IS NOT NULL
        AND fecha {op} %s
        {suc_sql}
    """
    sql = f"""
        SELECT COALESCE(SUM(c.saldo), 0)
        FROM caja c
        INNER JOIN (
            SELECT id_caja_abm_origen, MAX(fecha) AS max_fecha
            FROM caja
            WHERE {base_where}
            GROUP BY id_caja_abm_origen
        ) ult_f ON ult_f.id_caja_abm_origen = c.id_caja_abm_origen
              AND c.fecha = ult_f.max_fecha
        INNER JOIN (
            SELECT id_caja_abm_origen, fecha, MAX(codigo_movimiento) AS max_mov
            FROM caja
            WHERE {base_where}
            GROUP BY id_caja_abm_origen, fecha
        ) ult_m ON ult_m.id_caja_abm_origen = c.id_caja_abm_origen
              AND ult_m.fecha = c.fecha
              AND ult_m.max_mov = c.codigo_movimiento
        WHERE c.anulado = 'No'
    """
    params = [fecha_limite] + suc_params + [fecha_limite] + suc_params
    cursor.execute(sql, params)
    row = cursor.fetchone()
    return float(row[0] or 0) if row else 0.0


def fetch_tesoreria_resumen(cursor, filters: DashboardFilters) -> dict[str, Any]:
    where_clause, params = _where_caja(filters)
    excl = sql_excluir_interno_campo("c.tipo")

    saldo_inicial = _sum_saldo_cajas(
        cursor, filters.fecha_inicio_str, antes_de=True, cod_sucursal=filters.cod_sucursal
    )
    saldo_final = _sum_saldo_cajas(
        cursor, filters.fecha_fin_str, antes_de=False, cod_sucursal=filters.cod_sucursal
    )

    sql_flujos = f"""
        SELECT
            SUM(CASE WHEN {excl} = 1 THEN COALESCE(c.ingreso, 0) ELSE 0 END),
            SUM(CASE WHEN {excl} = 1 THEN COALESCE(c.egreso, 0) ELSE 0 END),
            SUM(CASE WHEN {excl} = 1 AND c.tipo_comprobante IN ('FA','FB','FC','FE','FM','TARJ')
                THEN COALESCE(c.ingreso, 0) ELSE 0 END),
            SUM(CASE WHEN {excl} = 1 AND (
                c.tipo_comprobante = 'REC'
                OR (c.tipo_comprobante = 'CHEQ' AND c.tipo_cp = 'Cliente')
                OR (c.tipo_comprobante = 'MCAJ' AND (
                    LOWER(c.tipo) LIKE '%%cobro%%' OR LOWER(c.tipo) LIKE '%%cobranza%%'
                ))
            ) THEN COALESCE(c.ingreso, 0) ELSE 0 END),
            SUM(CASE WHEN {excl} = 1 AND (
                c.tipo_comprobante = 'OP'
                OR (c.tipo_comprobante IN ('FA','FB') AND c.tipo_cp = 'Proveedor')
            ) THEN COALESCE(c.egreso, 0) ELSE 0 END)
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

    sql_tipo = f"""
        SELECT
            COALESCE(ca.tipo_caja, 'Sin tipo'),
            SUM(CASE WHEN {excl} = 1 THEN COALESCE(c.ingreso, 0) ELSE 0 END),
            SUM(CASE WHEN {excl} = 1 THEN COALESCE(c.egreso, 0) ELSE 0 END)
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
        "Saldos y flujos desde tabla caja (último campo Saldo por caja_abm).",
        "Vista consolidada: excluye transferencias entre cajas y cierres de caja del neto operativo.",
        "No incluye libro banco (librobanco); endpoint tesoreria/banco previsto en P1.",
        "Puede diferir de caja_saldo si hay movimientos registrados solo desde Synap sin actualizar saldo maestro.",
    ]
    return {
        "saldo_inicial": round_money(saldo_inicial),
        "saldo_final": round_money(saldo_final),
        "ingresos_operativos": round_money(ingresos_operativos),
        "egresos_operativos": round_money(egresos_operativos),
        "variacion_neta": round_money(ingresos_operativos - egresos_operativos),
        "ingresos_ventas": round_money(ingresos_ventas),
        "ingresos_cobranzas": round_money(ingresos_cobranzas),
        "egresos_proveedores": round_money(egresos_proveedores),
        "por_tipo_caja": por_tipo_caja,
        "banco_disponible": False,
        "disponible": True,
        "meta": build_meta(filters, notas_semanticas=notas),
    }
