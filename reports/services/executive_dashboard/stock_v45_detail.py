"""Detalle paginado de los 14 KPI de Abastecimiento/Stock V45."""
from __future__ import annotations

from datetime import timedelta

from .base import DashboardFilters, build_paginated_response
from .stock_v45 import (
    STOCK_V45_KEYS, _ap_join, _article_filter, _deposit_filter,
    _deposit_scope, _factors, _movement_filter,
)


_COST_KEYS = {"stock_valorizado", "valor_entradas", "valor_salidas"}
_LIMIT_KEYS = {"bajo_minimo", "punto_pedido", "sobre_maximo"}
_MOVEMENT_KEYS = {"entradas_periodo", "salidas_periodo", "valor_entradas", "valor_salidas"}
_SORTS = {
    "importe_desc": "d.importe DESC,d.articulo,d.id DESC",
    "importe_asc": "d.importe ASC,d.articulo,d.id",
    "articulo": "d.articulo,d.id",
    "fecha_desc": "d.fecha DESC,d.id DESC",
    "fecha_asc": "d.fecha ASC,d.id",
}


def _current_sql(filters: DashboardFilters, kpi: str, presentation: str) -> tuple[str, list]:
    scope, params = _deposit_scope("dep", filters)
    factor, cost_factor = _factors(presentation=presentation)
    base = f"""
      SELECT a.IDArt AS id,MAX(a.NombreArticulo) AS articulo,
        MAX(COALESCE(a.id_manual,'')) AS codigo_manual,
        CAST(a.IDArt AS CHAR) AS codigo_sistema,
        GROUP_CONCAT(DISTINCT dep.NombreDeposito ORDER BY dep.NombreDeposito SEPARATOR ', ') AS deposito,
        SUM(sd.saldo) AS saldo,
        SUM(COALESCE(sd.saldo_pedido_cliente,0)) AS reservado,
        SUM(COALESCE(sd.saldo_pedido_proveedor,0)) AS pendiente,
        MAX({factor}) AS factor,
        MAX(COALESCE(a.PrecioCosto,0))/NULLIF(MAX({cost_factor}),0) AS costo_base
      FROM stock_deposito sd
      JOIN articulo a ON a.IDArt=sd.id_articulo
      JOIN deposito dep ON dep.CodDeposito=sd.id_deposito
      {_ap_join()}
      WHERE {_article_filter()} AND {_deposit_filter()}{scope}
      GROUP BY a.IDArt
    """
    conditions = {
        "stock_valorizado": ("x.saldo>0", "x.saldo*x.costo_base"),
        "unidades_disponibles": ("x.saldo>0", "x.saldo/x.factor"),
        "articulos_con_stock": ("x.saldo>0", "1"),
        "articulos_stock_negativo": ("x.saldo<0", "1"),
        "stock_reservado": ("x.reservado>0", "x.reservado/x.factor"),
        "pendiente_recibir": ("x.pendiente>0", "x.pendiente/x.factor"),
        "sin_movimiento_90d": ("x.saldo>0 AND mov.IDArt IS NULL", "1"),
    }
    condition, metric = conditions[kpi]
    movement_join = ""
    if kpi == "sin_movimiento_90d":
        movement_where, movement_params = _movement_filter(filters, period=False)
        movement_join = f"""
          LEFT JOIN (SELECT DISTINCT s.IDArt FROM stock s
            JOIN deposito dep ON dep.CodDeposito=s.CodDeposito
            WHERE s.Fecha >= %s AND s.Fecha < %s AND {movement_where}
          ) mov ON mov.IDArt=x.id
        """
        params += [
            (filters.fecha_fin - timedelta(days=89)).isoformat(),
            (filters.fecha_fin + timedelta(days=1)).isoformat(),
        ] + movement_params
    return f"""
      SELECT x.id,NULL AS fecha,x.articulo,x.codigo_manual,x.codigo_sistema,
        x.deposito,'' AS documento,{metric} AS importe,
        x.saldo/x.factor AS stock_actual,NULL AS stock_minimo,
        NULL AS punto_pedido,NULL AS stock_maximo,
        x.reservado/x.factor AS reservado,x.pendiente/x.factor AS pendiente_recibir
      FROM ({base}) x {movement_join} WHERE {condition}
    """, params


def _limits_sql(filters: DashboardFilters, kpi: str, presentation: str) -> tuple[str, list]:
    scope, params = _deposit_scope("dep", filters)
    factor, _ = _factors(presentation=presentation)
    limits = {
        "bajo_minimo": ("lim.stock_minimo>0 AND COALESCE(sd.saldo,0)<=lim.stock_minimo",
                         "(lim.stock_minimo-COALESCE(sd.saldo,0))/({factor})"),
        "punto_pedido": ("lim.punto_pedido>0 AND COALESCE(sd.saldo,0)<=lim.punto_pedido",
                         "(lim.punto_pedido-COALESCE(sd.saldo,0))/({factor})"),
        "sobre_maximo": ("lim.stock_maximo>0 AND COALESCE(sd.saldo,0)>lim.stock_maximo",
                         "(COALESCE(sd.saldo,0)-lim.stock_maximo)/({factor})"),
    }
    condition, metric = limits[kpi]
    metric = metric.format(factor=factor)
    return f"""
      SELECT CONCAT(lim.id_articulo,'|',lim.id_deposito) AS id,NULL AS fecha,
        a.NombreArticulo AS articulo,COALESCE(a.id_manual,'') AS codigo_manual,
        CAST(a.IDArt AS CHAR) AS codigo_sistema,dep.NombreDeposito AS deposito,
        '' AS documento,{metric} AS importe,
        COALESCE(sd.saldo,0)/({factor}) AS stock_actual,
        lim.stock_minimo/({factor}) AS stock_minimo,
        lim.punto_pedido/({factor}) AS punto_pedido,
        lim.stock_maximo/({factor}) AS stock_maximo,
        COALESCE(sd.reservado,0)/({factor}) AS reservado,
        COALESCE(sd.pendiente,0)/({factor}) AS pendiente_recibir
      FROM (SELECT id_articulo,id_deposito,MAX(stock_minimo) AS stock_minimo,
        MAX(punto_pedido) AS punto_pedido,MAX(stock_maximo) AS stock_maximo
        FROM deposito_reposicion GROUP BY id_articulo,id_deposito) lim
      JOIN articulo a ON a.IDArt=lim.id_articulo
      JOIN deposito dep ON dep.CodDeposito=lim.id_deposito
      LEFT JOIN (SELECT id_articulo,id_deposito,SUM(saldo) AS saldo,
        SUM(saldo_pedido_cliente) AS reservado,
        SUM(saldo_pedido_proveedor) AS pendiente
        FROM stock_deposito GROUP BY id_articulo,id_deposito) sd
        ON sd.id_articulo=lim.id_articulo AND sd.id_deposito=lim.id_deposito
      {_ap_join()}
      WHERE {_article_filter()} AND {_deposit_filter()} AND {condition}{scope}
    """, params


def _movement_sql(filters: DashboardFilters, kpi: str, presentation: str) -> tuple[str, list]:
    where, params = _movement_filter(filters, period=True)
    factor, _ = _factors(presentation=presentation, stock_alias="s")
    metrics = {
        "entradas_periodo": f"COALESCE(s.Entrada,0)/({factor})",
        "salidas_periodo": f"COALESCE(s.Salida,0)/({factor})",
        "valor_entradas": "ABS(COALESCE(s.PrecioCostoxR,COALESCE(s.PrecioCostoxU,0)*s.Entrada))",
        "valor_salidas": "ABS(COALESCE(s.PrecioCostoxR,COALESCE(s.PrecioCostoxU,0)*s.Salida))",
    }
    direction = "Entrada" if kpi in {"entradas_periodo", "valor_entradas"} else "Salida"
    return f"""
      SELECT s.id_stock AS id,DATE(s.Fecha) AS fecha,
        COALESCE(a.NombreArticulo,'Sin artículo') AS articulo,
        COALESCE(a.id_manual,'') AS codigo_manual,
        CAST(a.IDArt AS CHAR) AS codigo_sistema,dep.NombreDeposito AS deposito,
        CONCAT(COALESCE(s.Comprobante,''),' ',COALESCE(s.NroComprobante,'')) AS documento,
        {metrics[kpi]} AS importe,NULL AS stock_actual,NULL AS stock_minimo,
        NULL AS punto_pedido,NULL AS stock_maximo,NULL AS reservado,
        NULL AS pendiente_recibir
      FROM stock s
      JOIN deposito dep ON dep.CodDeposito=s.CodDeposito
      LEFT JOIN articulo a ON a.IDArt=s.IDArt
      {_ap_join()}
      WHERE {where} AND COALESCE(s.{direction},0)<>0
    """, params


def list_stock_v45_detail(
    cursor, filters: DashboardFilters, *, kpi: str, presentation: str = "unidad",
    allow_cost: bool = False, order: str = "fecha_desc",
) -> dict:
    if kpi not in STOCK_V45_KEYS or presentation not in {"unidad", "display", "bulto"}:
        raise ValueError("Indicador o presentación desconocida.")
    if kpi in _COST_KEYS and not allow_cost:
        raise PermissionError("Sin permiso de costos.")
    if kpi in _LIMIT_KEYS:
        source, params = _limits_sql(filters, kpi, presentation)
    elif kpi in _MOVEMENT_KEYS:
        source, params = _movement_sql(filters, kpi, presentation)
    else:
        source, params = _current_sql(filters, kpi, presentation)
    search = ""
    if filters.busqueda:
        search = " WHERE (d.articulo LIKE %s OR d.codigo_manual LIKE %s OR d.codigo_sistema LIKE %s OR d.documento LIKE %s)"
        term = f"%{filters.busqueda}%"
        params += [term] * 4
    cursor.execute(f"SELECT COUNT(*),COALESCE(SUM(d.importe),0) FROM ({source}) d{search}", params)
    total_row = cursor.fetchone() or (0, 0)
    sort = _SORTS.get(order, _SORTS["fecha_desc"])
    if kpi not in _MOVEMENT_KEYS and order in {"fecha_desc", "fecha_asc"}:
        sort = _SORTS["articulo"]
    cursor.execute(
        f"SELECT d.* FROM ({source}) d{search} ORDER BY {sort} LIMIT %s OFFSET %s",
        params + [filters.limit, filters.offset],
    )
    columns = [column[0] for column in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall() or []]
    for row in rows:
        for field in ("importe", "stock_actual", "stock_minimo", "punto_pedido",
                      "stock_maximo", "reservado", "pendiente_recibir"):
            if row[field] is not None:
                row[field] = round(float(row[field]), 2)
        if row["fecha"] is not None:
            row["fecha"] = row["fecha"].isoformat() if hasattr(row["fecha"], "isoformat") else str(row["fecha"])
    payload = build_paginated_response(
        filters, rows, int(total_row[0] or 0), float(total_row[1] or 0),
        notas_semanticas=["Existencias y límites son foto actual; movimientos usan el período seleccionado."],
    )
    payload.update({"kpi": kpi, "presentacion": presentation, "foto_actual": kpi not in _MOVEMENT_KEYS})
    return payload
