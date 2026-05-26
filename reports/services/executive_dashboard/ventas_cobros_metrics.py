"""Ventas por medio de cobro — facturado vs cobrado en caja."""
from __future__ import annotations

from typing import Any

from .base import DashboardFilters, build_meta, round_money
from .caja_classification import get_payment_method, medio_cobro_bucket


def _empty_buckets() -> dict[str, float]:
    return {
        "efectivo": 0.0,
        "tarjeta": 0.0,
        "cuenta_corriente": 0.0,
        "cheque": 0.0,
        "transferencia": 0.0,
        "otros": 0.0,
        "total": 0.0,
    }


def _finalize_buckets(b: dict[str, float]) -> dict[str, float]:
    total = sum(b[k] for k in b if k != "total")
    out = {k: round_money(b[k]) for k in b if k != "total"}
    out["total"] = round_money(total)
    return out


def _fetch_facturado_resumen(cursor, filters: DashboardFilters) -> dict[str, float]:
    buckets = _empty_buckets()
    conds = [
        "rv.fecha >= %s",
        "rv.fecha <= %s",
        "(rv.anulado IS NULL OR rv.anulado = 'No')",
    ]
    params: list = [filters.fecha_inicio_str, filters.fecha_fin_str]
    if filters.cod_sucursal is not None:
        conds.append("rv.id_sucursal = %s")
        params.append(filters.cod_sucursal)
    where = " AND ".join(conds)
    sql = f"""
        SELECT
            COALESCE(SUM(rv.total_efectivo), 0),
            COALESCE(SUM(rv.total_tarjeta), 0),
            COALESCE(SUM(rv.total_ctacte), 0),
            COALESCE(SUM(rv.total_cheque), 0),
            COALESCE(SUM(rv.total_transferencia), 0),
            COALESCE(SUM(rv.total_otro_medio), 0)
        FROM resumen_venta_cv rv
        WHERE {where}
    """
    try:
        cursor.execute(sql, params)
        row = cursor.fetchone()
    except Exception:
        row = None
    if row:
        buckets["efectivo"] += float(row[0] or 0)
        buckets["tarjeta"] += float(row[1] or 0)
        buckets["cuenta_corriente"] += float(row[2] or 0)
        buckets["cheque"] += float(row[3] or 0)
        buckets["transferencia"] += float(row[4] or 0)
        buckets["otros"] += float(row[5] or 0)

    cc_conds = [
        "cc.Fecha >= %s",
        "cc.Fecha <= %s",
        "cc.Anulado = 'No'",
        "cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM')",
        """NOT EXISTS (
            SELECT 1 FROM resumen_venta_cv rv2
            WHERE rv2.codigo_movimiento = cc.CodigoMovimiento
              AND (rv2.anulado IS NULL OR rv2.anulado = 'No')
        )""",
    ]
    cc_params: list = [filters.fecha_inicio_str, filters.fecha_fin_str]
    if filters.cod_sucursal is not None:
        cc_conds.append("cc.CodSucursal = %s")
        cc_params.append(filters.cod_sucursal)
    sql_cc = f"""
        SELECT
            COALESCE(SUM(COALESCE(cc.tpv_importe_efectivo, cc.TotalEfectivoP, 0)), 0),
            COALESCE(SUM(COALESCE(cc.tpv_importe_tarjeta, cc.Total_Tarjeta, 0)), 0),
            COALESCE(SUM(COALESCE(cc.tpv_importe_ctacte, 0)), 0),
            COALESCE(SUM(COALESCE(cc.tpv_importe_cheque, 0)), 0),
            COALESCE(SUM(COALESCE(cc.tpv_importe_transferencia, 0)), 0),
            0
        FROM cuentacliente cc
        WHERE {" AND ".join(cc_conds)}
    """
    try:
        cursor.execute(sql_cc, cc_params)
        row_cc = cursor.fetchone()
    except Exception:
        row_cc = None
    if row_cc:
        buckets["efectivo"] += float(row_cc[0] or 0)
        buckets["tarjeta"] += float(row_cc[1] or 0)
        buckets["cuenta_corriente"] += float(row_cc[2] or 0)
        buckets["cheque"] += float(row_cc[3] or 0)
        buckets["transferencia"] += float(row_cc[4] or 0)

    return _finalize_buckets(buckets)


def _fetch_cobrado_caja(cursor, filters: DashboardFilters) -> dict[str, float]:
    buckets = {
        "efectivo": 0.0,
        "tarjeta": 0.0,
        "cheque": 0.0,
        "transferencia": 0.0,
        "otros": 0.0,
        "total": 0.0,
    }
    conds = [
        "c.fecha >= %s",
        "c.fecha <= %s",
        "c.anulado = 'No'",
        "COALESCE(c.ingreso, 0) > 0",
    ]
    params: list = [filters.fecha_inicio_str, filters.fecha_fin_str]
    if filters.cod_sucursal is not None:
        conds.append("c.cod_sucursal = %s")
        params.append(filters.cod_sucursal)
    sql = f"""
        SELECT c.tipo_comprobante, c.tipo, SUM(COALESCE(c.ingreso, 0))
        FROM caja c
        WHERE {" AND ".join(conds)}
        GROUP BY c.tipo_comprobante, c.tipo
    """
    cursor.execute(sql, params)
    for tipo_comp, tipo, monto in cursor.fetchall():
        medio = get_payment_method(tipo_comp, tipo)
        bucket = medio_cobro_bucket(medio)
        buckets[bucket] = buckets.get(bucket, 0.0) + float(monto or 0)
    return _finalize_buckets(buckets)


def fetch_ventas_cobros_resumen(cursor, filters: DashboardFilters) -> dict[str, Any]:
    facturado = _fetch_facturado_resumen(cursor, filters)
    cobrado = _fetch_cobrado_caja(cursor, filters)
    notas = [
        "Facturado por medio: al emitir (resumen_venta_cv + complemento cuentacliente sin resumen).",
        "Cobrado en caja: ingresos reales en caja en el período (contado FA + cobranzas REC).",
        "En ventas a cuenta corriente, facturado en cuenta_corriente no implica cobro en el mismo período.",
        "Ventas netas del área Ventas incluyen facturas no cobradas; comparar series con esa definición.",
    ]
    return {
        "facturado_por_medio": facturado,
        "cobrado_caja_por_medio": cobrado,
        "disponible": True,
        "meta": build_meta(filters, notas_semanticas=notas),
    }
