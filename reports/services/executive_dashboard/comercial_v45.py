"""Indicadores de Comercial/Ventas del Command Center V45.

Fuente: modCM_ComercialDatos.bas (CMCom_CargarDocumentos,
CMCom_CargarVentasFacturas, CMCom_CargarRentabilidad y
CMCom_CargarPedidosVinculados). Las consultas son de solo lectura.
"""
from __future__ import annotations

from datetime import timedelta

from .base import DashboardFilters, build_meta, build_paginated_response, comparison_filters, round_money


FACTURAS = ("FA", "FB", "FC", "FE", "FM")
CREDITOS = ("NCA", "NCB", "NCC", "NCE", "NCM")
DEBITOS = ("NDA", "NDB", "NDC", "NDE", "NDM")


def _scope(alias: str, filters: DashboardFilters) -> tuple[str, list[int]]:
    parts: list[str] = []
    params: list[int] = []
    if filters.puntos_venta:
        parts.append(f"{alias}.id_pv IN ({','.join(['%s'] * len(filters.puntos_venta))})")
        params.extend(filters.puntos_venta)
    if filters.sucursales_filtro:
        parts.append(f"{alias}.CodSucursal IN ({','.join(['%s'] * len(filters.sucursales_filtro))})")
        params.extend(filters.sucursales_filtro)
    return (" AND " + " AND ".join(parts) if parts else ""), params


def _period(filters: DashboardFilters) -> list[str]:
    return [filters.fecha_inicio_str, (filters.fecha_fin + timedelta(days=1)).isoformat()]


def _as_float(value) -> float:
    return float(value or 0)


def _documents(cursor, filters: DashboardFilters, *, gross: bool) -> dict:
    scope, scope_params = _scope("cp", filters)
    amount = "COALESCE(cp.ImporteVenta, 0)" if gross else "COALESCE(cp.SubtotalDesc, 0)"
    cursor.execute(
        f"""
        SELECT
          SUM(cp.TipoComprobante = 'PRE'),
          SUM(IF(cp.TipoComprobante = 'PRE', {amount}, 0)),
          SUM(cp.TipoComprobante = 'PED'),
          SUM(IF(cp.TipoComprobante = 'PED', {amount}, 0)),
          SUM(cp.TipoComprobante = 'PED' AND UPPER(COALESCE(cp.Estado,'')) = 'PENDIENTE'),
          SUM(IF(cp.TipoComprobante = 'PED' AND UPPER(COALESCE(cp.Estado,'')) = 'PENDIENTE', {amount}, 0)),
          SUM(cp.TipoComprobante = 'REM')
        FROM comp_ped cp
        WHERE cp.Fecha >= %s AND cp.Fecha < %s
          AND cp.CodigoMovimiento <> 0 AND cp.Anulado = 'No'
          AND cp.TipoComprobante IN ('PRE','PED','REM') {scope}
        """,
        _period(filters) + scope_params,
    )
    row = cursor.fetchone() or (0,) * 7
    return dict(zip(
        ("presupuestos", "monto_presupuestos", "pedidos", "monto_pedidos",
         "pedidos_pendientes", "monto_pendientes", "remitos"),
        [_as_float(v) for v in row],
    ))


def _sales(cursor, filters: DashboardFilters, *, gross: bool) -> dict:
    scope, scope_params = _scope("cc", filters)
    debit = "COALESCE(cc.ImporteVenta,0)" if gross else "COALESCE(cc.SubtotalDesc,0)"
    credit = "COALESCE(cc.ImporteCobro,0)" if gross else "COALESCE(cc.SubtotalDesc,0)"
    cursor.execute(
        f"""
        SELECT
          SUM(CASE
              WHEN cc.TipoComprobante IN ('NCA','NCB','NCC','NCE','NCM') THEN -({credit})
              WHEN cc.TipoComprobante IN ('FA','FB','FC','FE','FM','NDA','NDB','NDC','NDE','NDM') THEN {debit}
              ELSE 0 END),
          SUM(cc.TipoComprobante IN ('FA','FB','FC','FE','FM')),
          SUM(IF(cc.TipoComprobante IN ('NCA','NCB','NCC','NCE','NCM'), ABS({credit}), 0)),
          SUM(IF(cc.TipoComprobante IN ('NDA','NDB','NDC','NDE','NDM'), ABS({debit}), 0))
        FROM cuentacliente cc
        WHERE cc.Fecha >= %s AND cc.Fecha < %s
          AND cc.CodigoMovimiento <> 0 AND cc.Anulado = 'No' {scope}
        """,
        _period(filters) + scope_params,
    )
    row = cursor.fetchone() or (0,) * 4
    return dict(zip(
        ("ventas_netas", "facturas", "creditos_devoluciones", "notas_debito"),
        [_as_float(v) for v in row],
    ))


def _stock_scope(filters: DashboardFilters) -> tuple[str, list[int]]:
    """Un renglón de stock se autoriza por su comprobante origen, sin ampliar PV."""
    if not filters.puntos_venta and not filters.sucursales_filtro:
        return "", []
    cc_scope, cc_params = _scope("origin", filters)
    return (
        " AND EXISTS (SELECT 1 FROM cuentacliente origin "
        "WHERE origin.CodigoMovimiento = s.CodigoMovimiento "
        f"AND origin.CodigoMovimiento <> 0 {cc_scope})",
        cc_params,
    )


def _profit(cursor, filters: DashboardFilters, *, gross: bool) -> dict:
    scope, scope_params = _stock_scope(filters)
    if gross:
        sales = (
            "COALESCE(s.PrecioNetoxR,0)+COALESCE(s.PrecioIVAxR,0)+"
            "COALESCE(s.ImpIB,0)+COALESCE(s.impuesto_interno_subtotal,0)"
        )
        cost = (
            "COALESCE(s.PrecioCostoxR,0)*(1+(COALESCE((SELECT MAX(iv.Alicuota) "
            "FROM iva iv WHERE iv.ID=CAST(COALESCE(s.Alicuota,0) AS UNSIGNED)),0)/100))"
        )
    else:
        sales = "COALESCE(s.PrecioNetoxR,0)"
        cost = "COALESCE(s.PrecioCostoxR,0)"
    cursor.execute(
        f"""
        SELECT
          SUM(IF(s.TipoComp IN ('Venta','Venta TPV','ND Anul NC'),
                 ({sales}), -({sales}))),
          SUM(IF(s.TipoComp IN ('Venta','Venta TPV','ND Anul NC'),
                 ({cost}), -({cost})))
        FROM stock s
        WHERE s.Fecha >= %s AND s.Fecha < %s AND s.Anulado = 'No'
          AND COALESCE(s.visualiza_ensamble,'No') = 'No'
          AND s.TipoComp IN ('Venta','Venta TPV','Devol - Cliente','ND Anul NC')
          {scope}
        """,
        _period(filters) + scope_params,
    )
    row = cursor.fetchone() or (0, 0)
    net, cost_total = (_as_float(v) for v in row)
    profit = net - cost_total
    return {
        "venta_base_rentabilidad": net,
        "costo_ventas": cost_total,
        "rentabilidad": profit,
        "margen_porcentaje": profit / net * 100 if abs(net) > 0.0001 else 0.0,
    }


def _linked_orders(cursor, filters: DashboardFilters) -> dict:
    """V45 reemplaza los conteos por Estado con vínculos reales de stock."""
    scope, scope_params = _scope("cp", filters)
    base = f"""
        FROM comp_ped cp
        WHERE cp.Fecha >= %s AND cp.Fecha < %s
          AND cp.TipoComprobante = 'PED' AND cp.CodigoMovimiento <> 0
          AND UPPER(COALESCE(cp.Anulado,'No')) <> 'SI' {scope}
    """
    common = _period(filters) + scope_params
    cursor.execute(
        f"""SELECT COUNT(DISTINCT cp.CodigoMovimiento) {base}
          AND EXISTS (SELECT 1 FROM stock s
            INNER JOIN comp_ped rem ON rem.CodigoMovimiento = s.codmov_remito
            WHERE s.codmov_pedido = cp.CodigoMovimiento
              AND UPPER(COALESCE(s.Anulado,'No')) <> 'SI'
              AND rem.TipoComprobante = 'REM'
              AND UPPER(COALESCE(rem.Anulado,'No')) <> 'SI')""",
        common,
    )
    in_remito = int((cursor.fetchone() or (0,))[0] or 0)
    cursor.execute(
        f"""SELECT COUNT(DISTINCT cp.CodigoMovimiento) {base}
          AND EXISTS (SELECT 1 FROM stock s
            INNER JOIN cuentacliente fac ON fac.CodigoMovimiento = s.CodigoMovimiento
            WHERE s.codmov_pedido = cp.CodigoMovimiento
              AND UPPER(COALESCE(s.Anulado,'No')) <> 'SI'
              AND s.TipoComp IN ('Venta','Venta TPV','ND Anul NC')
              AND UPPER(COALESCE(fac.Anulado,'No')) <> 'SI'
              AND fac.TipoComprobante IN
                ('FA','FB','FC','FE','FM','NDA','NDB','NDC','NDE','NDM'))""",
        common,
    )
    invoiced = int((cursor.fetchone() or (0,))[0] or 0)
    return {"pedidos_en_remito": in_remito, "pedidos_facturados": invoiced}


def _daily_sales(cursor, filters: DashboardFilters, *, gross: bool) -> list[dict]:
    scope, scope_params = _scope("cc", filters)
    day_count = (filters.fecha_fin - filters.fecha_inicio).days + 1
    group_expr = "DATE(cc.Fecha)" if day_count <= 120 else "DATE_FORMAT(cc.Fecha,'%%Y-%%m-01')"
    debit = "COALESCE(cc.ImporteVenta,0)" if gross else "COALESCE(cc.SubtotalDesc,0)"
    credit = "COALESCE(cc.ImporteCobro,0)" if gross else "COALESCE(cc.SubtotalDesc,0)"
    cursor.execute(
        f"""
        SELECT {group_expr}, SUM(CASE
          WHEN cc.TipoComprobante IN ('NCA','NCB','NCC','NCE','NCM') THEN -({credit})
          WHEN cc.TipoComprobante IN ('FA','FB','FC','FE','FM','NDA','NDB','NDC','NDE','NDM') THEN {debit}
          ELSE 0 END)
        FROM cuentacliente cc
        WHERE cc.Fecha >= %s AND cc.Fecha < %s
          AND cc.CodigoMovimiento <> 0 AND cc.Anulado = 'No' {scope}
        GROUP BY {group_expr} ORDER BY {group_expr}
        """,
        _period(filters) + scope_params,
    )
    values = {
        fecha.isoformat() if hasattr(fecha, "isoformat") else str(fecha): round_money(importe)
        for fecha, importe in cursor.fetchall() or []
    }
    series: list[dict] = []
    if day_count <= 120:
        current = filters.fecha_inicio
        while current <= filters.fecha_fin:
            key = current.isoformat()
            series.append({"fecha": key, "valor": values.get(key, 0.0)})
            current += timedelta(days=1)
    else:
        current = filters.fecha_inicio.replace(day=1)
        last_month = filters.fecha_fin.replace(day=1)
        while current <= last_month:
            key = current.isoformat()
            series.append({"fecha": key, "valor": values.get(key, 0.0)})
            current = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
    return series


def _kpis(cursor, filters: DashboardFilters, *, gross: bool, include_profit: bool) -> dict:
    docs = _documents(cursor, filters, gross=gross)
    sales = _sales(cursor, filters, gross=gross)
    links = _linked_orders(cursor, filters)
    count_invoices = int(sales["facturas"])
    values = {
        **docs, **sales, **links,
        "ticket_promedio": sales["ventas_netas"] / count_invoices if count_invoices else 0,
        "rentabilidad": None,
        "margen_porcentaje": None,
    }
    if include_profit:
        values.update(_profit(cursor, filters, gross=gross))
    money_keys = {
        "ventas_netas", "monto_presupuestos", "monto_pedidos", "monto_pendientes",
        "creditos_devoluciones", "notas_debito", "ticket_promedio", "rentabilidad",
        "venta_base_rentabilidad", "costo_ventas",
    }
    for key in money_keys:
        if values.get(key) is not None:
            values[key] = round_money(values[key])
    for key in (
        "presupuestos", "pedidos", "pedidos_pendientes", "remitos",
        "facturas", "pedidos_en_remito", "pedidos_facturados",
    ):
        values[key] = int(values[key])
    if values["margen_porcentaje"] is not None:
        values["margen_porcentaje"] = round(values["margen_porcentaje"], 2)
    return values


def fetch_comercial_ventas_v45(
    cursor, filters: DashboardFilters, *, gross: bool = False,
    include_profit: bool = False, compare_previous: bool = False,
) -> dict:
    """Calcula 16 KPI V45; comparación usa igual cantidad de días previos."""
    values = _kpis(cursor, filters, gross=gross, include_profit=include_profit)
    payload = {
        "kpis": values,
        "incluye_impuestos": gross,
        "disponible": True,
        "meta": build_meta(filters, fuente="modCM_ComercialDatos.bas/V45"),
    }
    if compare_previous:
        days = (filters.fecha_fin - filters.fecha_inicio).days + 1
        previous = comparison_filters(filters)
        before = _kpis(cursor, previous, gross=gross, include_profit=include_profit)
        payload["comparacion"] = {
            "periodo": {"inicio": previous.fecha_inicio_str, "fin": previous.fecha_fin_str},
            "kpis": before,
            "diferencias": {
                key: round((value - before[key]), 2)
                if value is not None and before.get(key) is not None else None
                for key, value in values.items()
                if key in before and isinstance(value, (int, float, type(None)))
            },
        }
        payload["series"] = {
            "agrupacion": "dia" if days <= 120 else "mes",
            "ventas_actual": _daily_sales(cursor, filters, gross=gross),
            "ventas_anterior": _daily_sales(cursor, previous, gross=gross),
        }
    return payload


_CUSTOMER_DOCS = {
    "ventas_netas", "facturas", "creditos_devoluciones", "notas_debito", "ticket_promedio",
}
_ORDER_DOCS = {
    "presupuestos", "monto_presupuestos", "pedidos", "monto_pedidos",
    "pedidos_pendientes", "monto_pendientes", "pedidos_en_remito",
    "pedidos_facturados", "remitos",
}
_PROFIT_DOCS = {"rentabilidad", "margen_porcentaje"}
COMERCIAL_V45_DETAIL_KEYS = _CUSTOMER_DOCS | _ORDER_DOCS | _PROFIT_DOCS


def _detail_expression(kpi: str, *, gross: bool) -> tuple[str, str, str]:
    """Devuelve tabla, condición y expresión monetaria, sin datos del usuario en SQL."""
    if kpi in _CUSTOMER_DOCS:
        debit = "COALESCE(d.ImporteVenta,0)" if gross else "COALESCE(d.SubtotalDesc,0)"
        credit = "COALESCE(d.ImporteCobro,0)" if gross else "COALESCE(d.SubtotalDesc,0)"
        if kpi == "facturas" or kpi == "ticket_promedio":
            return "cuentacliente", "d.TipoComprobante IN ('FA','FB','FC','FE','FM')", debit
        if kpi == "creditos_devoluciones":
            return "cuentacliente", "d.TipoComprobante IN ('NCA','NCB','NCC','NCE','NCM')", f"ABS({credit})"
        if kpi == "notas_debito":
            return "cuentacliente", "d.TipoComprobante IN ('NDA','NDB','NDC','NDE','NDM')", f"ABS({debit})"
        return "cuentacliente", "d.TipoComprobante IN ('FA','FB','FC','FE','FM','NCA','NCB','NCC','NCE','NCM','NDA','NDB','NDC','NDE','NDM')", (
            "CASE WHEN d.TipoComprobante IN ('NCA','NCB','NCC','NCE','NCM') "
            f"THEN -({credit}) ELSE {debit} END"
        )
    if kpi in _ORDER_DOCS:
        amount = "COALESCE(d.ImporteVenta,0)" if gross else "COALESCE(d.SubtotalDesc,0)"
        if kpi in ("presupuestos", "monto_presupuestos"):
            return "comp_ped", "d.TipoComprobante = 'PRE'", amount
        if kpi == "remitos":
            return "comp_ped", "d.TipoComprobante = 'REM'", amount
        if kpi in ("pedidos_pendientes", "monto_pendientes"):
            return "comp_ped", "d.TipoComprobante = 'PED' AND UPPER(COALESCE(d.Estado,'')) = 'PENDIENTE'", amount
        if kpi == "pedidos_en_remito":
            return "comp_ped", """d.TipoComprobante = 'PED' AND EXISTS (
                SELECT 1 FROM stock s JOIN comp_ped rem ON rem.CodigoMovimiento = s.codmov_remito
                WHERE s.codmov_pedido = d.CodigoMovimiento AND rem.TipoComprobante = 'REM'
                  AND UPPER(COALESCE(s.Anulado,'No')) <> 'SI'
                  AND UPPER(COALESCE(rem.Anulado,'No')) <> 'SI')""", amount
        if kpi == "pedidos_facturados":
            return "comp_ped", """d.TipoComprobante = 'PED' AND EXISTS (
                SELECT 1 FROM stock s JOIN cuentacliente fac ON fac.CodigoMovimiento = s.CodigoMovimiento
                WHERE s.codmov_pedido = d.CodigoMovimiento
                  AND UPPER(COALESCE(s.Anulado,'No')) <> 'SI'
                  AND s.TipoComp IN ('Venta','Venta TPV','ND Anul NC')
                  AND UPPER(COALESCE(fac.Anulado,'No')) <> 'SI'
                  AND fac.TipoComprobante IN ('FA','FB','FC','FE','FM','NDA','NDB','NDC','NDE','NDM'))""", amount
        return "comp_ped", "d.TipoComprobante = 'PED'", amount
    raise ValueError("KPI sin detalle de comprobantes.")


def list_comercial_v45_detail(
    cursor, filters: DashboardFilters, *, kpi: str, gross: bool = False,
    allow_cost: bool = False, order: str = "fecha_desc",
) -> dict:
    """Grilla buscable y paginada; conteo y monto salen de idéntico WHERE."""
    if kpi not in COMERCIAL_V45_DETAIL_KEYS:
        raise ValueError("Indicador desconocido.")
    if kpi in _PROFIT_DOCS:
        if not allow_cost:
            raise PermissionError("Sin permiso para consultar costos.")
        return _list_profit_detail(cursor, filters, kpi=kpi, gross=gross, order=order)

    table, condition, amount = _detail_expression(kpi, gross=gross)
    scope, scope_params = _scope("d", filters)
    where = [
        "d.Fecha >= %s", "d.Fecha < %s", "d.CodigoMovimiento <> 0",
        "d.Anulado = 'No'", condition,
    ]
    params: list = _period(filters) + scope_params
    if scope:
        where.append(scope.strip()[4:])  # elimina el prefijo AND; parámetros al final
    if filters.busqueda:
        pattern = "%" + filters.busqueda.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        where.append("(COALESCE(cli.nombre_cliente,'') LIKE %s OR d.NroComprobante LIKE %s OR CAST(d.Codigo AS CHAR) LIKE %s)")
        params.extend([pattern] * 3)
    from_where = f"FROM {table} d LEFT JOIN cliente cli ON cli.Codigo = d.Codigo WHERE " + " AND ".join(where)
    cursor.execute(
        f"SELECT COUNT(*), COALESCE(SUM({amount}),0) {from_where}",
        params,
    )
    aggregate = cursor.fetchone() or (0, 0)
    ordering = {
        "fecha_desc": "d.Fecha DESC, d.CodigoMovimiento DESC",
        "fecha_asc": "d.Fecha ASC, d.CodigoMovimiento ASC",
        "cliente": "cli.nombre_cliente ASC, d.Fecha DESC",
        "importe_desc": "importe DESC, d.CodigoMovimiento DESC",
        "importe_asc": "importe ASC, d.CodigoMovimiento DESC",
    }.get(order, "d.Fecha DESC, d.CodigoMovimiento DESC")
    cursor.execute(
        f"""SELECT d.CodigoMovimiento, DATE_FORMAT(d.Fecha,'%%Y-%%m-%%d'),
            d.TipoComprobante, d.NroComprobante, d.Codigo,
            COALESCE(cli.nombre_cliente,''), {amount} AS importe
          {from_where} ORDER BY {ordering} LIMIT %s OFFSET %s""",
        params + [filters.limit, filters.offset],
    )
    columns = (
        "codigo_movimiento", "fecha", "tipo_comprobante", "numero", "codigo_cliente",
        "cliente", "importe",
    )
    rows = []
    for row in cursor.fetchall() or []:
        item = dict(zip(columns, row))
        item["codigo_movimiento"] = int(item["codigo_movimiento"])
        item["importe"] = round_money(item["importe"])
        rows.append(item)
    result = build_paginated_response(
        filters, rows, int(aggregate[0] or 0), _as_float(aggregate[1]),
        notas_semanticas=["Detalle V45 del indicador " + kpi],
    )
    result["kpi"] = kpi
    result["orden"] = order
    return result


def _list_profit_detail(cursor, filters: DashboardFilters, *, kpi: str, gross: bool, order: str) -> dict:
    scope, scope_params = _stock_scope(filters)
    if gross:
        sale = "COALESCE(s.PrecioNetoxR,0)+COALESCE(s.PrecioIVAxR,0)+COALESCE(s.ImpIB,0)+COALESCE(s.impuesto_interno_subtotal,0)"
        cost = "COALESCE(s.PrecioCostoxR,0)*(1+(COALESCE((SELECT MAX(iv.Alicuota) FROM iva iv WHERE iv.ID=CAST(COALESCE(s.Alicuota,0) AS UNSIGNED)),0)/100))"
    else:
        sale = "COALESCE(s.PrecioNetoxR,0)"
        cost = "COALESCE(s.PrecioCostoxR,0)"
    sign = "IF(s.TipoComp IN ('Venta','Venta TPV','ND Anul NC'),1,-1)"
    net_expr = f"({sign})*({sale})"
    cost_expr = f"({sign})*({cost})"
    profit_expr = f"({net_expr})-({cost_expr})"
    where = """s.Fecha >= %s AND s.Fecha < %s AND s.Anulado = 'No'
        AND COALESCE(s.visualiza_ensamble,'No') = 'No'
        AND s.TipoComp IN ('Venta','Venta TPV','Devol - Cliente','ND Anul NC')"""
    params: list = _period(filters) + scope_params
    where += scope
    if filters.busqueda:
        pattern = "%" + filters.busqueda.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        where += " AND (COALESCE(a.NombreArticulo,'') LIKE %s OR COALESCE(s.CodigoArticulo,'') LIKE %s)"
        params.extend([pattern, pattern])
    from_where = "FROM stock s LEFT JOIN articulo a ON a.IDArt = s.IDArt WHERE " + where
    cursor.execute(
        f"SELECT COUNT(*), COALESCE(SUM({profit_expr}),0) {from_where}", params,
    )
    aggregate = cursor.fetchone() or (0, 0)
    ordering = {
        "fecha_desc": "s.Fecha DESC, s.CodigoMovimiento DESC",
        "fecha_asc": "s.Fecha ASC, s.CodigoMovimiento ASC",
        "cliente": "a.NombreArticulo ASC, s.Fecha DESC",
        "importe_desc": "rentabilidad DESC, s.CodigoMovimiento DESC",
        "importe_asc": "rentabilidad ASC, s.CodigoMovimiento DESC",
    }.get(order, "s.Fecha DESC, s.CodigoMovimiento DESC")
    cursor.execute(
        f"""SELECT s.CodigoMovimiento, DATE_FORMAT(s.Fecha,'%%Y-%%m-%%d'),
            s.TipoComp, s.CodigoArticulo, COALESCE(a.NombreArticulo,''),
            s.Cantidad, {net_expr} AS venta, {cost_expr} AS costo,
            {profit_expr} AS rentabilidad
            {from_where} ORDER BY {ordering} LIMIT %s OFFSET %s""",
        params + [filters.limit, filters.offset],
    )
    columns = (
        "codigo_movimiento", "fecha", "tipo_comprobante", "codigo_articulo",
        "articulo", "cantidad", "venta", "costo", "rentabilidad",
    )
    rows = []
    for row in cursor.fetchall() or []:
        item = dict(zip(columns, row))
        item["codigo_movimiento"] = int(item["codigo_movimiento"])
        for key in ("cantidad", "venta", "costo", "rentabilidad"):
            item[key] = round_money(item[key])
        rows.append(item)
    result = build_paginated_response(
        filters, rows, int(aggregate[0] or 0), _as_float(aggregate[1]),
        notas_semanticas=["Venta, costo y rentabilidad por renglón de stock V45."],
    )
    result["kpi"] = kpi
    result["orden"] = order
    return result
