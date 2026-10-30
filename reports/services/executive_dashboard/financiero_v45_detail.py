"""Documentos, cheques y saldos del Análisis financiero V45."""
from __future__ import annotations

from .base import DashboardFilters, build_paginated_response, round_money
from .comercial_v45 import _scope as _sales_scope
from .compras_v45 import _scope as _purchase_scope
from .financiero_v45 import _dates
from .resumen_v45 import _table_exists
from .resumen_v45_detail import list_resumen_v45_detail


FINANCIERO_V45_VIEWS = frozenset({
    "cobranzas", "pagos", "cartera_cobrar", "cartera_pagar",
    "vencido_cobrar", "vencido_pagar", "cheques_cartera",
    "cheques_emitidos", "cheques_rechazados", "efectivo", "tarjetas", "bancos",
})
FINANCIAL_SNAPSHOT_KEYS = {
    "efectivo": "efectivo_actual", "tarjetas": "tarjetas_actual", "bancos": "bancos_actual",
}
CHEQUE_VIEWS = frozenset({"cheques_cartera", "cheques_emitidos", "cheques_rechazados"})
CHEQUE_GROUPS = {
    "cheques_cartera": frozenset({"entidad", "banco", "fecha", "vencimiento"}),
    "cheques_emitidos": frozenset({"entidad", "banco", "fecha", "vencimiento"}),
    "cheques_rechazados": frozenset({"tipo", "entidad", "banco", "fecha", "vencimiento"}),
}


def _check_source(view: str) -> str:
    """Mismas condiciones de estado que las tarjetas financieras de VB6."""
    tercero = (
        "SELECT DATE_FORMAT(ch.FechaCobro,'%%Y-%%m-%%d') fecha,"
        "ch.ID movimiento,'Tercero' tipo,COALESCE(CAST(ch.NroCheque AS CHAR),'') comprobante,"
        "ch.CodCliente codigo_entidad,"
        "COALESCE(NULLIF(TRIM(c.nombre_cliente),''),NULLIF(TRIM(ch.Librador),''),'Sin cliente') entidad,"
        "COALESCE(NULLIF(TRIM(b.Nombre),''),'Sin banco') banco,"
        "COALESCE(ch.Importe,0) importe "
        "FROM chequetercero ch LEFT JOIN cliente c ON c.Codigo=ch.CodCliente "
        "LEFT JOIN banco b ON b.CodBanco=ch.CodBanco "
        "WHERE UPPER(COALESCE(ch.Anulado,''))='NO'"
    )
    propio = (
        "SELECT DATE_FORMAT(ch.FechaCobro,'%%Y-%%m-%%d') fecha,"
        "ch.ID movimiento,'Propio' tipo,COALESCE(CAST(ch.NroCheque AS CHAR),'') comprobante,"
        "ch.CodProveedor codigo_entidad,COALESCE(NULLIF(TRIM(p.Nombre),''),'Sin proveedor') entidad,"
        "COALESCE(NULLIF(TRIM(b.Nombre),''),'Sin banco') banco,"
        "COALESCE(ch.Importe,0) importe "
        "FROM chequepropio ch LEFT JOIN proveedor p ON p.Codigo=ch.CodProveedor "
        "LEFT JOIN banco b ON b.CodBanco=ch.CodBanco "
        "WHERE UPPER(COALESCE(ch.Anulado,''))='NO'"
    )
    if view == "cheques_cartera":
        return tercero + " AND UPPER(COALESCE(ch.Encartera,''))='SI'"
    if view == "cheques_emitidos":
        return propio + (
            " AND UPPER(COALESCE(ch.pagado,''))='NO'"
            " AND UPPER(COALESCE(ch.rechazado,''))='NO'"
            " AND UPPER(COALESCE(ch.en_nd_proveedor,''))='NO'"
        )
    return (
        tercero + " AND UPPER(COALESCE(ch.Rechazado,''))='SI'"
        " UNION ALL " + propio + " AND UPPER(COALESCE(ch.rechazado,''))='SI'"
    )


def _check_group_expr(group: str) -> str:
    if group == "vencimiento":
        return (
            "CASE WHEN q.fecha IS NULL THEN 'Sin fecha' "
            "WHEN DATEDIFF(%s,q.fecha)<0 THEN 'Por vencer' "
            "WHEN DATEDIFF(%s,q.fecha)<=7 THEN '0–7 días' "
            "WHEN DATEDIFF(%s,q.fecha)<=30 THEN '8–30 días' "
            "WHEN DATEDIFF(%s,q.fecha)<=60 THEN '31–60 días' "
            "ELSE '+60 días' END"
        )
    return {
        "entidad": "q.entidad", "banco": "q.banco", "tipo": "q.tipo",
        "fecha": "COALESCE(q.fecha,'Sin fecha')",
    }[group]


def _check_detail(cursor, filters: DashboardFilters, view: str, *, mode: str, group: str) -> dict:
    if filters.puntos_venta or filters.sucursales_filtro:
        payload = build_paginated_response(filters, [], 0)
        payload.update(vista=view, disponible=False, motivo="sin_alcance_territorial")
        return payload
    tables = ("chequetercero", "cliente", "banco") if view == "cheques_cartera" else (
        ("chequepropio", "proveedor", "banco") if view == "cheques_emitidos" else
        ("chequetercero", "chequepropio", "cliente", "proveedor", "banco")
    )
    if any(not _table_exists(cursor, table) for table in tables):
        payload = build_paginated_response(filters, [], 0)
        payload.update(vista=view, disponible=False)
        return payload
    source = _check_source(view)
    params: list = []
    search = ""
    if filters.busqueda:
        search = (" WHERE (q.entidad LIKE %s OR q.banco LIKE %s "
                  "OR q.comprobante LIKE %s)")
        params = [f"%{filters.busqueda}%"] * 3
    cursor.execute(f"SELECT COUNT(*),COALESCE(SUM(q.importe),0) FROM ({source}) q{search}", params)
    count, amount = cursor.fetchone() or (0, 0)
    if mode == "ranking":
        if group not in CHEQUE_GROUPS[view]:
            raise ValueError("Agrupador de cheques inválido")
        expr = _check_group_expr(group)
        group_params = [filters.fecha_fin_str] * 4 if group == "vencimiento" else []
        cursor.execute(
            f"SELECT {expr} etiqueta,SUM(q.importe) importe,COUNT(*) cantidad "
            f"FROM ({source}) q{search} GROUP BY etiqueta ORDER BY importe DESC,etiqueta LIMIT 500",
            group_params + params,
        )
        rows = [dict(zip(("etiqueta", "importe", "cantidad"), row)) for row in cursor.fetchall() or []]
        payload = {
            "filas": rows, "total_registros": len(rows), "total_importe": round_money(amount),
            "total_cantidad": int(count or 0), "vista": view, "modo": mode,
            "nota": "Saldo actual de cheques; se muestran valores de todos los estados que integran esta tarjeta.",
            "truncado": len(rows) >= 500,
        }
    else:
        cursor.execute(
            f"SELECT * FROM ({source}) q{search} "
            "ORDER BY q.fecha DESC,q.movimiento DESC LIMIT %s OFFSET %s",
            params + [filters.limit, filters.offset],
        )
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall() or []]
        payload = build_paginated_response(filters, rows, int(count or 0), round_money(amount))
        payload["vista"] = view
    payload.setdefault("meta", {})["alcance"] = "Saldo actual de cheques"
    return payload


def _source(filters: DashboardFilters, view: str) -> tuple[str, list, str]:
    if view == "cobranzas":
        scope, scope_params = _sales_scope("cc", filters)
        source = (
            "SELECT DATE_FORMAT(cc.Fecha,'%%Y-%%m-%%d') fecha,"
            "cc.CodigoMovimiento movimiento,cc.TipoComprobante tipo,"
            "COALESCE(cc.NroComprobante,'') comprobante,"
            "cc.Codigo codigo_entidad,COALESCE(c.nombre_cliente,'') entidad,"
            "cc.CodSucursal sucursal,cc.id_pv punto_venta,"
            "CASE WHEN cc.TipoComprobante='REC' THEN COALESCE(cc.ImporteCobro,0) "
            "ELSE COALESCE(cc.ImporteVenta,0) END importe "
            "FROM cuentacliente cc LEFT JOIN cliente c ON c.Codigo=cc.Codigo "
            "WHERE cc.Fecha >= %s AND cc.Fecha < %s "
            "AND cc.CondVenta IN ('Contado','-') "
            "AND cc.TipoComprobante IN ('REC','FA','FB','FC','FE','FM') "
            f"AND cc.CodigoMovimiento<>0 AND cc.Anulado='No'{scope}"
        )
        return source, _dates(filters) + scope_params, "Período seleccionado"
    if view == "pagos":
        scope, scope_params = _purchase_scope("cp", filters)
        source = (
            "SELECT DATE_FORMAT(cp.Fecha,'%%Y-%%m-%%d') fecha,"
            "cp.CodigoMovimiento movimiento,cp.TipoComprobante tipo,"
            "COALESCE(cp.NroComprobante,'') comprobante,"
            "cp.Codigo codigo_entidad,COALESCE(p.Nombre,'') entidad,"
            "cp.CodSucursal sucursal,cp.id_pv punto_venta,"
            "COALESCE(cp.ImportePago,0) importe "
            "FROM cuentaproveedor cp LEFT JOIN proveedor p ON p.Codigo=cp.Codigo "
            "WHERE cp.Fecha >= %s AND cp.Fecha < %s "
            "AND cp.TipoComprobante='OP' AND cp.CondCompra IN ('Contado','-') "
            f"AND cp.CodigoMovimiento<>0 AND cp.Anulado='No'{scope}"
        )
        return source, _dates(filters) + scope_params, "Período seleccionado"

    clients = view.endswith("cobrar")
    due = view.startswith("vencido")
    table = "recibo_factura" if clients else "op_factura"
    alias = "rf" if clients else "ofc"
    origin = "cuentacliente" if clients else "cuentaproveedor"
    scope, scope_params = (_sales_scope if clients else _purchase_scope)("doc", filters)
    territorial = (
        f" AND EXISTS (SELECT 1 FROM {origin} doc "
        f"WHERE doc.CodigoMovimiento={alias}.CodigoMovimiento{scope})"
        if scope else ""
    )
    kinds = (
        "'FA','FB','FC','FE','FM','NDA','NDB','NDC','NDE','NDM'"
        if clients else "'FA','FB','FC','FM','ND'"
    )
    name_table = "cliente" if clients else "proveedor"
    name_field = "nombre_cliente" if clients else "Nombre"
    name_join = (
        f"LEFT JOIN {name_table} e ON e.Codigo="
        f"{alias}.Codigo"
    )
    due_condition = f" AND {alias}.Vencimiento <= %s" if due else ""
    source = (
        f"SELECT DATE_FORMAT({alias}.Fecha,'%%Y-%%m-%%d') fecha,"
        f"DATE_FORMAT({alias}.Vencimiento,'%%Y-%%m-%%d') vencimiento,"
        f"{alias}.CodigoMovimiento movimiento,{alias}.TipoComprobante tipo,"
        f"COALESCE({alias}.NroComprobante,'') comprobante,"
        f"{alias}.Codigo codigo_entidad,COALESCE(e.{name_field},'') entidad,"
        f"COALESCE({alias}.Saldo,0) importe "
        f"FROM {table} {alias} {name_join} "
        f"WHERE {alias}.Vencimiento IS NOT NULL "
        f"AND {alias}.TipoComprobante IN ({kinds}) "
        f"AND {alias}.Anulado='No' AND {alias}.Estado='N/Canc'"
        f"{due_condition}{territorial}"
    )
    return source, ([filters.fecha_fin_str] if due else []) + scope_params, "Cartera abierta actual"


def list_financiero_v45_detail(cursor, filters: DashboardFilters, *, view: str,
                              mode: str = "documentos", group: str = "entidad") -> dict:
    if view not in FINANCIERO_V45_VIEWS:
        raise ValueError("Vista financiera inválida")
    if view in FINANCIAL_SNAPSHOT_KEYS:
        payload = list_resumen_v45_detail(cursor, filters, key=FINANCIAL_SNAPSHOT_KEYS[view])
        payload["vista"] = view
        return payload
    if view in CHEQUE_VIEWS:
        return _check_detail(cursor, filters, view, mode=mode, group=group)
    required = (
        "cuentacliente" if view == "cobranzas" else
        "cuentaproveedor" if view == "pagos" else
        "recibo_factura" if view.endswith("cobrar") else "op_factura"
    )
    if not _table_exists(cursor, required):
        payload = build_paginated_response(filters, [], 0)
        payload["vista"] = view
        payload["disponible"] = False
        return payload
    source, params, scope_label = _source(filters, view)
    search = ""
    if filters.busqueda:
        search = (
            " WHERE (q.entidad LIKE %s OR q.comprobante LIKE %s "
            "OR CAST(q.movimiento AS CHAR) LIKE %s)"
        )
        params += [f"%{filters.busqueda}%"] * 3
    cursor.execute(
        f"SELECT COUNT(*),COALESCE(SUM(q.importe),0) FROM ({source}) q{search}",
        params,
    )
    count, amount = cursor.fetchone() or (0, 0)
    cursor.execute(
        f"SELECT * FROM ({source}) q{search} "
        "ORDER BY q.fecha DESC,q.movimiento DESC LIMIT %s OFFSET %s",
        params + [filters.limit, filters.offset],
    )
    columns = [col[0] for col in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall() or []]
    payload = build_paginated_response(
        filters, rows, int(count or 0), round_money(amount),
        notas_semanticas=(
            ["La cartera abierta actual usa cuotas impagas; el saldo histórico del KPI usa el último movimiento por entidad."]
            if view.startswith("cartera_") else None
        ),
    )
    payload["vista"] = view
    payload.setdefault("meta", {})["alcance"] = scope_label
    return payload
