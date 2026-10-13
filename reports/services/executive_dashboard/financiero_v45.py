"""Análisis financiero V45; saldos históricos y disponibilidad de solo lectura."""
from __future__ import annotations

from datetime import timedelta

from .base import DashboardFilters, build_meta, comparison_filters, round_money
from .comercial_v45 import _scope as _sales_scope
from .compras_v45 import _scope as _purchase_scope
from .resumen_v45 import _table_exists


FINANCIERO_V45_KEYS = (
    "cobranzas", "pagos", "flujo_neto", "saldo_cobrar", "saldo_pagar",
    "vencido_cobrar", "vencido_pagar", "efectivo", "tarjetas",
    "cheques_cartera", "cheques_emitidos", "cheques_rechazados", "bancos",
    "cobrar_mas_60", "pagar_mas_60",
)


def _dates(filters: DashboardFilters) -> list[str]:
    return [filters.fecha_inicio_str, (filters.fecha_fin + timedelta(days=1)).isoformat()]


def _flows(cursor, filters: DashboardFilters) -> dict:
    sales_scope, sales_params = _sales_scope("cc", filters)
    cursor.execute(
        f"""SELECT COALESCE(SUM(CASE WHEN cc.TipoComprobante='REC'
                THEN COALESCE(cc.ImporteCobro,0)
                WHEN cc.TipoComprobante IN ('FA','FB','FC','FE','FM')
                THEN COALESCE(cc.ImporteVenta,0) ELSE 0 END),0)
            FROM cuentacliente cc WHERE cc.Fecha >= %s AND cc.Fecha < %s
              AND cc.CondVenta IN ('Contado','-')
              AND cc.TipoComprobante IN ('REC','FA','FB','FC','FE','FM')
              AND cc.CodigoMovimiento<>0 AND cc.Anulado='No'{sales_scope}""",
        _dates(filters) + sales_params,
    )
    row = cursor.fetchone()
    collected = round_money(row[0] if row else 0)
    purchase_scope, purchase_params = _purchase_scope("cp", filters)
    cursor.execute(
        f"""SELECT COALESCE(SUM(cp.ImportePago),0) FROM cuentaproveedor cp
            WHERE cp.Fecha >= %s AND cp.Fecha < %s
              AND cp.TipoComprobante='OP' AND cp.CondCompra IN ('Contado','-')
              AND cp.CodigoMovimiento<>0 AND cp.Anulado='No'{purchase_scope}""",
        _dates(filters) + purchase_params,
    )
    row = cursor.fetchone()
    paid = round_money(row[0] if row else 0)
    return {"cobranzas": collected, "pagos": paid, "flujo_neto": round_money(collected - paid)}


def _historic_balance(cursor, filters: DashboardFilters, *, clients: bool) -> float | None:
    table = "cuentacliente" if clients else "cuentaproveedor"
    if not _table_exists(cursor, table):
        return None
    pk = "id_cuentacliente" if clients else "id_cuentaproveedor"
    scope, scope_params = (_sales_scope if clients else _purchase_scope)("a", filters)
    end = (filters.fecha_fin + timedelta(days=1)).isoformat()
    if scope:
        # Cuando hay alcance, se suman cambios de saldo por movimiento;
        # sumar saldos acumulados de todas las filas duplicaría la deuda.
        cursor.execute(
            f"""SELECT COALESCE(SUM(q.importe),0) FROM (
              SELECT a.Codigo,SUM(COALESCE(a.Saldo,0)-COALESCE((
                SELECT p.Saldo FROM {table} p
                WHERE p.Codigo=a.Codigo AND p.Anulado='No' AND p.{pk}<a.{pk}
                ORDER BY p.{pk} DESC LIMIT 1),0)) importe
              FROM {table} a WHERE a.Anulado='No' AND a.Fecha < %s{scope}
              GROUP BY a.Codigo HAVING ABS(importe)>0.005
            ) q""",
            [end] + scope_params,
        )
    else:
        cursor.execute(
            f"""SELECT COALESCE(SUM(a.Saldo),0) FROM (
              SELECT u.Codigo,MAX(u.{pk}) id_ultimo FROM {table} u
              WHERE u.Anulado='No' AND u.Fecha < %s GROUP BY u.Codigo
            ) ult JOIN {table} a ON a.{pk}=ult.id_ultimo
            WHERE ABS(COALESCE(a.Saldo,0))>0.005""",
            [end],
        )
    row = cursor.fetchone()
    return round_money(row[0] if row else 0)


def _aging(cursor, filters: DashboardFilters, *, clients: bool) -> dict:
    table = "recibo_factura" if clients else "op_factura"
    if not _table_exists(cursor, table):
        return {key: None for key in (
            "vencido", "mas_60", "saldo", "por_vencer", "d0_7", "d8_30", "d31_60",
        )}
    alias = "rf" if clients else "of"
    kinds = (
        "'FA','FB','FC','FE','FM','NDA','NDB','NDC','NDE','NDM'"
        if clients else "'FA','FB','FC','FM','ND'"
    )
    origin = "cuentacliente" if clients else "cuentaproveedor"
    origin_scope, scope_params = (_sales_scope if clients else _purchase_scope)("doc", filters)
    territorial = (
        f" AND EXISTS (SELECT 1 FROM {origin} doc "
        f"WHERE doc.CodigoMovimiento={alias}.CodigoMovimiento{origin_scope})"
        if origin_scope else ""
    )
    cursor.execute(
        f"""SELECT
              COALESCE(SUM(CASE WHEN DATEDIFF(%s,{alias}.Vencimiento)<0 THEN {alias}.Saldo ELSE 0 END),0),
              COALESCE(SUM(CASE WHEN DATEDIFF(%s,{alias}.Vencimiento) BETWEEN 0 AND 7 THEN {alias}.Saldo ELSE 0 END),0),
              COALESCE(SUM(CASE WHEN DATEDIFF(%s,{alias}.Vencimiento) BETWEEN 8 AND 30 THEN {alias}.Saldo ELSE 0 END),0),
              COALESCE(SUM(CASE WHEN DATEDIFF(%s,{alias}.Vencimiento) BETWEEN 31 AND 60 THEN {alias}.Saldo ELSE 0 END),0),
              COALESCE(SUM(CASE WHEN DATEDIFF(%s,{alias}.Vencimiento)>=61 THEN {alias}.Saldo ELSE 0 END),0)
            FROM {table} {alias} WHERE {alias}.Vencimiento IS NOT NULL
              AND {alias}.TipoComprobante IN ({kinds})
              AND {alias}.Anulado='No' AND {alias}.Estado='N/Canc'{territorial}""",
        [filters.fecha_fin_str] * 5 + scope_params,
    )
    row = cursor.fetchone() or (0,) * 5
    future, d0, d8, d31, d61 = (round_money(value) for value in row)
    return {
        "por_vencer": future, "d0_7": d0, "d8_30": d8,
        "d31_60": d31, "mas_60": d61,
        "vencido": round_money(d0 + d8 + d31 + d61),
        "saldo": round_money(future + d0 + d8 + d31 + d61),
    }


def _cash_and_checks(cursor, filters: DashboardFilters) -> dict:
    # Cajas, cheques y bancos no comparten una clave territorial unívoca;
    # no se expone el saldo global con filtros parciales.
    if filters.puntos_venta or filters.sucursales_filtro:
        return {
            "efectivo": None, "tarjetas": None, "cheques_cartera": None,
            "cheques_emitidos": None, "cheques_rechazados": None, "bancos": None,
        }
    result = {}
    if _table_exists(cursor, "caja_saldo") and _table_exists(cursor, "caja_abm"):
        cursor.execute(
            """SELECT UPPER(ca.tipo_caja),COALESCE(SUM(cs.saldo),0)
                FROM caja_saldo cs JOIN caja_abm ca ON ca.id_caja=cs.id_caja
                WHERE ca.anulado='No' AND UPPER(COALESCE(cs.moneda,'PESOS'))='PESOS'
                  AND UPPER(ca.tipo_caja) IN ('ACUMULATIVA','TARJETA')
                GROUP BY UPPER(ca.tipo_caja)""", [],
        )
        balances = {kind: round_money(value) for kind, value in cursor.fetchall() or []}
        result["efectivo"] = balances.get("ACUMULATIVA", 0.0)
        result["tarjetas"] = balances.get("TARJETA", 0.0)
    else:
        result["efectivo"] = result["tarjetas"] = None
    if _table_exists(cursor, "chequetercero"):
        cursor.execute(
            """SELECT COALESCE(SUM(CASE WHEN UPPER(COALESCE(Encartera,''))='SI'
                THEN COALESCE(Importe,0) ELSE 0 END),0),
              COALESCE(SUM(CASE WHEN UPPER(COALESCE(Rechazado,''))='SI'
                THEN COALESCE(Importe,0) ELSE 0 END),0)
              FROM chequetercero WHERE UPPER(COALESCE(Anulado,''))='NO'""", [],
        )
        row = cursor.fetchone() or (0, 0)
        result["cheques_cartera"] = round_money(row[0])
        rejected = float(row[1] or 0)
    else:
        result["cheques_cartera"] = None
        rejected = 0.0
    if _table_exists(cursor, "chequepropio"):
        cursor.execute(
            """SELECT COALESCE(SUM(CASE WHEN UPPER(COALESCE(pagado,''))='NO'
                AND UPPER(COALESCE(rechazado,''))='NO'
                AND UPPER(COALESCE(en_nd_proveedor,''))='NO'
                THEN COALESCE(Importe,0) ELSE 0 END),0),
              COALESCE(SUM(CASE WHEN UPPER(COALESCE(rechazado,''))='SI'
                THEN COALESCE(Importe,0) ELSE 0 END),0)
              FROM chequepropio WHERE UPPER(COALESCE(Anulado,''))='NO'""", [],
        )
        row = cursor.fetchone() or (0, 0)
        result["cheques_emitidos"] = round_money(row[0])
        rejected += float(row[1] or 0)
    else:
        result["cheques_emitidos"] = None
    result["cheques_rechazados"] = round_money(rejected) if (
        result["cheques_cartera"] is not None or result["cheques_emitidos"] is not None
    ) else None
    if _table_exists(cursor, "cuenta_banco"):
        cursor.execute(
            """SELECT COALESCE(SUM(saldo),0) FROM cuenta_banco
              WHERE anulado='No' AND UPPER(COALESCE(moneda,'PESOS'))='PESOS'""", [],
        )
        row = cursor.fetchone()
        result["bancos"] = round_money(row[0] if row else 0)
    else:
        result["bancos"] = None
    return result


def _flow_series(cursor, filters: DashboardFilters) -> dict:
    days = (filters.fecha_fin - filters.fecha_inicio).days + 1
    if days <= 45:
        bucket = "dia"
        label = "DATE_FORMAT({alias}.Fecha,'%%Y-%%m-%%d')"
    elif days <= 200:
        bucket = "semana"
        label = "DATE_FORMAT(DATE_SUB({alias}.Fecha,INTERVAL WEEKDAY({alias}.Fecha) DAY),'%%Y-%%m-%%d')"
    else:
        bucket = "mes"
        label = "DATE_FORMAT({alias}.Fecha,'%%Y-%%m-01')"
    sales_scope, sales_params = _sales_scope("cc", filters)
    purchase_scope, purchase_params = _purchase_scope("cp", filters)
    sale_label = label.format(alias="cc")
    purchase_label = label.format(alias="cp")
    cursor.execute(
        f"""SELECT x.fecha,COALESCE(SUM(x.cobranzas),0),COALESCE(SUM(x.pagos),0)
            FROM (SELECT {sale_label} fecha,
              SUM(CASE WHEN cc.TipoComprobante='REC' THEN COALESCE(cc.ImporteCobro,0)
                WHEN cc.TipoComprobante IN ('FA','FB','FC','FE','FM')
                THEN COALESCE(cc.ImporteVenta,0) ELSE 0 END) cobranzas,0 pagos
              FROM cuentacliente cc WHERE cc.Fecha >= %s AND cc.Fecha < %s
                AND cc.CondVenta IN ('Contado','-') AND cc.CodigoMovimiento<>0
                AND cc.Anulado='No'
                AND cc.TipoComprobante IN ('REC','FA','FB','FC','FE','FM'){sales_scope}
              GROUP BY {sale_label}
              UNION ALL SELECT {purchase_label} fecha,0 cobranzas,
                SUM(cp.ImportePago) pagos FROM cuentaproveedor cp
              WHERE cp.Fecha >= %s AND cp.Fecha < %s
                AND cp.TipoComprobante='OP' AND cp.CondCompra IN ('Contado','-')
                AND cp.CodigoMovimiento<>0 AND cp.Anulado='No'{purchase_scope}
              GROUP BY {purchase_label}) x
            GROUP BY x.fecha ORDER BY x.fecha""",
        _dates(filters) + sales_params + _dates(filters) + purchase_params,
    )
    return {
        "agrupacion": bucket,
        "filas": [
            {"fecha": str(day), "cobranzas": round_money(collected), "pagos": round_money(paid)}
            for day, collected, paid in cursor.fetchall() or []
        ],
    }


def fetch_financiero_v45(cursor, filters: DashboardFilters) -> dict:
    prior = comparison_filters(filters)
    flow = _flows(cursor, filters)
    previous_flow = _flows(cursor, prior)
    cobrar = _aging(cursor, filters, clients=True)
    pagar = _aging(cursor, filters, clients=False)
    current = {
        **flow,
        "saldo_cobrar": _historic_balance(cursor, filters, clients=True),
        "saldo_pagar": _historic_balance(cursor, filters, clients=False),
        "vencido_cobrar": cobrar["vencido"],
        "vencido_pagar": pagar["vencido"],
        "cobrar_mas_60": cobrar["mas_60"],
        "pagar_mas_60": pagar["mas_60"],
        **_cash_and_checks(cursor, filters),
    }
    return {
        "kpis": current,
        "aging": {"cobrar": cobrar, "pagar": pagar},
        "comparacion": {
            "periodo": {"inicio": prior.fecha_inicio_str, "fin": prior.fecha_fin_str},
            "kpis": previous_flow,
            "diferencias": {key: round_money(flow[key] - previous_flow[key]) for key in flow},
        },
        "serie_flujo": _flow_series(cursor, filters),
        "disponible": True,
        "meta": build_meta(filters, fuente="modCM_FinancieroDatos.bas/V45"),
    }
