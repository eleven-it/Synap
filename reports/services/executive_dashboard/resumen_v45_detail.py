"""Aperturas de Resumen gerencial V45 con los predicados de sus KPI."""
from __future__ import annotations

from .base import DashboardFilters, build_paginated_response
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
        sql = (
            "SELECT cc.Fecha fecha,cc.CodigoMovimiento movimiento,"
            "cc.TipoComprobante tipo,cc.NroComprobante comprobante,"
            "COALESCE(c.nombre_cliente,'') entidad,"
            f"{amount} importe FROM cuentacliente cc "
            "LEFT JOIN cliente c ON c.Codigo=cc.Codigo "
            "WHERE cc.Fecha >= %s AND cc.Fecha < %s "
            f"AND cc.CodigoMovimiento<>0 AND cc.Anulado='No' AND {kinds}{scope}"
        )
        return sql, period + scope_params, ("cuentacliente", "cliente")

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
