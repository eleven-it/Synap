"""Abastecimiento/Compras V45 según modCM_ComprasDatos.bas."""
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

from .base import DashboardFilters, build_meta, round_money


COMPRAS_V45_KEYS = (
    "compras_netas", "facturas", "ticket_promedio", "notas_credito",
    "ordenes_compra", "monto_oc", "oc_pendientes", "monto_pendiente",
    "oc_parciales", "remitos_recibidos", "remitos_sin_factura",
    "oc_vencidas", "proveedores", "plazo_promedio",
)


def _has(cursor, table: str, column: str | None = None) -> bool:
    if column:
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema=DATABASE() AND table_name=%s AND column_name=%s",
            [table, column],
        )
    else:
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema=DATABASE() AND table_name=%s", [table],
        )
    row = cursor.fetchone()
    return bool(row and row[0])


def _scope(alias: str, filters: DashboardFilters) -> tuple[str, list[int]]:
    # El módulo V45 de compras filtra por sucursal, no por PV.
    if not filters.sucursales_filtro:
        return "", []
    return (
        f" AND {alias}.CodSucursal IN ({','.join(['%s'] * len(filters.sucursales_filtro))})",
        list(filters.sucursales_filtro),
    )


def _dates(filters: DashboardFilters) -> list[str]:
    return [filters.fecha_inicio_str, (filters.fecha_fin + timedelta(days=1)).isoformat()]


def _period(cursor, filters: DashboardFilters, options: dict[str, bool]) -> dict:
    scope, scope_params = _scope("cp", filters)
    cursor.execute(
        f"""SELECT COALESCE(SUM(CASE WHEN cp.TipoComprobante='NC'
                  THEN -COALESCE(cp.SubtotalDesc,0)
                  WHEN cp.TipoComprobante IN ('FA','FB','FC','FE','FM','ND')
                  THEN COALESCE(cp.SubtotalDesc,0) ELSE 0 END),0),
              COALESCE(SUM(cp.TipoComprobante IN ('FA','FB','FC','FE','FM')),0),
              COALESCE(SUM(cp.TipoComprobante='NC'),0),
              COUNT(DISTINCT CASE WHEN cp.TipoComprobante IN ('FA','FB','FC','FE','FM')
                THEN cp.Codigo END),
              COALESCE(SUM(cp.TipoComprobante='OC'),0),
              COALESCE(SUM(CASE WHEN cp.TipoComprobante='OC'
                THEN COALESCE(cp.SubtotalDesc,0) ELSE 0 END),0),
              COALESCE(SUM(cp.TipoComprobante='REM'),0)
            FROM cuentaproveedor cp WHERE cp.Fecha >= %s AND cp.Fecha < %s
              AND cp.CodigoMovimiento<>0 AND cp.Anulado='No'
              AND cp.TipoComprobante IN ('FA','FB','FC','FE','FM','NC','ND','OC','REM'){scope}""",
        _dates(filters) + scope_params,
    )
    row = cursor.fetchone() or (0,) * 7
    buys, bills, credits, vendors, orders, order_amount, remitos = row
    values = {
        "compras_netas": round_money(buys),
        "facturas": int(bills or 0),
        "ticket_promedio": round_money(float(buys or 0) / int(bills)) if bills else None,
        "notas_credito": int(credits or 0),
        "proveedores": int(vendors or 0),
        "ordenes_compra": int(orders or 0),
        "monto_oc": round_money(order_amount),
        "remitos_recibidos": int(remitos or 0),
    }
    # Las métricas de estado son una foto de todas las OC abiertas al corte.
    due = (
        "COALESCE(SUM(CASE WHEN cp.fecha_entrega_oc IS NOT NULL AND cp.fecha_entrega_oc < %s "
        "AND UPPER(COALESCE(cp.Estado,'')) IN ('PENDIENTE','PARCIAL','EN REMITO') "
        "THEN 1 ELSE 0 END),0)"
        if options["due"] else "0"
    )
    cursor.execute(
        f"""SELECT COALESCE(SUM(UPPER(COALESCE(cp.Estado,''))='PENDIENTE'),0),
              COALESCE(SUM(UPPER(COALESCE(cp.Estado,''))='PARCIAL'),0),
              COALESCE(SUM(CASE WHEN UPPER(COALESCE(cp.Estado,''))
                IN ('PENDIENTE','PARCIAL','EN REMITO')
                THEN COALESCE(cp.SubtotalDesc,0) ELSE 0 END),0),
              {due}
            FROM cuentaproveedor cp
            WHERE cp.TipoComprobante='OC' AND cp.CodigoMovimiento<>0
              AND cp.Anulado='No'{scope}""",
        ([(filters.fecha_fin + timedelta(days=1)).isoformat()] if options["due"] else []) + scope_params,
    )
    pending, partial, open_amount, overdue = cursor.fetchone() or (0, 0, 0, 0)
    values.update({
        "oc_pendientes": int(pending or 0),
        "oc_parciales": int(partial or 0),
        "monto_pendiente": round_money(open_amount),
        "oc_vencidas": int(overdue or 0) if options["due"] else None,
    })
    if options["line_amount"]:
        cursor.execute(
            f"""SELECT COALESCE(SUM(CASE WHEN COALESCE(sp.Cantidad,0)>0
                    THEN COALESCE(sp.PrecioNetoxR,0)*
                      GREATEST(COALESCE(sp.cantidad_pendiente,0),0)/sp.Cantidad
                    ELSE 0 END),0)
                FROM stockp sp JOIN cuentaproveedor cp
                  ON cp.CodigoMovimiento=sp.CodigoMovimiento
                WHERE cp.TipoComprobante='OC' AND cp.Anulado='No'
                  AND cp.CodigoMovimiento<>0
                  AND UPPER(COALESCE(cp.Estado,'')) IN ('PENDIENTE','PARCIAL','EN REMITO')
                  AND sp.Anulado='No' AND sp.Comprobante='OC'{scope}""",
            scope_params,
        )
        detail = cursor.fetchone()
        values["monto_pendiente"] = round_money(detail[0] if detail else 0)
    if options["receipt_state"]:
        cursor.execute(
            f"""SELECT COUNT(*) FROM cuentaproveedor cp
                WHERE cp.TipoComprobante='REM' AND cp.CodigoMovimiento<>0
                  AND cp.Anulado='No'
                  AND UPPER(COALESCE(cp.estado_remito,''))='PENDIENTE'{scope}""",
            scope_params,
        )
        row = cursor.fetchone()
        values["remitos_sin_factura"] = int(row[0] or 0) if row else 0
    else:
        values["remitos_sin_factura"] = None
    if options["receipt_date"]:
        cursor.execute(
            f"""SELECT AVG(DATEDIFF(cp.fecha_recepcion,cp.Fecha)),COUNT(*)
                FROM cuentaproveedor cp
                WHERE cp.TipoComprobante='OC' AND cp.Fecha >= %s AND cp.Fecha < %s
                  AND cp.fecha_recepcion IS NOT NULL AND cp.fecha_recepcion>=cp.Fecha
                  AND UPPER(COALESCE(cp.Estado,'')) IN ('CERRADO','FACTURADO','EN REMITO')
                  AND cp.CodigoMovimiento<>0 AND cp.Anulado='No'{scope}""",
            _dates(filters) + scope_params,
        )
        avg_days, valid_count = cursor.fetchone() or (None, 0)
        values["plazo_promedio"] = round(float(avg_days), 2) if valid_count and avg_days is not None else None
    else:
        values["plazo_promedio"] = None
    return values


def _series(cursor, filters: DashboardFilters) -> dict:
    scope, scope_params = _scope("cp", filters)
    days = (filters.fecha_fin - filters.fecha_inicio).days + 1
    if days <= 45:
        bucket, expression = "día", "DATE_FORMAT(cp.Fecha,'%%Y-%%m-%%d')"
    elif days <= 200:
        bucket, expression = "semana", "DATE_FORMAT(DATE_SUB(cp.Fecha,INTERVAL WEEKDAY(cp.Fecha) DAY),'%%Y-%%m-%%d')"
    else:
        bucket, expression = "mes", "DATE_FORMAT(cp.Fecha,'%%Y-%%m-01')"
    cursor.execute(
        f"""SELECT {expression},
          COALESCE(SUM(CASE WHEN cp.TipoComprobante='NC' THEN -COALESCE(cp.SubtotalDesc,0)
            WHEN cp.TipoComprobante IN ('FA','FB','FC','FE','FM','ND') THEN COALESCE(cp.SubtotalDesc,0)
            ELSE 0 END),0),
          COALESCE(SUM(CASE WHEN cp.TipoComprobante='OC' THEN COALESCE(cp.SubtotalDesc,0) ELSE 0 END),0)
          FROM cuentaproveedor cp WHERE cp.Fecha >= %s AND cp.Fecha < %s
            AND cp.CodigoMovimiento<>0 AND cp.Anulado='No'
            AND cp.TipoComprobante IN ('FA','FB','FC','FE','FM','NC','ND','OC'){scope}
          GROUP BY {expression} ORDER BY {expression}""",
        _dates(filters) + scope_params,
    )
    return {
        "agrupacion": bucket,
        "filas": [
            {"fecha": str(day), "compras": round_money(buy), "ordenes": round_money(order)}
            for day, buy, order in cursor.fetchall() or []
        ],
    }


def fetch_compras_v45(cursor, filters: DashboardFilters) -> dict:
    if not _has(cursor, "cuentaproveedor"):
        return {"disponible": False, "motivo": "sin_cuentaproveedor", "kpis": {}}
    options = {
        "due": _has(cursor, "cuentaproveedor", "fecha_entrega_oc"),
        "receipt_state": _has(cursor, "cuentaproveedor", "estado_remito"),
        "receipt_date": _has(cursor, "cuentaproveedor", "fecha_recepcion"),
        "line_amount": _has(cursor, "stockp") and _has(cursor, "stockp", "cantidad_pendiente"),
    }
    actual = _period(cursor, filters, options)
    days = (filters.fecha_fin - filters.fecha_inicio).days + 1
    previous_filters = replace(
        filters, fecha_inicio=filters.fecha_inicio - timedelta(days=days),
        fecha_fin=filters.fecha_inicio - timedelta(days=1),
        fecha_referencia=filters.fecha_inicio - timedelta(days=1),
    )
    previous = _period(cursor, previous_filters, options)
    return {
        "kpis": actual,
        "comparacion": {
            "periodo": {"inicio": previous_filters.fecha_inicio_str, "fin": previous_filters.fecha_fin_str},
            "kpis": previous,
            "diferencias": {
                key: round_money(actual[key] - previous[key])
                for key in COMPRAS_V45_KEYS
                if actual.get(key) is not None and previous.get(key) is not None
            },
            "no_comparables": ["oc_pendientes", "monto_pendiente", "oc_parciales", "remitos_sin_factura", "oc_vencidas"],
        },
        "serie_evolucion": _series(cursor, filters),
        "disponible": True,
        "meta": build_meta(filters, fuente="modCM_ComprasDatos.bas/V45"),
    }
