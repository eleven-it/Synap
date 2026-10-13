"""Resumen gerencial V45: modCM_ResumenDatos.bas, sin escrituras."""
from __future__ import annotations

from datetime import timedelta

from .base import DashboardFilters, build_meta, comparison_filters, round_money
from .comercial_v45 import _scope as _sales_scope


RESUMEN_V45_KEYS = (
    "ventas", "compras_netas", "cobranzas", "pagos", "presupuestos", "pedidos",
    "facturas", "remitos", "vencimiento_cobrar", "vencimiento_pagar",
    "efectivo_actual", "tarjetas_actual", "cheques_actual", "bancos_actual",
    "venta_cuenta_corriente", "compra_cuenta_corriente",
)
_CREDIT_TYPES = "'NCA','NCB','NCC','NCE','NCM'"
_DEBIT_TYPES = "'FA','FB','FC','FE','FM','NDA','NDB','NDC','NDE','NDM'"
_INVOICE_TYPES = "'FA','FB','FC','FE','FM'"


def _period(filters: DashboardFilters) -> list[str]:
    return [filters.fecha_inicio_str, (filters.fecha_fin + timedelta(days=1)).isoformat()]


def _purchase_scope(alias: str, filters: DashboardFilters) -> tuple[str, list[int]]:
    if not filters.sucursales_filtro:
        return "", []
    return (
        f" AND {alias}.CodSucursal IN ({','.join(['%s'] * len(filters.sucursales_filtro))})",
        list(filters.sucursales_filtro),
    )


def _table_exists(cursor, name: str) -> bool:
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema=DATABASE() AND table_name=%s", [name],
    )
    row = cursor.fetchone()
    return bool(row and row[0])


def _sales_amount(gross: bool) -> str:
    debit = "COALESCE(cc.ImporteVenta,0)" if gross else "COALESCE(cc.SubtotalDesc,0)"
    credit = "COALESCE(cc.ImporteCobro,0)" if gross else "COALESCE(cc.SubtotalDesc,0)"
    return (
        f"CASE WHEN cc.TipoComprobante IN ({_CREDIT_TYPES}) THEN -({credit}) "
        f"WHEN cc.TipoComprobante IN ({_DEBIT_TYPES}) THEN {debit} ELSE 0 END"
    )


def _period_metrics(cursor, filters: DashboardFilters, *, gross: bool, has_rv: bool) -> dict:
    period = _period(filters)
    sales_scope, sales_params = _sales_scope("cc", filters)
    cursor.execute(
        f"""
        SELECT COALESCE(SUM({_sales_amount(gross)}),0),
          COALESCE(SUM(CASE WHEN cc.TipoComprobante='REC'
            AND cc.CondVenta IN ('Contado','-') THEN COALESCE(cc.ImporteCobro,0)
            WHEN cc.TipoComprobante IN ({_INVOICE_TYPES})
            AND cc.CondVenta IN ('Contado','-') THEN COALESCE(cc.ImporteVenta,0)
            ELSE 0 END),0),
          COALESCE(SUM(cc.TipoComprobante IN ({_INVOICE_TYPES})),0)
        FROM cuentacliente cc
        WHERE cc.Fecha >= %s AND cc.Fecha < %s
          AND cc.CodigoMovimiento<>0 AND cc.Anulado='No'{sales_scope}
        """,
        period + sales_params,
    )
    ventas, cobranzas, facturas = cursor.fetchone() or (0, 0, 0)

    purchase_scope, purchase_params = _purchase_scope("cp", filters)
    cursor.execute(
        f"""
        SELECT COALESCE(SUM(CASE WHEN cp.TipoComprobante='NC' THEN -COALESCE(cp.SubtotalDesc,0)
          WHEN cp.TipoComprobante IN ('FA','FB','FC','FE','FM','ND') THEN COALESCE(cp.SubtotalDesc,0)
          ELSE 0 END),0),
          COALESCE(SUM(CASE WHEN cp.TipoComprobante='OP'
            AND cp.CondCompra IN ('Contado','-') THEN COALESCE(cp.ImportePago,0)
            ELSE 0 END),0)
        FROM cuentaproveedor cp
        WHERE cp.Fecha >= %s AND cp.Fecha < %s
          AND cp.CodigoMovimiento<>0 AND cp.Anulado='No'{purchase_scope}
        """,
        period + purchase_params,
    )
    compras, pagos = cursor.fetchone() or (0, 0)

    # comp_ped conserva id_pv y CodSucursal en Best Sox; misma intersección
    # territorial que el tablero Comercial/Ventas.
    docs_scope, docs_params = _sales_scope("cp", filters)
    cursor.execute(
        f"""
        SELECT COALESCE(SUM(cp.TipoComprobante='PRE'),0),
          COALESCE(SUM(cp.TipoComprobante='PED'),0),
          COALESCE(SUM(cp.TipoComprobante='REM'),0)
        FROM comp_ped cp
        WHERE cp.Fecha >= %s AND cp.Fecha < %s
          AND cp.CodigoMovimiento<>0 AND cp.Anulado='No'{docs_scope}
        """,
        period + docs_params,
    )
    presupuestos, pedidos, remitos = cursor.fetchone() or (0, 0, 0)

    sale_current = _sales_account_current(cursor, filters, gross=gross, has_rv=has_rv)
    purchase_current = _purchase_account_current(cursor, filters)
    return {
        "ventas": round_money(ventas), "compras_netas": round_money(compras),
        "cobranzas": round_money(cobranzas), "pagos": round_money(pagos),
        "presupuestos": int(presupuestos or 0), "pedidos": int(pedidos or 0),
        "facturas": int(facturas or 0), "remitos": int(remitos or 0),
        "venta_cuenta_corriente": round_money(sale_current),
        "compra_cuenta_corriente": round_money(purchase_current),
    }


def _sales_account_source(filters: DashboardFilters, *, gross: bool, has_rv: bool) -> tuple[str, list]:
    credit = f"({_CREDIT_TYPES})"
    debit = "('NDA','NDB','NDC','NDE','NDM')"
    adjustment = f"({_CREDIT_TYPES},'NDA','NDB','NDC','NDE','NDM')"
    total = (
        f"CASE WHEN cc.TipoComprobante IN {credit} THEN ABS(COALESCE(cc.ImporteCobro,0)) "
        "ELSE ABS(COALESCE(cc.ImporteVenta,0)) END"
    )
    joins = """LEFT JOIN cuentacliente ccv1 ON ccv1.CodigoMovimiento=CAST(cc.NroFacturaMov AS UNSIGNED)
      LEFT JOIN cuentacliente ccv2 ON ccv2.CodigoMovimiento=CAST(ccv1.NroFacturaMov AS UNSIGNED)"""
    summary_case = ""
    if has_rv:
        joins += """ LEFT JOIN (SELECT codigo_movimiento,
          MAX(ABS(COALESCE(total_efectivo,0))) total_efectivo,
          MAX(ABS(COALESCE(total_ctacte,0))) total_ctacte,
          MAX(ABS(COALESCE(total_tarjeta,0))) total_tarjeta,
          MAX(ABS(COALESCE(total_cheque,0))) total_cheque,
          MAX(ABS(COALESCE(total_transferencia,0))) total_transferencia,
          MAX(ABS(COALESCE(total_otro_medio,0))) total_otro_medio
          FROM resumen_venta_cv WHERE UPPER(COALESCE(anulado,'NO'))<>'SI'
          GROUP BY codigo_movimiento) rvcc ON rvcc.codigo_movimiento=cc.CodigoMovimiento"""
        total_rv = "(" + "+".join(
            f"ABS(COALESCE(rvcc.{field},0))" for field in (
                "total_efectivo", "total_ctacte", "total_tarjeta", "total_cheque",
                "total_transferencia", "total_otro_medio",
            )
        ) + ")"
        summary_case = (
            f"WHEN cc.TipoComprobante IN {adjustment} AND COALESCE(rvcc.total_ctacte,0)<>0 "
            f"AND {total_rv}<>0 THEN LEAST({total},{total}*ABS(rvcc.total_ctacte)/{total_rv}) "
            f"WHEN COALESCE(rvcc.total_ctacte,0)<>0 THEN LEAST({total},ABS(rvcc.total_ctacte)) "
        )
    base = (
        "CASE " + summary_case +
        "WHEN COALESCE(cc.tpv_importe_ctacte,0)<>0 THEN ABS(cc.tpv_importe_ctacte) "
        f"WHEN UPPER(TRIM(COALESCE(cc.CondVenta,''))) LIKE 'CTA/CTE%' THEN {total} "
        f"WHEN cc.TipoComprobante IN {credit} AND UPPER(TRIM(COALESCE(cc.tipo_devol_nc,'')))='CREDITO' THEN {total} "
        f"WHEN cc.TipoComprobante IN {debit} AND COALESCE(cc.NroFacturaMov,0)=0 THEN {total} "
        f"WHEN cc.TipoComprobante IN {adjustment} AND (COALESCE(ccv1.tpv_importe_ctacte,0)<>0 "
        "OR UPPER(TRIM(COALESCE(ccv1.CondVenta,''))) LIKE 'CTA/CTE%') "
        f"THEN CASE WHEN COALESCE(ccv1.tpv_importe_ctacte,0)<>0 THEN LEAST({total},ABS(ccv1.tpv_importe_ctacte)) ELSE {total} END "
        f"WHEN cc.TipoComprobante IN {adjustment} AND (COALESCE(ccv2.tpv_importe_ctacte,0)<>0 "
        "OR UPPER(TRIM(COALESCE(ccv2.CondVenta,''))) LIKE 'CTA/CTE%') "
        f"THEN CASE WHEN COALESCE(ccv2.tpv_importe_ctacte,0)<>0 THEN LEAST({total},ABS(ccv2.tpv_importe_ctacte)) ELSE {total} END "
        "ELSE 0 END"
    )
    value = f"LEAST({total},{base})" if gross else (
        f"CASE WHEN {total}<>0 THEN LEAST({total},{base})*ABS(COALESCE(cc.SubtotalDesc,0))/{total} ELSE 0 END"
    )
    value = f"({value})*CASE WHEN cc.TipoComprobante IN {credit} THEN -1 ELSE 1 END"
    scope, scope_params = _sales_scope("cc", filters)
    return (
        f"""SELECT cc.Fecha fecha,cc.CodigoMovimiento movimiento,
          cc.TipoComprobante tipo,cc.NroComprobante comprobante,
          cc.Codigo codigo_entidad,{value} importe
          FROM cuentacliente cc {joins}
          WHERE cc.Fecha >= %s AND cc.Fecha < %s
            AND COALESCE(cc.CodigoMovimiento,0)<>0
            AND UPPER(COALESCE(cc.Anulado,'NO'))<>'SI'
            AND cc.TipoComprobante IN ({_CREDIT_TYPES},{_DEBIT_TYPES}){scope}
        """,
        _period(filters) + scope_params,
    )


def _sales_account_current(cursor, filters: DashboardFilters, *, gross: bool, has_rv: bool) -> float:
    source, params = _sales_account_source(filters, gross=gross, has_rv=has_rv)
    cursor.execute(f"SELECT COALESCE(SUM(q.importe),0) FROM ({source}) q", params)
    row = cursor.fetchone()
    return float(row[0] or 0) if row else 0.0


def _purchase_account_source(filters: DashboardFilters) -> tuple[str, list]:
    total = (
        "CASE WHEN cp.TipoComprobante='NC' THEN ABS(COALESCE(cp.ImportePago,0)) "
        "ELSE ABS(COALESCE(cp.ImporteCompra,0)) END"
    )
    base = (
        f"CASE WHEN UPPER(TRIM(COALESCE(cp.CondCompra,''))) LIKE 'CTA/CTE%' THEN {total} "
        f"WHEN cp.TipoComprobante='NC' AND UPPER(TRIM(COALESCE(cp.tipo_devol_nc,'')))='CREDITO' THEN {total} "
        f"WHEN cp.TipoComprobante='ND' AND COALESCE(cp.NroFacturaMov,0)=0 THEN {total} "
        f"WHEN cp.TipoComprobante IN ('NC','ND') AND UPPER(TRIM(COALESCE(cpv1.CondCompra,''))) LIKE 'CTA/CTE%' THEN {total} "
        f"WHEN cp.TipoComprobante IN ('NC','ND') AND UPPER(TRIM(COALESCE(cpv2.CondCompra,''))) LIKE 'CTA/CTE%' THEN {total} "
        "ELSE 0 END"
    )
    value = (
        f"(CASE WHEN {total}<>0 THEN LEAST({total},{base})*ABS(COALESCE(cp.SubtotalDesc,0))/{total} "
        "ELSE 0 END)*CASE WHEN cp.TipoComprobante='NC' THEN -1 ELSE 1 END"
    )
    scope, scope_params = _purchase_scope("cp", filters)
    return (
        f"""SELECT cp.Fecha fecha,cp.CodigoMovimiento movimiento,
          cp.TipoComprobante tipo,cp.NroComprobante comprobante,
          cp.Codigo codigo_entidad,{value} importe
          FROM cuentaproveedor cp
          LEFT JOIN cuentaproveedor cpv1 ON cpv1.CodigoMovimiento=CAST(cp.NroFacturaMov AS UNSIGNED)
          LEFT JOIN cuentaproveedor cpv2 ON cpv2.CodigoMovimiento=CAST(cpv1.NroFacturaMov AS UNSIGNED)
          WHERE cp.Fecha >= %s AND cp.Fecha < %s
            AND COALESCE(cp.CodigoMovimiento,0)<>0
            AND UPPER(COALESCE(cp.Anulado,'NO'))<>'SI'
            AND cp.TipoComprobante IN ('FA','FB','FC','FE','FM','NC','ND'){scope}
        """,
        _period(filters) + scope_params,
    )


def _purchase_account_current(cursor, filters: DashboardFilters) -> float:
    source, params = _purchase_account_source(filters)
    cursor.execute(f"SELECT COALESCE(SUM(q.importe),0) FROM ({source}) q", params)
    row = cursor.fetchone()
    return float(row[0] or 0) if row else 0.0


def _snapshots(cursor, filters: DashboardFilters) -> dict:
    # Los saldos actuales y los vencimientos no tienen una relación territorial
    # comprobada en V45. Evitamos incluso consultar los importes globales.
    if filters.puntos_venta or filters.sucursales_filtro:
        return {key: None for key in (
            "efectivo_actual", "tarjetas_actual", "cheques_actual", "bancos_actual",
            "vencimiento_cobrar", "vencimiento_pagar",
            "vencimiento_cobrar_cantidad", "vencimiento_pagar_cantidad",
        )}
    values: dict = {}
    if _table_exists(cursor, "caja_saldo") and _table_exists(cursor, "caja_abm"):
        cursor.execute(
            """SELECT UPPER(ca.tipo_caja),COALESCE(SUM(cs.saldo),0)
               FROM caja_saldo cs JOIN caja_abm ca ON ca.id_caja=cs.id_caja
               WHERE ca.anulado='No' AND UPPER(COALESCE(cs.moneda,'PESOS'))='PESOS'
               AND UPPER(ca.tipo_caja) IN ('ACUMULATIVA','TARJETA','CHEQUE')
               GROUP BY UPPER(ca.tipo_caja)""", [],
        )
        balances = {str(kind): round_money(amount) for kind, amount in cursor.fetchall() or []}
        values.update({
            "efectivo_actual": balances.get("ACUMULATIVA", 0.0),
            "tarjetas_actual": balances.get("TARJETA", 0.0),
            "cheques_actual": balances.get("CHEQUE", 0.0),
        })
    else:
        values.update({"efectivo_actual": None, "tarjetas_actual": None, "cheques_actual": None})
    if _table_exists(cursor, "cuenta_banco"):
        cursor.execute(
            """SELECT COALESCE(SUM(saldo),0) FROM cuenta_banco
               WHERE anulado='No' AND UPPER(COALESCE(moneda,'PESOS'))='PESOS'""", [],
        )
        row = cursor.fetchone()
        values["bancos_actual"] = round_money(row[0] if row else 0)
    else:
        values["bancos_actual"] = None
    for table, key, kinds in (
        ("recibo_factura", "vencimiento_cobrar", f"{_INVOICE_TYPES},'NDA','NDB','NDC','NDE','NDM'"),
        ("op_factura", "vencimiento_pagar", "'FA','FB','FC','FM','ND'"),
    ):
        if not _table_exists(cursor, table):
            values[key] = None
            continue
        cursor.execute(
            f"""SELECT COALESCE(SUM(saldo),0),COUNT(*) FROM {table}
              WHERE Vencimiento >= %s AND Vencimiento < %s
              AND TipoComprobante IN ({kinds})
              AND Anulado='No' AND Estado='N/Canc'""",
            _period(filters),
        )
        amount, count = cursor.fetchone() or (0, 0)
        values[key] = round_money(amount)
        values[key + "_cantidad"] = int(count or 0)
    return values


def _series(cursor, filters: DashboardFilters, *, gross: bool) -> dict:
    days = (filters.fecha_fin - filters.fecha_inicio).days + 1
    if days <= 45:
        bucket = "dia"
        expression = "DATE_FORMAT({alias}.Fecha,'%%Y-%%m-%%d')"
    elif days <= 200:
        bucket = "semana"
        expression = "DATE_FORMAT(DATE_SUB({alias}.Fecha,INTERVAL WEEKDAY({alias}.Fecha) DAY),'%%Y-%%m-%%d')"
    else:
        bucket = "mes"
        expression = "DATE_FORMAT({alias}.Fecha,'%%Y-%%m-01')"
    sales_expr = expression.format(alias="cc")
    purchase_expr = expression.format(alias="cp")
    sales_scope, sales_params = _sales_scope("cc", filters)
    purchase_scope, purchase_params = _purchase_scope("cp", filters)
    cursor.execute(
        f"""SELECT x.fecha,COALESCE(SUM(x.ventas),0),COALESCE(SUM(x.compras),0),
          COALESCE(SUM(x.cobranzas),0),COALESCE(SUM(x.pagos),0)
          FROM (
            SELECT {sales_expr} AS fecha,SUM({_sales_amount(gross)}) AS ventas,
              0 AS compras,SUM(CASE WHEN cc.TipoComprobante='REC'
                AND cc.CondVenta IN ('Contado','-') THEN COALESCE(cc.ImporteCobro,0)
                WHEN cc.TipoComprobante IN ({_INVOICE_TYPES})
                AND cc.CondVenta IN ('Contado','-') THEN COALESCE(cc.ImporteVenta,0)
                ELSE 0 END) AS cobranzas,0 AS pagos
            FROM cuentacliente cc WHERE cc.Fecha >= %s AND cc.Fecha < %s
              AND cc.CodigoMovimiento<>0 AND cc.Anulado='No'{sales_scope}
            GROUP BY {sales_expr}
            UNION ALL
            SELECT {purchase_expr} AS fecha,0 AS ventas,
              SUM(CASE WHEN cp.TipoComprobante='NC' THEN -COALESCE(cp.SubtotalDesc,0)
                WHEN cp.TipoComprobante IN ('FA','FB','FC','FE','FM','ND') THEN COALESCE(cp.SubtotalDesc,0)
                ELSE 0 END) AS compras,0 AS cobranzas,
              SUM(CASE WHEN cp.TipoComprobante='OP' AND cp.CondCompra IN ('Contado','-')
                THEN COALESCE(cp.ImportePago,0) ELSE 0 END) AS pagos
            FROM cuentaproveedor cp WHERE cp.Fecha >= %s AND cp.Fecha < %s
              AND cp.CodigoMovimiento<>0 AND cp.Anulado='No'{purchase_scope}
            GROUP BY {purchase_expr}
          ) x GROUP BY x.fecha ORDER BY x.fecha""",
        _period(filters) + sales_params + _period(filters) + purchase_params,
    )
    return {
        "agrupacion": bucket,
        "filas": [
            {"fecha": str(day), "ventas": round_money(sale), "compras": round_money(buy),
             "cobranzas": round_money(collected), "pagos": round_money(paid)}
            for day, sale, buy, collected, paid in cursor.fetchall() or []
        ],
    }


def fetch_resumen_v45(cursor, filters: DashboardFilters, *, gross: bool = False) -> dict:
    has_rv = _table_exists(cursor, "resumen_venta_cv")
    actual = _period_metrics(cursor, filters, gross=gross, has_rv=has_rv)
    prior = comparison_filters(filters)
    before = _period_metrics(cursor, prior, gross=gross, has_rv=has_rv)
    snapshots = _snapshots(cursor, filters)
    series = _series(cursor, filters, gross=gross)
    return {
        "kpis": {**actual, **snapshots},
        "comparacion": {
            "periodo": {"inicio": prior.fecha_inicio_str, "fin": prior.fecha_fin_str},
            "kpis": before,
            "diferencias": {key: round(actual[key] - value, 2) for key, value in before.items()},
            "no_comparables": [
                "efectivo_actual", "tarjetas_actual", "cheques_actual", "bancos_actual",
                "vencimiento_cobrar", "vencimiento_pagar",
            ],
        },
        "series": series,
        "disponible": True,
        "meta": build_meta(filters, fuente="modCM_ResumenDatos.bas/V45"),
    }
