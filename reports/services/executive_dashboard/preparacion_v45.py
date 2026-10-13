"""Preparación de pedidos V45; reglas de modCM_PreparacionDatos.bas."""
from __future__ import annotations

from datetime import timedelta

from .base import DashboardFilters, build_meta, comparison_filters, round_money
from .comercial_v45 import _scope


PREPARACION_V45_KEYS = (
    "pedidos_ingresados", "monto_pedidos", "pendientes", "monto_pendiente",
    "en_preparacion", "preparados", "backorder", "monto_backorder",
    "en_remito", "facturados", "cerrados", "anulados",
    "unidades_pendientes", "tiempo_promedio", "monto_facturado", "monto_en_remito",
)


def _exists(cursor, table: str, column: str | None = None) -> bool:
    if column is None:
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema=DATABASE() AND table_name=%s", [table],
        )
    else:
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema=DATABASE() AND table_name=%s AND column_name=%s",
            [table, column],
        )
    row = cursor.fetchone()
    return bool(row and row[0])


def _dates(filters: DashboardFilters) -> list[str]:
    return [filters.fecha_inicio_str, (filters.fecha_fin + timedelta(days=1)).isoformat()]


def _states(has_original: bool) -> dict[str, str]:
    estado = "UPPER(TRIM(COALESCE(cp.Estado,'')))"
    related = (
        "(COALESCE(cp.cod_mov_ped_orginal,0)<>0 "
        "AND COALESCE(cp.cod_mov_ped_orginal,0)<>COALESCE(cp.CodigoMovimiento,0))"
    )
    backorder = f"{estado} IN ('BACKORDER','BACK ORDER')"
    if has_original:
        backorder = (
            f"({backorder} OR ({related} AND "
            f"({estado} IN ('PENDIENTE','PREPARADO','PARCIAL','BACKORDER','BACK ORDER') "
            f"OR {estado} LIKE 'EN PREPARA%%')))"
        )
    return {
        "backorder": backorder,
        "pendientes": f"({estado}='PENDIENTE' AND NOT ({backorder}))",
        "en_preparacion": f"({estado} LIKE 'EN PREPARA%%' AND NOT ({backorder}))",
        "preparados": f"({estado}='PREPARADO' AND NOT ({backorder}))",
        "en_remito": f"{estado} IN ('EN REMITO','REMITIDO')",
        "facturados": f"{estado}='FACTURADO'",
        "cerrados": f"{estado} IN ('CERRADO','FINALIZADO','COMPLETADO')",
    }


def _base_orders(cursor, filters: DashboardFilters, states: dict[str, str]) -> dict:
    scope, scope_params = _scope("cp", filters)
    expressions = [
        "SUM(CASE WHEN UPPER(COALESCE(cp.Anulado,'NO'))<>'SI' THEN 1 ELSE 0 END)",
        "SUM(CASE WHEN UPPER(COALESCE(cp.Anulado,'NO'))<>'SI' THEN COALESCE(cp.ImporteVenta,0) ELSE 0 END)",
    ]
    for key in ("pendientes", "en_preparacion", "preparados", "backorder", "en_remito", "facturados", "cerrados"):
        expressions.append(
            f"SUM(CASE WHEN UPPER(COALESCE(cp.Anulado,'NO'))<>'SI' "
            f"AND {states[key]} THEN 1 ELSE 0 END)"
        )
        if key in {"pendientes", "backorder"}:
            expressions.append(
                f"SUM(CASE WHEN UPPER(COALESCE(cp.Anulado,'NO'))<>'SI' "
                f"AND {states[key]} THEN COALESCE(cp.ImporteVenta,0) ELSE 0 END)"
            )
    expressions.append("SUM(CASE WHEN UPPER(COALESCE(cp.Anulado,'NO'))='SI' THEN 1 ELSE 0 END)")
    cursor.execute(
        f"SELECT {','.join(expressions)} FROM comp_ped cp "
        f"WHERE cp.Fecha >= %s AND cp.Fecha < %s "
        f"AND cp.TipoComprobante='PED' AND cp.CodigoMovimiento<>0{scope}",
        _dates(filters) + scope_params,
    )
    row = list(cursor.fetchone() or [0] * len(expressions))
    keys = [
        "pedidos_ingresados", "monto_pedidos", "pendientes", "monto_pendiente",
        "en_preparacion", "preparados", "backorder", "monto_backorder",
        "en_remito", "facturados", "cerrados", "anulados",
    ]
    return {
        key: round_money(value) if key.startswith("monto_") else int(value or 0)
        for key, value in zip(keys, row)
    }


def _linked(cursor, filters: DashboardFilters, *, invoice: bool) -> tuple[int, float]:
    scope, scope_params = _scope("cp", filters)
    if invoice:
        join = "JOIN cuentacliente doc ON doc.CodigoMovimiento=s.CodigoMovimiento"
        condition = (
            "s.TipoComp IN ('Venta','Venta TPV','ND Anul NC') "
            "AND doc.TipoComprobante IN ('FA','FB','FC','FE','FM','NDA','NDB','NDC','NDE','NDM')"
        )
    else:
        join = "JOIN comp_ped doc ON doc.CodigoMovimiento=s.codmov_remito"
        condition = "doc.TipoComprobante='REM'"
    cursor.execute(
        f"""SELECT COUNT(DISTINCT cp.CodigoMovimiento) FROM comp_ped cp
            WHERE cp.Fecha >= %s AND cp.Fecha < %s
              AND cp.TipoComprobante='PED' AND cp.CodigoMovimiento<>0
              AND UPPER(COALESCE(cp.Anulado,'NO'))<>'SI'{scope}
              AND EXISTS (SELECT 1 FROM stock s {join}
                WHERE s.codmov_pedido=cp.CodigoMovimiento
                  AND UPPER(COALESCE(s.Anulado,'NO'))<>'SI'
                  AND UPPER(COALESCE(doc.Anulado,'NO'))<>'SI'
                  AND {condition})""",
        _dates(filters) + scope_params,
    )
    row = cursor.fetchone()
    count = row[0] if row else 0
    # Una factura puede consolidar varios pedidos; sumar una vez por documento.
    cursor.execute(
        f"""SELECT COALESCE(SUM(z.importe),0) FROM (
              SELECT doc.CodigoMovimiento,MAX(COALESCE(doc.ImporteVenta,0)) importe
              FROM comp_ped cp JOIN stock s ON s.codmov_pedido=cp.CodigoMovimiento
              {join}
              WHERE cp.Fecha >= %s AND cp.Fecha < %s
                AND cp.TipoComprobante='PED' AND cp.CodigoMovimiento<>0
                AND UPPER(COALESCE(cp.Anulado,'NO'))<>'SI'
                AND UPPER(COALESCE(s.Anulado,'NO'))<>'SI'
                AND UPPER(COALESCE(doc.Anulado,'NO'))<>'SI'
                AND {condition}{scope}
              GROUP BY doc.CodigoMovimiento
            ) z""",
        _dates(filters) + scope_params,
    )
    row = cursor.fetchone()
    return int(count or 0), round_money(row[0] if row else 0)


def _units(cursor, filters: DashboardFilters, states: dict[str, str]) -> float | None:
    if not _exists(cursor, "stockp") or not _exists(cursor, "stockp", "cantidad_pendiente"):
        return None
    scope, scope_params = _scope("cp", filters)
    active = "UPPER(COALESCE(cp.Anulado,'NO'))<>'SI'"
    stock_active = "AND UPPER(COALESCE(sp.Anulado,'NO'))<>'SI'" if _exists(cursor, "stockp", "Anulado") else ""
    condition = " OR ".join(f"({states[key]})" for key in ("pendientes", "backorder", "en_preparacion"))
    cursor.execute(
        f"""SELECT COALESCE(SUM(CASE WHEN {condition} THEN COALESCE(sp.cantidad_pendiente,0) ELSE 0 END),0)
            FROM comp_ped cp JOIN stockp sp ON sp.CodigoMovimiento=cp.CodigoMovimiento
            WHERE cp.Fecha >= %s AND cp.Fecha < %s AND cp.TipoComprobante='PED'
              AND cp.CodigoMovimiento<>0 AND {active}{stock_active}{scope}""",
        _dates(filters) + scope_params,
    )
    row = cursor.fetchone()
    return round_money(row[0] if row else 0)


def _time(cursor, filters: DashboardFilters) -> float | None:
    if not _exists(cursor, "comp_ped", "fecha_hora_preparacion"):
        return None
    if _exists(cursor, "comp_ped", "fecha_hora_entrega"):
        end = "fecha_hora_entrega"
    elif _exists(cursor, "comp_ped", "fecha_hora_fin_preparacion"):
        end = "fecha_hora_fin_preparacion"
    else:
        return None
    def parse(field: str) -> str:
        return (
            f"COALESCE(STR_TO_DATE(NULLIF(cp.{field},''),'%%Y-%%m-%%d %%H:%%i:%%s'),"
            f"STR_TO_DATE(NULLIF(cp.{field},''),'%%d/%%m/%%Y %%H:%%i:%%s'))"
        )
    scope, scope_params = _scope("cp", filters)
    cursor.execute(
        f"""SELECT AVG(x.minutos)/60,COUNT(*) FROM (
              SELECT TIMESTAMPDIFF(MINUTE,{parse('fecha_hora_preparacion')},{parse(end)}) minutos
              FROM comp_ped cp WHERE cp.Fecha >= %s AND cp.Fecha < %s
                AND cp.TipoComprobante='PED' AND cp.CodigoMovimiento<>0
                AND UPPER(COALESCE(cp.Anulado,'NO'))<>'SI'
                AND cp.fecha_hora_preparacion NOT IN ('','0000-00-00 00:00:00')
                AND cp.{end} NOT IN ('','0000-00-00 00:00:00'){scope}
            ) x WHERE x.minutos BETWEEN 0 AND 43200""",
        _dates(filters) + scope_params,
    )
    value, count = cursor.fetchone() or (None, 0)
    return round(float(value), 2) if count and value is not None else None


def _period_metrics(cursor, filters: DashboardFilters, states: dict[str, str], *, links: dict[str, bool]) -> dict:
    metrics = _base_orders(cursor, filters, states)
    if links["facturas"]:
        metrics["facturados"], metrics["monto_facturado"] = _linked(cursor, filters, invoice=True)
    else:
        metrics["monto_facturado"] = None
    if links["remitos"]:
        metrics["en_remito"], metrics["monto_en_remito"] = _linked(cursor, filters, invoice=False)
    else:
        metrics["monto_en_remito"] = None
    metrics["unidades_pendientes"] = _units(cursor, filters, states)
    metrics["tiempo_promedio"] = _time(cursor, filters)
    return metrics


def fetch_preparacion_v45(cursor, filters: DashboardFilters) -> dict:
    if not _exists(cursor, "comp_ped"):
        return {"disponible": False, "motivo": "sin_tabla_comp_ped", "kpis": {}}
    states = _states(_exists(cursor, "comp_ped", "cod_mov_ped_orginal"))
    stock_link = _exists(cursor, "stock") and _exists(cursor, "stock", "codmov_pedido")
    links = {
        "facturas": stock_link and _exists(cursor, "cuentacliente"),
        "remitos": stock_link and _exists(cursor, "stock", "codmov_remito"),
    }
    actual = _period_metrics(cursor, filters, states, links=links)
    previous_filters = comparison_filters(filters)
    previous = _period_metrics(cursor, previous_filters, states, links=links)
    state_keys = (
        ("Pendientes", "pendientes"), ("Backorder", "backorder"),
        ("En preparación", "en_preparacion"), ("Preparados", "preparados"),
        ("En remito", "en_remito"), ("Facturados", "facturados"),
        ("Cerrados", "cerrados"), ("Anulados", "anulados"),
    )
    amount_keys = (
        ("Pendientes", "monto_pendiente"), ("Backorder", "monto_backorder"),
        ("En remito", "monto_en_remito"), ("Facturados", "monto_facturado"),
    )
    return {
        "kpis": actual,
        "serie_estados": [
            {"estado": label, "actual": actual[key], "anterior": previous[key]}
            for label, key in state_keys
        ],
        "serie_importes": [
            {"estado": label, "importe": actual[key]}
            for label, key in amount_keys
        ],
        "comparacion": {
            "periodo": {"inicio": previous_filters.fecha_inicio_str, "fin": previous_filters.fecha_fin_str},
            "kpis": previous,
            "diferencias": {
                key: round_money(actual[key] - previous[key])
                for key in PREPARACION_V45_KEYS
                if actual.get(key) is not None and previous.get(key) is not None
            },
        },
        "disponible": True,
        "meta": build_meta(filters, fuente="modCM_PreparacionDatos.bas/V45"),
    }
