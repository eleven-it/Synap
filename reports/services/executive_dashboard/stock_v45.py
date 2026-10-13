"""Resumen Abastecimiento/Stock según modCM_StockDatos.bas de V45."""
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

from .base import DashboardFilters, build_meta, round_money


STOCK_V45_KEYS = (
    "stock_valorizado", "unidades_disponibles", "articulos_con_stock",
    "articulos_stock_negativo", "bajo_minimo", "punto_pedido", "sobre_maximo",
    "stock_reservado", "pendiente_recibir", "entradas_periodo", "salidas_periodo",
    "valor_entradas", "valor_salidas", "sin_movimiento_90d",
)


def _deposit_scope(alias: str, filters: DashboardFilters) -> tuple[str, list[int]]:
    if not filters.depositos_filtro:
        return "", []
    return (
        f" AND {alias}.CodDeposito IN ({','.join(['%s'] * len(filters.depositos_filtro))})",
        list(filters.depositos_filtro),
    )


def _article_filter(alias: str = "a") -> str:
    return (
        f"UPPER(COALESCE({alias}.tipo_art,'ARTICULO')) NOT IN ('GASTO','SERVICIO') "
        f"AND UPPER(COALESCE({alias}.Discontinuo,'NO')) <> 'SI'"
    )


def _deposit_filter(alias: str = "dep") -> str:
    return (
        f"UPPER(COALESCE({alias}.anulado,'NO')) <> 'SI' "
        f"AND UPPER(TRIM(COALESCE({alias}.suma_stock,'NO'))) = 'SI'"
    )


def _ap_join(article: str = "a", ap: str = "ap") -> str:
    return f"""
      LEFT JOIN articulo_prov {ap} ON {ap}.id_articulo_prov = (
        SELECT ap0.id_articulo_prov FROM articulo_prov ap0
        WHERE ap0.IDArt = {article}.IDArt
        ORDER BY CASE WHEN ap0.CodProveedor = {article}.CodigoProveedor THEN 0 ELSE 1 END,
          ap0.CodProveedor, ap0.id_articulo_prov LIMIT 1)
    """


def _factors(*, presentation: str, stock_alias: str | None = None) -> tuple[str, str]:
    display_raw = "NULLIF(ap.cantidad_unidad_display,0)"
    pack_raw = "COALESCE(NULLIF(ap.multiplicador_comp,0),NULLIF(ap.cantidad_display_bulto,0),0)"
    if stock_alias:
        display_raw = f"COALESCE({display_raw},NULLIF({stock_alias}.cantidad_unidad_display,0),0)"
        pack_raw = f"COALESCE(NULLIF({pack_raw},0),NULLIF({stock_alias}.multiplicador_comp,0),0)"
    display = f"IF(COALESCE({display_raw},0)>0,({display_raw}),1)"
    pack = f"IF(COALESCE({display_raw},0)>0 AND ({pack_raw})>0,({display_raw})*({pack_raw}),1)"
    cost = (
        "CASE UPPER(TRIM(COALESCE(ap.precio_unidad,'UNIDAD'))) "
        f"WHEN 'DISPLAY' THEN {display} WHEN 'BULTO' THEN {pack} "
        f"WHEN 'BULTO/PALLET' THEN {pack} ELSE 1 END"
    )
    factor = {"unidad": "1", "display": display, "bulto": pack}[presentation]
    return factor, cost


def _current(cursor, filters: DashboardFilters, presentation: str) -> dict:
    dep_scope, params = _deposit_scope("dep", filters)
    factor, cost_factor = _factors(presentation=presentation)
    cursor.execute(
        f"""
        SELECT
          COALESCE(SUM(IF(x.saldo>0,x.saldo*x.costo_base,0)),0) AS valorizado,
          COALESCE(SUM(IF(x.saldo>0,x.saldo/x.factor,0)),0) AS unidades,
          COALESCE(SUM(x.saldo>0),0) AS con_stock,
          COALESCE(SUM(x.saldo<0),0) AS negativos,
          COALESCE(SUM(IF(x.reservado>0,x.reservado/x.factor,0)),0) AS reservado,
          COALESCE(SUM(IF(x.pendiente>0,x.pendiente/x.factor,0)),0) AS pendiente
        FROM (
          SELECT a.IDArt,
            COALESCE(a.PrecioCosto,0)/NULLIF(MAX({cost_factor}),0) AS costo_base,
            MAX({factor}) AS factor,
            COALESCE(SUM(sd.saldo),0) AS saldo,
            COALESCE(SUM(sd.saldo_pedido_cliente),0) AS reservado,
            COALESCE(SUM(sd.saldo_pedido_proveedor),0) AS pendiente
          FROM stock_deposito sd
          JOIN articulo a ON a.IDArt = sd.id_articulo
          JOIN deposito dep ON dep.CodDeposito = sd.id_deposito
          {_ap_join()}
          WHERE {_article_filter()} AND {_deposit_filter()}{dep_scope}
          GROUP BY a.IDArt,a.PrecioCosto
        ) x
        """,
        params,
    )
    row = cursor.fetchone() or (0,) * 6
    return dict(zip(
        ("stock_valorizado", "unidades_disponibles", "articulos_con_stock",
         "articulos_stock_negativo", "stock_reservado", "pendiente_recibir"),
        [float(value or 0) for value in row],
    ))


def _limits(cursor, filters: DashboardFilters) -> dict:
    dep_scope, params = _deposit_scope("dep", filters)
    cursor.execute(
        f"""
        SELECT
          COUNT(DISTINCT IF(lim.stock_minimo>0 AND COALESCE(sd.saldo,0)<=lim.stock_minimo,
            CONCAT(lim.id_articulo,'|',lim.id_deposito),NULL)) AS bajo_minimo,
          COUNT(DISTINCT IF(lim.punto_pedido>0 AND COALESCE(sd.saldo,0)<=lim.punto_pedido,
            CONCAT(lim.id_articulo,'|',lim.id_deposito),NULL)) AS punto_pedido,
          COUNT(DISTINCT IF(lim.stock_maximo>0 AND COALESCE(sd.saldo,0)>lim.stock_maximo,
            CONCAT(lim.id_articulo,'|',lim.id_deposito),NULL)) AS sobre_maximo
        FROM (SELECT id_articulo,id_deposito,
          MAX(stock_minimo) AS stock_minimo, MAX(punto_pedido) AS punto_pedido,
          MAX(stock_maximo) AS stock_maximo
          FROM deposito_reposicion GROUP BY id_articulo,id_deposito) lim
        JOIN articulo a ON a.IDArt = lim.id_articulo
        JOIN deposito dep ON dep.CodDeposito = lim.id_deposito
        LEFT JOIN (SELECT id_articulo,id_deposito,SUM(saldo) AS saldo
          FROM stock_deposito GROUP BY id_articulo,id_deposito) sd
          ON sd.id_articulo = lim.id_articulo AND sd.id_deposito = lim.id_deposito
        WHERE {_article_filter()} AND {_deposit_filter()}{dep_scope}
        """,
        params,
    )
    row = cursor.fetchone() or (0, 0, 0)
    return dict(zip(("bajo_minimo", "punto_pedido", "sobre_maximo"), [int(v or 0) for v in row]))


def _movement_filter(filters: DashboardFilters, *, period: bool) -> tuple[str, list]:
    dep_scope, dep_params = _deposit_scope("dep", filters)
    where = (
        "s.Anulado = 'No' AND UPPER(COALESCE(s.tipo_art,'ARTICULO')) "
        "NOT IN ('GASTO','SERVICIO') "
        "AND UPPER(COALESCE(s.Comprobante,'')) NOT IN ('PED','PRE','OC') "
        "AND (COALESCE(s.Entrada,0)<>0 OR COALESCE(s.Salida,0)<>0) "
        "AND UPPER(COALESCE(s.no_entregado_fact,'NO'))<>'SI' "
        f"AND {_deposit_filter()}{dep_scope}"
    )
    params: list = dep_params
    if period:
        where = "s.Fecha >= %s AND s.Fecha < %s AND " + where
        params = [filters.fecha_inicio_str, (filters.fecha_fin + timedelta(days=1)).isoformat()] + params
    return where, params


def _movements(cursor, filters: DashboardFilters, presentation: str) -> dict:
    factor, _ = _factors(presentation=presentation, stock_alias="s")
    where, params = _movement_filter(filters, period=True)
    cursor.execute(
        f"""
        SELECT
          COALESCE(SUM(COALESCE(s.Entrada,0)/({factor})),0) AS entradas,
          COALESCE(SUM(COALESCE(s.Salida,0)/({factor})),0) AS salidas,
          COALESCE(SUM(IF(COALESCE(s.Entrada,0)<>0,
            ABS(COALESCE(s.PrecioCostoxR,COALESCE(s.PrecioCostoxU,0)*s.Entrada)),0)),0) AS valor_entradas,
          COALESCE(SUM(IF(COALESCE(s.Salida,0)<>0,
            ABS(COALESCE(s.PrecioCostoxR,COALESCE(s.PrecioCostoxU,0)*s.Salida)),0)),0) AS valor_salidas
        FROM stock s
        JOIN deposito dep ON dep.CodDeposito = s.CodDeposito
        LEFT JOIN articulo a ON a.IDArt = s.IDArt
        {_ap_join()}
        WHERE {where}
        """,
        params,
    )
    row = cursor.fetchone() or (0, 0, 0, 0)
    return dict(zip(
        ("entradas_periodo", "salidas_periodo", "valor_entradas", "valor_salidas"),
        [float(value or 0) for value in row],
    ))


def _without_movement(cursor, filters: DashboardFilters) -> int:
    dep_scope, dep_params = _deposit_scope("dep", filters)
    movement_where, movement_params = _movement_filter(filters, period=False)
    cursor.execute(
        f"""
        SELECT COUNT(*) AS sin_movimiento_90d FROM (
          SELECT a.IDArt,COALESCE(SUM(sd.saldo),0) AS saldo
          FROM stock_deposito sd
          JOIN articulo a ON a.IDArt = sd.id_articulo
          JOIN deposito dep ON dep.CodDeposito = sd.id_deposito
          WHERE {_article_filter()} AND {_deposit_filter()}{dep_scope}
          GROUP BY a.IDArt
        ) x
        LEFT JOIN (
          SELECT DISTINCT s.IDArt FROM stock s
          JOIN deposito dep ON dep.CodDeposito = s.CodDeposito
          WHERE s.Fecha >= %s AND s.Fecha < %s AND {movement_where}
        ) mov ON mov.IDArt = x.IDArt
        WHERE x.saldo > 0 AND mov.IDArt IS NULL
        """,
        dep_params + [
            (filters.fecha_fin - timedelta(days=89)).isoformat(),
            (filters.fecha_fin + timedelta(days=1)).isoformat(),
        ] + movement_params,
    )
    row = cursor.fetchone()
    return int(row[0] or 0) if row else 0


def _deposit_series(cursor, filters: DashboardFilters) -> list[dict]:
    scope, params = _deposit_scope("dep", filters)
    _, cost_factor = _factors(presentation="unidad")
    cursor.execute(
        f"""
        SELECT dep.CodDeposito,dep.NombreDeposito,
          COALESCE(SUM(IF(sd.saldo>0,sd.saldo*COALESCE(a.PrecioCosto,0)/NULLIF(({cost_factor}),0),0)),0)
          AS valor
        FROM stock_deposito sd
        JOIN articulo a ON a.IDArt = sd.id_articulo
        JOIN deposito dep ON dep.CodDeposito = sd.id_deposito
        {_ap_join()}
        WHERE {_article_filter()} AND {_deposit_filter()}{scope}
        GROUP BY dep.CodDeposito,dep.NombreDeposito
        ORDER BY valor DESC LIMIT 8
        """,
        params,
    )
    return [
        {"id_deposito": int(dep), "nombre": str(name), "valor": round_money(amount)}
        for dep, name, amount in cursor.fetchall() or []
    ]


def _movement_series(cursor, filters: DashboardFilters, presentation: str) -> dict:
    days = (filters.fecha_fin - filters.fecha_inicio).days + 1
    if days <= 45:
        bucket = "dia"
        expr = "DATE_FORMAT(s.Fecha,'%Y-%m-%d')"
    elif days <= 200:
        bucket = "semana"
        expr = "DATE_FORMAT(DATE_SUB(s.Fecha,INTERVAL WEEKDAY(s.Fecha) DAY),'%Y-%m-%d')"
    else:
        bucket = "mes"
        expr = "DATE_FORMAT(s.Fecha,'%Y-%m-01')"
    factor, _ = _factors(presentation=presentation, stock_alias="s")
    where, params = _movement_filter(filters, period=True)
    cursor.execute(
        f"""SELECT {expr} AS fecha,
          COALESCE(SUM(COALESCE(s.Entrada,0)/({factor})),0) AS entradas,
          COALESCE(SUM(COALESCE(s.Salida,0)/({factor})),0) AS salidas
        FROM stock s
        JOIN deposito dep ON dep.CodDeposito = s.CodDeposito
        LEFT JOIN articulo a ON a.IDArt = s.IDArt
        {_ap_join()}
        WHERE {where}
        GROUP BY {expr} ORDER BY {expr}
        """,
        params,
    )
    return {
        "agrupacion": bucket,
        "filas": [
            {"fecha": str(fecha), "entradas": round(float(entrada or 0), 2),
             "salidas": round(float(salida or 0), 2)}
            for fecha, entrada, salida in cursor.fetchall() or []
        ],
    }


def fetch_stock_v45(
    cursor, filters: DashboardFilters, *, presentation: str = "unidad",
    show_costs: bool = False, compare_previous: bool = False,
) -> dict:
    """Los 14 KPI; la comparación se limita a los flujos, no al snapshot."""
    if presentation not in {"unidad", "display", "bulto"}:
        raise ValueError("Presentación de stock desconocida.")
    values = {
        **_current(cursor, filters, presentation),
        **_limits(cursor, filters),
        **_movements(cursor, filters, presentation),
        "sin_movimiento_90d": _without_movement(cursor, filters),
    }
    for key in ("stock_valorizado", "valor_entradas", "valor_salidas"):
        values[key] = round_money(values[key]) if show_costs else None
    for key in ("unidades_disponibles", "stock_reservado", "pendiente_recibir",
                "entradas_periodo", "salidas_periodo"):
        values[key] = round(values[key], 2)
    for key in ("articulos_con_stock", "articulos_stock_negativo", "bajo_minimo",
                "punto_pedido", "sobre_maximo", "sin_movimiento_90d"):
        values[key] = int(values[key])
    payload = {
        "kpis": values, "presentacion": presentation, "disponible": True,
        "series_depositos": _deposit_series(cursor, filters) if show_costs else None,
        "serie_movimientos": _movement_series(cursor, filters, presentation),
        "meta": build_meta(filters, fuente="modCM_StockDatos.bas/V45",
                           snapshot="existencias actuales; el período se aplica a movimientos"),
    }
    if compare_previous:
        days = (filters.fecha_fin - filters.fecha_inicio).days + 1
        prior = replace(
            filters, fecha_inicio=filters.fecha_inicio - timedelta(days=days),
            fecha_fin=filters.fecha_inicio - timedelta(days=1),
            fecha_referencia=filters.fecha_inicio - timedelta(days=1),
        )
        before = _movements(cursor, prior, presentation)
        payload["serie_movimientos_anterior"] = _movement_series(cursor, prior, presentation)
        if not show_costs:
            before["valor_entradas"] = None
            before["valor_salidas"] = None
        payload["comparacion"] = {
            "periodo": {"inicio": prior.fecha_inicio_str, "fin": prior.fecha_fin_str},
            "kpis": before,
            "diferencias": {
                key: round(values[key] - value, 2) if value is not None else None
                for key, value in before.items()
            },
            "no_comparables": [
                "stock_valorizado", "unidades_disponibles", "articulos_con_stock",
                "articulos_stock_negativo", "bajo_minimo", "punto_pedido", "sobre_maximo",
                "stock_reservado", "pendiente_recibir", "sin_movimiento_90d",
            ],
        }
    return payload
