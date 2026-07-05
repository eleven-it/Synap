"""
Relay artículos remitados (``relay-articulo-remito.php``).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import to_int_or_none

from ecom.services.comprobantes_relay import (
    _append_estado,
    _append_filtros_busqueda,
    _fetch_all,
    _json_safe_row,
)
from ecom.services.cliente_relay import cod_viajante_desde_sesion_usuario


def _where_articulo_remito(
    body: Dict[str, Any],
    sess_user: Dict[str, Any],
    idcliente: Optional[int],
) -> Tuple[str, List[Any]]:
    params: List[Any] = []
    parts: List[str] = []

    if idcliente is not None:
        parts.append("comp_ped.Codigo = %s")
        params.append(idcliente)
    else:
        cv = cod_viajante_desde_sesion_usuario(sess_user)
        id_usuario = to_int_or_none(sess_user.get("id_usuario"))
        if id_usuario is not None:
            parts.append("comp_ped.idUsuario = %s")
            params.append(id_usuario)
        elif cv is not None:
            parts.append("comp_ped.CodViajante = %s")
            params.append(cv)

    if not parts:
        return "", []
    return " AND " + " AND ".join(parts), params


def listar_articulo_remito_relay(
    base_empresa: str,
    body: Dict[str, Any],
    sess_user: Dict[str, Any],
    idcliente: Optional[int],
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """Paridad ``relay-articulo-remito.php`` (líneas stock en remitos REM)."""
    where = ["comp_ped.TipoComprobante = %s"]
    params: List[Any] = ["REM"]

    tr = body.get("tipoRemito")
    if tr is not None and str(tr).strip() not in ("", "1"):
        where.append("comp_ped.TipoPedido = %s")
        params.append(str(tr).strip())

    _append_filtros_busqueda(body, "ped", where, params)
    _append_estado(body, where, params)
    extra_sql, extra_p = _where_articulo_remito(body, sess_user, idcliente)
    where_sql = " AND ".join(where) + extra_sql
    params.extend(extra_p)

    sql = f"""
        SELECT
            stock.id_manual,
            stock.IDArt,
            stock.Descripcion,
            stock.Cantidad,
            comp_ped.CodigoMovimiento,
            comp_ped.id_comp_ped AS id,
            DATE_FORMAT(comp_ped.Fecha,'%d/%m/%Y') AS FechaB,
            comp_ped.NroComprobante,
            comp_ped.CondVenta,
            comp_ped.Estado,
            comp_ped.TipoPedido,
            comp_ped.Anulado,
            cliente.nombre_cliente,
            viajantes.Nombre AS nombreViajante,
            (comp_ped.SubtotalDesc + comp_ped.IVA1 + comp_ped.IVA2) AS Total
        FROM stock
        LEFT JOIN comp_ped ON comp_ped.CodigoMovimiento = stock.CodigoMovimiento
        LEFT JOIN cliente ON cliente.Codigo = comp_ped.Codigo
        LEFT JOIN viajantes ON viajantes.CodViajante = comp_ped.CodViajante
        WHERE {where_sql}
        ORDER BY comp_ped.Fecha DESC
        LIMIT %s
    """
    params.append(max(1, min(int(limit), 2000)))
    rows = _fetch_all(base_empresa, sql, params)
    return [_json_safe_row(r) for r in rows]
