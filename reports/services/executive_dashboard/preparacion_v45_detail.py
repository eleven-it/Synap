"""Pedidos individuales detrás de los estados de Preparación V45."""
from __future__ import annotations

from .base import DashboardFilters, build_paginated_response, round_money
from .comercial_v45 import _scope
from .preparacion_v45 import _dates, _exists, _states


PREPARACION_V45_VIEWS = frozenset({
    "pedidos", "pendientes", "en_preparacion", "preparados", "backorder",
    "en_remito", "facturados", "cerrados", "anulados",
})


def list_preparacion_v45_detail(cursor, filters: DashboardFilters, *, view: str) -> dict:
    if view not in PREPARACION_V45_VIEWS:
        raise ValueError("Estado de pedido inválido")
    if not _exists(cursor, "comp_ped"):
        payload = build_paginated_response(filters, [], 0)
        payload["vista"] = view
        payload["disponible"] = False
        return payload
    states = _states(_exists(cursor, "comp_ped", "cod_mov_ped_orginal"))
    linked = view in {"en_remito", "facturados"}
    if linked and not (_exists(cursor, "stock") and _exists(cursor, "stock", "codmov_pedido")):
        payload = build_paginated_response(filters, [], 0)
        payload["vista"] = view
        payload["disponible"] = False
        return payload
    if view == "anulados":
        condition = "UPPER(COALESCE(cp.Anulado,'NO'))='SI'"
    else:
        condition = "UPPER(COALESCE(cp.Anulado,'NO'))<>'SI'"
        if view not in {"pedidos", "en_remito", "facturados"}:
            condition += f" AND {states[view]}"
    if linked:
        if view == "facturados":
            if not _exists(cursor, "cuentacliente"):
                payload = build_paginated_response(filters, [], 0)
                payload["vista"] = view
                payload["disponible"] = False
                return payload
            join = "JOIN cuentacliente doc ON doc.CodigoMovimiento=s.CodigoMovimiento"
            linked_condition = (
                "s.TipoComp IN ('Venta','Venta TPV','ND Anul NC') "
                "AND doc.TipoComprobante IN ('FA','FB','FC','FE','FM','NDA','NDB','NDC','NDE','NDM')"
            )
        else:
            join = "JOIN comp_ped doc ON doc.CodigoMovimiento=s.codmov_remito"
            linked_condition = "doc.TipoComprobante='REM'"
        condition += (
            f" AND EXISTS (SELECT 1 FROM stock s {join} "
            "WHERE s.codmov_pedido=cp.CodigoMovimiento "
            "AND UPPER(COALESCE(s.Anulado,'NO'))<>'SI' "
            "AND UPPER(COALESCE(doc.Anulado,'NO'))<>'SI' "
            f"AND {linked_condition})"
        )
    scope, scope_params = _scope("cp", filters)
    source = (
        "SELECT DATE_FORMAT(cp.Fecha,'%%Y-%%m-%%d') fecha,"
        "cp.CodigoMovimiento movimiento,COALESCE(cp.NroComprobante,'') comprobante,"
        "cp.Codigo codigo_cliente,COALESCE(c.nombre_cliente,'') cliente,"
        "cp.CodSucursal sucursal,cp.id_pv punto_venta,"
        "COALESCE(cp.Estado,'') estado,COALESCE(cp.FormaEntrega,'') entrega,"
        "DATE_FORMAT(cp.FechaEntrega,'%%Y-%%m-%%d') fecha_entrega,"
        "cp.cod_mov_ped_orginal pedido_original,COALESCE(cp.ImporteVenta,0) importe "
        "FROM comp_ped cp LEFT JOIN cliente c ON c.Codigo=cp.Codigo "
        "WHERE cp.Fecha >= %s AND cp.Fecha < %s "
        f"AND cp.TipoComprobante='PED' AND cp.CodigoMovimiento<>0 AND {condition}{scope}"
    )
    params = _dates(filters) + scope_params
    search = ""
    if filters.busqueda:
        search = (
            " WHERE (CAST(q.movimiento AS CHAR) LIKE %s OR q.comprobante LIKE %s "
            "OR q.cliente LIKE %s OR q.estado LIKE %s)"
        )
        params += [f"%{filters.busqueda}%"] * 4
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
    keys = [column[0] for column in cursor.description]
    rows = [dict(zip(keys, row)) for row in cursor.fetchall() or []]
    payload = build_paginated_response(
        filters, rows, int(count or 0), None if linked else round_money(amount),
        notas_semanticas=(
            ["La cantidad corresponde a pedidos vinculados. El monto del KPI suma comprobantes únicos, no importes de pedidos."]
            if linked else None
        ),
    )
    payload["vista"] = view
    return payload
