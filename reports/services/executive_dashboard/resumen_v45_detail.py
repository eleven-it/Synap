"""Aperturas de Resumen gerencial V45 con los predicados de sus KPI."""
from __future__ import annotations

from .base import DashboardFilters, build_paginated_response, comparison_filters, round_money
from .comercial_v45 import _scope as _sales_scope
from .resumen_v45 import (
    _CREDIT_TYPES, _DEBIT_TYPES, _INVOICE_TYPES, _period, _purchase_scope,
    _purchase_account_source, _sales_account_source, _sales_amount, _table_exists,
)


RESUMEN_V45_DETAIL_KEYS = frozenset({
    "ventas", "compras_netas", "cobranzas", "pagos",
    "presupuestos", "pedidos", "facturas", "remitos",
    "vencimiento_cobrar", "vencimiento_pagar",
    "efectivo_actual", "tarjetas_actual", "cheques_actual", "bancos_actual",
    "venta_cuenta_corriente", "compra_cuenta_corriente",
})
COUNT_KEYS = frozenset({"presupuestos", "pedidos", "facturas", "remitos"})
GLOBAL_KEYS = frozenset({
    "vencimiento_cobrar", "vencimiento_pagar",
    "efectivo_actual", "tarjetas_actual", "cheques_actual", "bancos_actual",
})
RANKING_DIMENSIONS = frozenset({"entidad", "vendedor", "marca"})


def _source(filters: DashboardFilters, key: str, gross: bool, *, has_rv: bool = False):
    period = _period(filters)
    if key in {"venta_cuenta_corriente", "compra_cuenta_corriente"}:
        sales = key == "venta_cuenta_corriente"
        core, params = (
            _sales_account_source(filters, gross=gross, has_rv=has_rv)
            if sales else _purchase_account_source(filters)
        )
        entity = "cliente" if sales else "proveedor"
        name = "nombre_cliente" if sales else "Nombre"
        sql = (
            "SELECT q.fecha,q.movimiento,q.tipo,q.comprobante,"
            f"COALESCE(c.{name},'') entidad,q.importe FROM ({core}) q "
            f"LEFT JOIN {entity} c ON c.Codigo=q.codigo_entidad "
            "WHERE q.importe<>0"
        )
        return sql, params, ("cuentacliente", "cliente") if sales else ("cuentaproveedor", "proveedor")
    if key in {"ventas", "cobranzas", "facturas"}:
        scope, scope_params = _sales_scope("cc", filters)
        if key == "ventas":
            amount = _sales_amount(gross)
            kinds = f"cc.TipoComprobante IN ({_CREDIT_TYPES},{_DEBIT_TYPES})"
        elif key == "cobranzas":
            amount = (
                "CASE WHEN cc.TipoComprobante='REC' THEN COALESCE(cc.ImporteCobro,0) "
                "ELSE COALESCE(cc.ImporteVenta,0) END"
            )
            kinds = (
                "(cc.TipoComprobante='REC' OR "
                f"cc.TipoComprobante IN ({_INVOICE_TYPES})) "
                "AND cc.CondVenta IN ('Contado','-')"
            )
        else:
            amount = "1"
            kinds = f"cc.TipoComprobante IN ({_INVOICE_TYPES})"
        sale_columns = (
            "COALESCE(c.CUIT,'') cuit,cc.CondVenta condicion_venta,"
            "COALESCE(v.Nombre,'') vendedor,cc.CodSucursal sucursal,"
            "cc.id_pv punto_venta,"
            f"{_sales_amount(False)} importe_neto,"
            f"{_sales_amount(True)} importe_final,"
            if key == "ventas" else ""
        )
        seller_join = "LEFT JOIN viajantes v ON v.CodViajante=cc.CodViajante " if key == "ventas" else ""
        sql = (
            "SELECT cc.Fecha fecha,cc.CodigoMovimiento movimiento,"
            "cc.TipoComprobante tipo,cc.NroComprobante comprobante,"
            "COALESCE(c.nombre_cliente,'') entidad,"
            f"{sale_columns}{amount} importe FROM cuentacliente cc "
            "LEFT JOIN cliente c ON c.Codigo=cc.Codigo "
            f"{seller_join}"
            "WHERE cc.Fecha >= %s AND cc.Fecha < %s "
            f"AND cc.CodigoMovimiento<>0 AND cc.Anulado='No' AND {kinds}{scope}"
        )
        required = ("cuentacliente", "cliente", "viajantes") if key == "ventas" else ("cuentacliente", "cliente")
        return sql, period + scope_params, required

    if key in {"compras_netas", "pagos"}:
        scope, scope_params = _purchase_scope("cp", filters)
        if key == "compras_netas":
            kinds = "cp.TipoComprobante IN ('FA','FB','FC','FE','FM','NC','ND')"
            amount = (
                "CASE WHEN cp.TipoComprobante='NC' THEN -COALESCE(cp.SubtotalDesc,0) "
                "ELSE COALESCE(cp.SubtotalDesc,0) END"
            )
        else:
            kinds = "cp.TipoComprobante='OP' AND cp.CondCompra IN ('Contado','-')"
            amount = "COALESCE(cp.ImportePago,0)"
        sql = (
            "SELECT cp.Fecha fecha,cp.CodigoMovimiento movimiento,"
            "cp.TipoComprobante tipo,cp.NroComprobante comprobante,"
            "COALESCE(p.Nombre,'') entidad,"
            f"{amount} importe FROM cuentaproveedor cp "
            "LEFT JOIN proveedor p ON p.Codigo=cp.Codigo "
            "WHERE cp.Fecha >= %s AND cp.Fecha < %s "
            f"AND cp.CodigoMovimiento<>0 AND cp.Anulado='No' AND {kinds}{scope}"
        )
        return sql, period + scope_params, ("cuentaproveedor", "proveedor")

    if key in {"presupuestos", "pedidos", "remitos"}:
        scope, scope_params = _sales_scope("cp", filters)
        kind = {"presupuestos": "PRE", "pedidos": "PED", "remitos": "REM"}[key]
        sql = (
            "SELECT cp.Fecha fecha,cp.CodigoMovimiento movimiento,"
            "cp.TipoComprobante tipo,cp.NroComprobante comprobante,"
            "COALESCE(c.nombre_cliente,'') entidad,1 importe FROM comp_ped cp "
            "LEFT JOIN cliente c ON c.Codigo=cp.Codigo "
            "WHERE cp.Fecha >= %s AND cp.Fecha < %s "
            f"AND cp.CodigoMovimiento<>0 AND cp.Anulado='No' AND cp.TipoComprobante='{kind}'{scope}"
        )
        return sql, period + scope_params, ("comp_ped", "cliente")

    if key in {"vencimiento_cobrar", "vencimiento_pagar"}:
        if key == "vencimiento_cobrar":
            table, alias, client_table, client_name = "recibo_factura", "rf", "cliente", "nombre_cliente"
            kinds = f"{_INVOICE_TYPES},'NDA','NDB','NDC','NDE','NDM'"
        else:
            table, alias, client_table, client_name = "op_factura", "of", "proveedor", "Nombre"
            kinds = "'FA','FB','FC','FM','ND'"
        sql = (
            f"SELECT {alias}.Vencimiento fecha,{alias}.CodigoMovimiento movimiento,"
            f"{alias}.TipoComprobante tipo,{alias}.NroComprobante comprobante,"
            f"COALESCE(c.{client_name},'') entidad,COALESCE({alias}.Saldo,0) importe "
            f"FROM {table} {alias} LEFT JOIN {client_table} c ON c.Codigo={alias}.Codigo "
            f"WHERE {alias}.Vencimiento >= %s AND {alias}.Vencimiento < %s "
            f"AND {alias}.TipoComprobante IN ({kinds}) "
            f"AND {alias}.Anulado='No' AND {alias}.Estado='N/Canc'"
        )
        return sql, period, (table, client_table)

    if key in {"efectivo_actual", "tarjetas_actual", "cheques_actual"}:
        kind = {
            "efectivo_actual": "ACUMULATIVA",
            "tarjetas_actual": "TARJETA",
            "cheques_actual": "CHEQUE",
        }[key]
        sql = (
            "SELECT NULL fecha,cs.id_caja_saldo movimiento,ca.tipo_caja tipo,"
            "CAST(cs.id_caja AS CHAR) comprobante,COALESCE(ca.nombre_caja,'') entidad,"
            "COALESCE(cs.saldo,0) importe FROM caja_saldo cs "
            "JOIN caja_abm ca ON ca.id_caja=cs.id_caja "
            "WHERE ca.anulado='No' AND UPPER(COALESCE(cs.moneda,'PESOS'))='PESOS' "
            f"AND UPPER(ca.tipo_caja)='{kind}'"
        )
        return sql, [], ("caja_saldo", "caja_abm")

    sql = (
        "SELECT NULL fecha,cb.CodCuenta movimiento,cb.TipoCuenta tipo,"
        "cb.NroCuenta comprobante,CAST(cb.CodBanco AS CHAR) entidad,"
        "COALESCE(cb.saldo,0) importe FROM cuenta_banco cb "
        "WHERE cb.anulado='No' AND UPPER(COALESCE(cb.moneda,'PESOS'))='PESOS'"
    )
    return sql, [], ("cuenta_banco",)


def list_resumen_v45_detail(
    cursor, filters: DashboardFilters, *, key: str, gross: bool = False,
) -> dict:
    if key not in RESUMEN_V45_DETAIL_KEYS:
        raise ValueError("Indicador de resumen inválido")
    if key in GLOBAL_KEYS and (filters.puntos_venta or filters.sucursales_filtro):
        return {
            "disponible": False, "motivo": "sin_alcance_territorial",
            "filas": [], "indicador": key,
        }
    source, params, required = _source(
        filters, key, gross,
        has_rv=_table_exists(cursor, "resumen_venta_cv")
        if key == "venta_cuenta_corriente" else False,
    )
    missing = [table for table in required if not _table_exists(cursor, table)]
    if missing:
        return {
            "disponible": False, "motivo": "tablas_faltantes",
            "tablas_faltantes": missing, "filas": [], "indicador": key,
        }
    search = ""
    if filters.busqueda:
        search = " WHERE (q.entidad LIKE %s OR CAST(q.comprobante AS CHAR) LIKE %s)"
        params += [f"%{filters.busqueda}%"] * 2
    cursor.execute(
        f"SELECT COUNT(*),COALESCE(SUM(q.importe),0) FROM ({source}) q{search}",
        params,
    )
    count, amount = cursor.fetchone() or (0, 0)
    order = "q.movimiento DESC" if key in GLOBAL_KEYS else "q.fecha DESC,q.movimiento DESC"
    cursor.execute(
        f"SELECT * FROM ({source}) q{search} ORDER BY {order} LIMIT %s OFFSET %s",
        params + [filters.limit, filters.offset],
    )
    columns = [field[0] for field in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall() or []]
    payload = build_paginated_response(
        filters, rows, int(count or 0), None if key in COUNT_KEYS else amount,
    )
    payload["indicador"] = key
    payload["meta"]["alcance"] = (
        "Saldo actual sin filtro territorial" if key in GLOBAL_KEYS
        else "Período seleccionado"
    )
    return payload


def _ranking_source(cursor, filters: DashboardFilters, key: str, gross: bool,
                    dimension: str):
    """Agrupa documentos del KPI; ventas por marca usa renglones y se declara aparte."""
    if dimension == "vendedor":
        if key != "ventas":
            raise ValueError("Vendedor sólo corresponde a ventas")
        scope, scope_params = _sales_scope("cc", filters)
        return (
            "SELECT COALESCE(NULLIF(v.Nombre,''),'Sin vendedor') etiqueta,"
            f"{_sales_amount(gross)} importe,1 cantidad "
            "FROM cuentacliente cc LEFT JOIN viajantes v ON v.CodViajante=cc.CodViajante "
            "WHERE cc.Fecha >= %s AND cc.Fecha < %s AND cc.CodigoMovimiento<>0 "
            "AND cc.Anulado='No' "
            f"AND cc.TipoComprobante IN ({_CREDIT_TYPES},{_DEBIT_TYPES}){scope}",
            _period(filters) + scope_params, ("cuentacliente", "viajantes"),
            "Mismo importe de cabecera que Ventas netas.",
        )
    if dimension == "marca":
        if key != "ventas":
            raise ValueError("Marca sólo corresponde a ventas")
        scope, scope_params = _sales_scope("cc", filters)
        line = (
            "COALESCE(st.PrecioNetoxR,0)+COALESCE(st.PrecioIVAxR,0)+"
            "COALESCE(st.ImpIB,0)+COALESCE(st.impuesto_interno_subtotal,0)"
            if gross else "COALESCE(st.PrecioNetoxR,0)"
        )
        return (
            "SELECT COALESCE(NULLIF(m.NombreMarca,''),'Sin marca') etiqueta,"
            f"CASE WHEN cc.TipoComprobante IN ({_CREDIT_TYPES}) "
            f"THEN -({line}) ELSE ({line}) END importe,"
            f"CASE WHEN cc.TipoComprobante IN ({_CREDIT_TYPES}) "
            "THEN -COALESCE(st.Cantidad,0) ELSE COALESCE(st.Cantidad,0) END cantidad "
            "FROM stock st JOIN cuentacliente cc ON cc.CodigoMovimiento=st.CodigoMovimiento "
            "JOIN articulo a ON a.IDArt=st.IDArt "
            "LEFT JOIN marca m ON m.CodMarca=a.CodigoMarca "
            "WHERE cc.Fecha >= %s AND cc.Fecha < %s AND cc.CodigoMovimiento<>0 "
            "AND cc.Anulado='No' AND st.Anulado='No' "
            "AND COALESCE(st.visualiza_ensamble,'No')='No' "
            "AND st.TipoComp IN ('Venta','Venta TPV','Devol - Cliente','ND Anul NC') "
            f"AND cc.TipoComprobante IN ({_CREDIT_TYPES},{_DEBIT_TYPES}){scope}",
            _period(filters) + scope_params,
            ("stock", "cuentacliente", "articulo", "marca"),
            "Importes por renglón de stock; ajustes de cabecera sin artículo pueden diferir del KPI.",
        )
    source, params, required = _source(
        filters, key, gross,
        has_rv=_table_exists(cursor, "resumen_venta_cv")
        if key == "venta_cuenta_corriente" else False,
    )
    return (f"SELECT COALESCE(NULLIF(q.entidad,''),'Sin especificar') etiqueta,"
            "q.importe importe,1 cantidad FROM (" + source + ") q",
            params, required, "Agrupado por entidad del documento.")


def list_resumen_v45_ranking(cursor, filters: DashboardFilters, *, key: str,
                            dimension: str = "entidad", gross: bool = False,
                            compare: bool = False) -> dict:
    """Ranking y comparación de períodos para la apertura visual de cada KPI."""
    if key not in RESUMEN_V45_DETAIL_KEYS or dimension not in RANKING_DIMENSIONS:
        raise ValueError("Indicador o agrupación inválida")
    if dimension in {"vendedor", "marca"} and key != "ventas":
        raise ValueError("Agrupación no disponible para este indicador")
    if key in GLOBAL_KEYS and (filters.puntos_venta or filters.sucursales_filtro):
        return {"disponible": False, "motivo": "sin_alcance_territorial", "filas": []}
    if compare and key in GLOBAL_KEYS:
        return {"disponible": False, "motivo": "saldo_sin_periodo", "filas": []}

    def grouped(period_filters):
        source, params, required, note = _ranking_source(
            cursor, period_filters, key, gross, dimension,
        )
        missing = [table for table in required if not _table_exists(cursor, table)]
        if missing:
            return None, note, missing, 0, 0
        search = ""
        if filters.busqueda:
            search = " WHERE r.etiqueta LIKE %s"
            params = params + [f"%{filters.busqueda}%"]
        cursor.execute(
            f"SELECT COALESCE(SUM(r.importe),0),COALESCE(SUM(r.cantidad),0) "
            f"FROM ({source}) r{search}", params,
        )
        amount, quantity = cursor.fetchone() or (0, 0)
        cursor.execute(
            f"SELECT r.etiqueta,SUM(r.importe) importe,SUM(r.cantidad) cantidad "
            f"FROM ({source}) r{search} GROUP BY r.etiqueta "
            "ORDER BY ABS(SUM(r.importe)) DESC,r.etiqueta LIMIT 500",
            params,
        )
        return ([dict(zip((field[0] for field in cursor.description), row))
                for row in cursor.fetchall() or []], note, [],
                round_money(amount), float(quantity or 0))

    current, note, missing, current_total, current_qty = grouped(filters)
    if missing:
        return {"disponible": False, "motivo": "tablas_faltantes",
                "tablas_faltantes": missing, "filas": []}
    prior = []
    previous_filters = comparison_filters(filters) if compare else None
    previous_total = 0
    if previous_filters:
        prior, _, missing, previous_total, _ = grouped(previous_filters)
        if missing:
            return {"disponible": False, "motivo": "tablas_faltantes",
                    "tablas_faltantes": missing, "filas": []}
    by_previous = {row["etiqueta"]: row for row in prior}
    by_current = {row["etiqueta"]: row for row in current}
    labels = list(by_current) + [label for label in by_previous if label not in by_current]
    rows = []
    for label in labels:
        actual = float(by_current.get(label, {}).get("importe") or 0)
        previous = float(by_previous.get(label, {}).get("importe") or 0)
        qty = float(by_current.get(label, {}).get("cantidad") or 0)
        rows.append({"etiqueta": label, "importe": round_money(actual),
                     "cantidad": qty, "anterior": round_money(previous),
                     "variacion": round_money(actual - previous),
                     "variacion_pct": round((actual - previous) / abs(previous) * 100, 2)
                     if previous else None})
    return {
        "indicador": key, "dimension": dimension, "filas": rows,
        "total_importe": current_total,
        "total_anterior": previous_total,
        "total_cantidad": current_qty,
        "periodo": {"inicio": filters.fecha_inicio_str, "fin": filters.fecha_fin_str},
        "comparacion": ({"inicio": previous_filters.fecha_inicio_str,
                         "fin": previous_filters.fecha_fin_str} if previous_filters else None),
        "nota": note,
        "truncado": len(current) >= 500 or len(prior) >= 500,
    }
