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
RANKING_DIMENSIONS = frozenset({
    "entidad", "vendedor", "marca", "fecha", "tipo", "sucursal",
    "punto_venta", "condicion_venta", "articulo", "proveedor_habitual",
    "rubro", "subrubro", "categoria", "actividad_iibb", "zona",
    "provincia", "departamento", "distrito", "jurisdiccion_iibb", "usuario",
    "medio_cobro", "tipo_entrega",
})
_SALES_KEYS = frozenset({"ventas", "cobranzas", "facturas"})
_PURCHASE_KEYS = frozenset({"compras_netas", "pagos"})
_DOCUMENT_COUNT_KEYS = frozenset({"presupuestos", "pedidos", "remitos"})


def _allowed_dimensions(key: str) -> frozenset[str]:
    if key == "ventas":
        return frozenset({"entidad", "vendedor", "marca", "fecha", "tipo",
                          "sucursal", "punto_venta", "condicion_venta", "articulo",
                          "proveedor_habitual", "rubro", "subrubro", "categoria",
                          "actividad_iibb", "zona", "provincia", "departamento",
                          "distrito", "jurisdiccion_iibb", "usuario",
                          "medio_cobro", "tipo_entrega"})
    if key == "compras_netas":
        return frozenset({"entidad", "fecha", "tipo", "sucursal", "punto_venta",
                          "articulo", "marca", "rubro", "subrubro", "categoria"})
    if key in _SALES_KEYS | _PURCHASE_KEYS | _DOCUMENT_COUNT_KEYS:
        return frozenset({"entidad", "fecha", "tipo", "sucursal", "punto_venta"})
    if key in GLOBAL_KEYS:
        return frozenset({"entidad", "tipo"})
    return frozenset({"entidad", "fecha", "tipo"})


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
            "COALESCE(v.Nombre,'') vendedor,"
            f"{_sales_amount(False)} importe_neto,"
            f"{_sales_amount(True)} importe_final,"
            if key == "ventas" else ""
        )
        seller_join = "LEFT JOIN viajantes v ON v.CodViajante=cc.CodViajante " if key == "ventas" else ""
        sql = (
            "SELECT cc.Fecha fecha,cc.CodigoMovimiento movimiento,"
            "cc.TipoComprobante tipo,cc.NroComprobante comprobante,"
            "COALESCE(c.nombre_cliente,'') entidad,"
            "cc.CodSucursal sucursal,cc.id_pv punto_venta,"
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
            "COALESCE(p.Nombre,'') entidad,cp.CodSucursal sucursal,cp.id_pv punto_venta,"
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
            "COALESCE(c.nombre_cliente,'') entidad,cp.CodSucursal sucursal,"
            "cp.id_pv punto_venta,1 importe FROM comp_ped cp "
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


def _sales_payment_method_source(filters: DashboardFilters, gross: bool):
    scope, scope_params = _sales_scope("cc", filters)
    fields = (
        "total_efectivo", "total_ctacte", "total_tarjeta", "total_cheque",
        "total_transferencia", "total_otro_medio",
    )
    amounts = [f"ABS(COALESCE(rv.{field},0))" for field in fields]
    total = "(" + "+".join(amounts) + ")"
    per_method = "CASE medios.n " + " ".join(
        f"WHEN {index} THEN {amount}" for index, amount in enumerate(amounts, 1)
    ) + " END"
    label = (
        "CASE WHEN " + total + "=0 AND medios.n=1 THEN 'Sin medio informado' "
        "WHEN medios.n=1 THEN 'Efectivo' WHEN medios.n=2 THEN 'Cuenta corriente' "
        "WHEN medios.n=3 THEN 'Tarjeta' WHEN medios.n=4 THEN 'Cheque' "
        "WHEN medios.n=5 THEN 'Transferencia' ELSE 'Otro medio' END"
    )
    summary = ",".join(f"MAX({field}) {field}" for field in fields)
    ratio = f"CASE WHEN {total}=0 THEN CASE WHEN medios.n=1 THEN 1 ELSE 0 END ELSE {per_method}/{total} END"
    return (
        f"SELECT {label} etiqueta,({_sales_amount(gross)})*({ratio}) importe,"
        f"CASE WHEN {per_method}<>0 OR ({total}=0 AND medios.n=1) THEN 1 ELSE 0 END cantidad "
        "FROM cuentacliente cc LEFT JOIN (SELECT codigo_movimiento," + summary +
        " FROM resumen_venta_cv WHERE UPPER(COALESCE(anulado,'NO'))<>'SI' "
        "GROUP BY codigo_movimiento) rv ON rv.codigo_movimiento=cc.CodigoMovimiento "
        "CROSS JOIN (SELECT 1 n UNION ALL SELECT 2 UNION ALL SELECT 3 "
        "UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6) medios "
        "WHERE cc.Fecha >= %s AND cc.Fecha < %s AND cc.CodigoMovimiento<>0 "
        "AND cc.Anulado='No' "
        f"AND cc.TipoComprobante IN ({_CREDIT_TYPES},{_DEBIT_TYPES}){scope}",
        _period(filters) + scope_params, ("cuentacliente", "resumen_venta_cv"),
        "El importe se distribuye proporcionalmente entre los medios informados.",
    )


def _sales_delivery_source(filters: DashboardFilters, gross: bool):
    scope, scope_params = _sales_scope("cc", filters)
    label = (
        "COALESCE(NULLIF(TRIM(cd.FormaEntrega),''),"
        "NULLIF(TRIM(cp.FormaEntrega),''),'Sin tipo de entrega')"
    )
    orders = (
        "(SELECT CodigoMovimiento,MAX(FormaEntrega) FormaEntrega FROM comp_ped "
        "WHERE UPPER(COALESCE(Anulado,'NO'))<>'SI' GROUP BY CodigoMovimiento)"
    )
    return (
        f"SELECT {label} etiqueta,{_sales_amount(gross)} importe,1 cantidad "
        "FROM cuentacliente cc LEFT JOIN " + orders +
        " cd ON cd.CodigoMovimiento=cc.CodigoMovimiento "
        "LEFT JOIN (SELECT CodigoMovimientoF,MAX(CodigoMovimientoP) CodigoMovimientoP "
        "FROM ped_fact WHERE UPPER(COALESCE(Anulado,'NO'))<>'SI' "
        "GROUP BY CodigoMovimientoF) pf ON pf.CodigoMovimientoF=cc.CodigoMovimiento "
        "LEFT JOIN " + orders + " cp ON cp.CodigoMovimiento=pf.CodigoMovimientoP "
        "WHERE cc.Fecha >= %s AND cc.Fecha < %s AND cc.CodigoMovimiento<>0 "
        "AND cc.Anulado='No' "
        f"AND cc.TipoComprobante IN ({_CREDIT_TYPES},{_DEBIT_TYPES}){scope}",
        _period(filters) + scope_params, ("cuentacliente", "comp_ped", "ped_fact"),
        "Forma de entrega del comprobante o del pedido relacionado.",
    )


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
    if key == "ventas" and dimension == "medio_cobro":
        return _sales_payment_method_source(filters, gross)
    if key == "ventas" and dimension == "tipo_entrega":
        return _sales_delivery_source(filters, gross)
    product_dimensions = {
        "marca": ("LEFT JOIN marca m ON m.CodMarca=a.CodigoMarca ",
                  "m.NombreMarca", ("marca",), "Sin marca"),
        "articulo": ("", "a.NombreArticulo", (), "Sin artículo"),
        "proveedor_habitual": ("LEFT JOIN proveedor p ON p.Codigo=a.CodigoProveedor ",
                               "p.Nombre", ("proveedor",), "Sin proveedor"),
        "rubro": ("LEFT JOIN rubro r ON r.CodigoRubro=a.CodigoRubro ",
                  "r.NombreRubro", ("rubro",), "Sin rubro"),
        "subrubro": ("LEFT JOIN subrubro sr ON sr.IDSubRubro=a.IDSubRubro ",
                     "sr.NombreSubRubro", ("subrubro",), "Sin subrubro"),
        "categoria": ("LEFT JOIN rubro r ON r.CodigoRubro=a.CodigoRubro "
                      "LEFT JOIN rubro_categoria rc ON rc.id_categoria=r.id_categoria ",
                      "rc.nombre_categoria", ("rubro", "rubro_categoria"), "Sin categoría"),
        "actividad_iibb": ("LEFT JOIN activ_iibb ai ON ai.ID=a.cod_act_iibb ",
                           "ai.nombre_iibb", ("activ_iibb",), "Sin actividad IIBB"),
    }
    if dimension in product_dimensions and key in {"ventas", "compras_netas"}:
        if key == "compras_netas":
            if dimension not in {"articulo", "marca", "rubro", "subrubro", "categoria"}:
                raise ValueError("Agrupación por producto no disponible para compras")
            scope, scope_params = _purchase_scope("st", filters)
            joins, field, needed, fallback = product_dimensions[dimension]
            label = f"COALESCE(NULLIF(TRIM({field}),''),'{fallback}')"
            amount = (
                "CASE WHEN st.TipoComp IN ('Devol - Proveedor','Anul Compra') "
                "THEN -COALESCE(st.PrecioCostoxR,0) ELSE COALESCE(st.PrecioCostoxR,0) END"
            )
            return (
                f"SELECT {label} etiqueta,{amount} importe,"
                "ABS(COALESCE(st.Cantidad,0)) cantidad "
                "FROM stock st JOIN articulo a ON a.IDArt=st.IDArt " + joins +
                "WHERE st.Fecha >= %s AND st.Fecha < %s "
                "AND st.CodigoMovimiento<>0 AND st.Anulado='No' "
                "AND st.TipoComp IN ('Compra','Devol - Proveedor','ND Anul NC',"
                f"'Anul NC Devol','Anul Compra'){scope}",
                _period(filters) + scope_params, ("stock", "articulo") + needed,
                "Importes por renglón de stock a costo; descuentos de cabecera pueden diferir del KPI.",
            )
        scope, scope_params = _sales_scope("cc", filters)
        joins, field, needed, fallback = product_dimensions[dimension]
        label = f"COALESCE(NULLIF(TRIM({field}),''),'{fallback}')"
        line = (
            "COALESCE(st.PrecioNetoxR,0)+COALESCE(st.PrecioIVAxR,0)+"
            "COALESCE(st.ImpIB,0)+COALESCE(st.impuesto_interno_subtotal,0)"
            if gross else "COALESCE(st.PrecioNetoxR,0)"
        )
        return (
            f"SELECT {label} etiqueta,"
            f"CASE WHEN cc.TipoComprobante IN ({_CREDIT_TYPES}) "
            f"THEN -({line}) ELSE ({line}) END importe,"
            "ABS(COALESCE(st.Cantidad,0)) cantidad "
            "FROM stock st JOIN cuentacliente cc ON cc.CodigoMovimiento=st.CodigoMovimiento "
            "JOIN articulo a ON a.IDArt=st.IDArt "
            f"{joins}"
            "WHERE cc.Fecha >= %s AND cc.Fecha < %s AND cc.CodigoMovimiento<>0 "
            "AND cc.Anulado='No' AND st.Anulado='No' "
            "AND COALESCE(st.visualiza_ensamble,'No')='No' "
            "AND st.TipoComp IN ('Venta','Venta TPV','Devol - Cliente','ND Anul NC') "
            f"AND cc.TipoComprobante IN ({_CREDIT_TYPES},{_DEBIT_TYPES}){scope}",
            _period(filters) + scope_params,
            ("stock", "cuentacliente", "articulo") + needed,
            "Importes por renglón de stock; ajustes de cabecera sin artículo pueden diferir del KPI.",
        )
    territory_dimensions = {
        "zona": ("LEFT JOIN cliente c ON c.Codigo=cc.Codigo "
                 "LEFT JOIN erp_zona z ON z.id_zona=c.id_zona ",
                 "z.nombre_zona", ("cliente", "erp_zona"), "Sin zona"),
        "provincia": ("LEFT JOIN cliente c ON c.Codigo=cc.Codigo "
                      "LEFT JOIN provincia p ON p.CodProvincia=c.CodProvincia ",
                      "p.Provincia", ("cliente", "provincia"), "Sin provincia"),
        "departamento": ("LEFT JOIN cliente c ON c.Codigo=cc.Codigo "
                         "LEFT JOIN provincia p ON p.CodProvincia=c.CodProvincia "
                         "LEFT JOIN departamento d ON d.IDDepartamento=c.IDDepartamento ",
                         "CONCAT(COALESCE(NULLIF(p.Provincia,''),'Sin provincia'),' - ',"
                         "COALESCE(NULLIF(d.NombreDepartamento,''),'Sin departamento'))",
                         ("cliente", "provincia", "departamento"), "Sin departamento"),
        "distrito": ("LEFT JOIN cliente c ON c.Codigo=cc.Codigo "
                     "LEFT JOIN provincia p ON p.CodProvincia=c.CodProvincia "
                     "LEFT JOIN departamento d ON d.IDDepartamento=c.IDDepartamento "
                     "LEFT JOIN distrito di ON di.IDDistrito=c.IDDistrito ",
                     "CONCAT(COALESCE(NULLIF(p.Provincia,''),'Sin provincia'),' - ',"
                     "COALESCE(NULLIF(d.NombreDepartamento,''),'Sin departamento'),' - ',"
                     "COALESCE(NULLIF(di.NombreDistrito,''),'Sin distrito'))",
                     ("cliente", "provincia", "departamento", "distrito"), "Sin distrito"),
        "jurisdiccion_iibb": (
            "LEFT JOIN cliente c ON c.Codigo=cc.Codigo "
            "LEFT JOIN provincia p ON p.CodProvincia=c.CodProvincia "
            "LEFT JOIN retencion_juridic_convenio j "
            "ON j.id_juridic_convenio=p.id_juridic_convenio ",
            "COALESCE(NULLIF(TRIM(j.nombre_juridiccion),''),"
            "NULLIF(TRIM(p.Provincia),''),'Sin jurisdicción IIBB')",
            ("cliente", "provincia", "retencion_juridic_convenio"), "Sin jurisdicción IIBB"),
        "usuario": ("LEFT JOIN usuarios u ON u.id_usuario=cc.IdUsuario ",
                    "COALESCE(NULLIF(TRIM(CONCAT(COALESCE(u.nombre_usuario,''),' ',"
                    "COALESCE(u.apellido_usuario,''))),''),"
                    "NULLIF(TRIM(u.cod_usuario),''),'Sin usuario')",
                    ("usuarios",), "Sin usuario"),
    }
    if dimension in territory_dimensions:
        if key != "ventas":
            raise ValueError("Agrupación territorial sólo corresponde a ventas")
        scope, scope_params = _sales_scope("cc", filters)
        joins, field, needed, fallback = territory_dimensions[dimension]
        label = field if dimension in {"departamento", "distrito", "jurisdiccion_iibb", "usuario"} else (
            f"COALESCE(NULLIF(TRIM({field}),''),'{fallback}')"
        )
        return (
            f"SELECT {label} etiqueta,{_sales_amount(gross)} importe,1 cantidad "
            "FROM cuentacliente cc " + joins +
            "WHERE cc.Fecha >= %s AND cc.Fecha < %s AND cc.CodigoMovimiento<>0 "
            "AND cc.Anulado='No' "
            f"AND cc.TipoComprobante IN ({_CREDIT_TYPES},{_DEBIT_TYPES}){scope}",
            _period(filters) + scope_params, ("cuentacliente",) + needed,
            "Mismo importe de cabecera que Ventas netas.",
        )
    source, params, required = _source(
        filters, key, gross,
        has_rv=_table_exists(cursor, "resumen_venta_cv")
        if key == "venta_cuenta_corriente" else False,
    )
    expression = {
        "entidad": "COALESCE(NULLIF(q.entidad,''),'Sin especificar')",
        "fecha": "COALESCE(DATE_FORMAT(q.fecha,'%%d/%%m/%%Y'),'Sin fecha')",
        "tipo": "COALESCE(NULLIF(q.tipo,''),'Sin tipo')",
        "sucursal": "COALESCE(CAST(q.sucursal AS CHAR),'Sin sucursal')",
        "punto_venta": "COALESCE(CAST(q.punto_venta AS CHAR),'Sin punto de venta')",
        "condicion_venta": "COALESCE(NULLIF(q.condicion_venta,''),'Sin condición')",
    }[dimension]
    return (f"SELECT {expression} etiqueta,q.importe importe,1 cantidad "
            "FROM (" + source + ") q",
            params, required, "Agrupado por " + dimension.replace("_", " ") + ".")


def list_resumen_v45_ranking(cursor, filters: DashboardFilters, *, key: str,
                            dimension: str = "entidad", gross: bool = False,
                            compare: bool = False) -> dict:
    """Ranking y comparación de períodos para la apertura visual de cada KPI."""
    if key not in RESUMEN_V45_DETAIL_KEYS or dimension not in RANKING_DIMENSIONS:
        raise ValueError("Indicador o agrupación inválida")
    if dimension not in _allowed_dimensions(key):
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
