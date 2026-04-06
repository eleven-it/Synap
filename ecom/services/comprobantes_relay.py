"""
Listados de comprobantes desde ``comp_ped`` (paridad ``relay-pedidos.php``, ``relay-presupuestos.php``, ``relay-remitos.php``).

Solo lectura (SPEC [DECISIÓN-B-C1]). SQL parametrizado.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import to_int_or_none

from ecom.services.cliente_relay import cod_viajante_desde_sesion_usuario


def _si_no(val: Any, default: str = "No") -> str:
    if val is None:
        return default
    s = str(val).strip().lower()
    if s in ("si", "sí", "yes", "1", "true"):
        return "Si"
    return "No"


def _json_safe_row(item: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in list(item.items()):
        if isinstance(v, Decimal):
            item[k] = float(v)
        elif isinstance(v, (date, datetime)):
            item[k] = v.isoformat() if hasattr(v, "isoformat") else str(v)
        elif isinstance(v, bytes):
            item[k] = v.decode("utf-8", errors="replace")
    return item


def _append_filtros_busqueda(
    body: Dict[str, Any],
    tipo_listado: str,
    where: List[str],
    params: List[Any],
) -> None:
    """Fecha, NroComprobante, TipoPedido, estadoPedido (paridad PHP)."""
    campo = (body.get("campoBusca") or "-").strip()
    if campo == "-":
        return

    if campo == "Fecha":
        fd = (body.get("fechaDesde") or "").strip()
        fh = (body.get("fechaHasta") or "").strip()
        if fd and fh:
            where.append("comp_ped.Fecha BETWEEN %s AND %s")
            params.extend([fd, fh])
        return

    if campo == "NroComprobante":
        num = (body.get("numeroComp") or "").strip()
        if not num:
            return
        if tipo_listado == "ped":
            where.append("comp_ped.NroCompBusq LIKE %s")
            params.append(f"{num}%")
        else:
            where.append("comp_ped.NroCompBusq LIKE %s")
            params.append(f"%{num}%")
        return

    if campo == "TipoPedido":
        tp = body.get("tipoPedido")
        if tp is None or str(tp).strip() == "1":
            return
        where.append("comp_ped.TipoPedido = %s")
        params.append(str(tp).strip())


def _append_estado(body: Dict[str, Any], where: List[str], params: List[Any]) -> None:
    ep = body.get("estadoPedido")
    if ep is None or str(ep).strip() in ("", "1"):
        return
    where.append("comp_ped.Estado = %s")
    params.append(str(ep).strip())


def _append_tipo_remito(body: Dict[str, Any], where: List[str], params: List[Any]) -> None:
    tr = body.get("tipoRemito")
    if tr is None or str(tr).strip() in ("", "1"):
        return
    where.append("comp_ped.TipoPedido = %s")
    params.append(str(tr).strip())


def _where_pedidos(
    body: Dict[str, Any],
    sess_user: Dict[str, Any],
    idcliente: Optional[int],
) -> Tuple[str, List[Any]]:
    """Paridad ``relay-pedidos.php`` (vendedor / cliente)."""
    params: List[Any] = []
    parts: List[str] = []
    vendedor = str(body.get("vendedor") or "").lower() == "true"

    if not vendedor:
        if idcliente is not None:
            parts.append("comp_ped.Codigo = %s")
            params.append(idcliente)
        return (" AND " + " AND ".join(parts)) if parts else "", params

    cod_raw = body.get("filtraVendedor")
    if cod_raw is not None and str(cod_raw).strip().lower() != "todos":
        cv = to_int_or_none(cod_raw)
        if cv is not None:
            parts.append("comp_ped.CodViajante = %s")
            params.append(cv)
    else:
        cv = cod_viajante_desde_sesion_usuario(sess_user)
        if cv is not None:
            parts.append("comp_ped.CodViajante = %s")
            params.append(cv)

    if str(body.get("listaPed") or "").strip().lower() == "cliente" and idcliente is not None:
        parts.append("comp_ped.Codigo = %s")
        params.append(idcliente)

    if not parts:
        return "", []
    return " AND " + " AND ".join(parts), params


def _where_presupuestos(
    body: Dict[str, Any],
    sess_user: Dict[str, Any],
    idcliente: Optional[int],
) -> Tuple[str, List[Any]]:
    """Paridad ``relay-presupuestos.php`` (vendedor con ``filtraVendedor`` / ``todos_clientes``)."""
    params: List[Any] = []
    parts: List[str] = []
    vendedor = str(body.get("vendedor") or "").lower() == "true"

    if not vendedor:
        if idcliente is not None:
            parts.append("comp_ped.Codigo = %s")
            params.append(idcliente)
        return (" AND " + " AND ".join(parts)) if parts else "", params

    cod_raw = body.get("filtraVendedor")
    if cod_raw is not None and str(cod_raw).strip().lower() != "todos":
        cv = to_int_or_none(cod_raw)
        if cv is not None:
            parts.append("comp_ped.CodViajante = %s")
            params.append(cv)
    else:
        if _si_no(sess_user.get("todos_clientes"), "No") == "No":
            cv_sess = cod_viajante_desde_sesion_usuario(sess_user)
            if cv_sess is not None:
                parts.append("comp_ped.CodViajante = %s")
                params.append(cv_sess)

    if str(body.get("listaPed") or "").strip().lower() == "cliente" and idcliente is not None:
        parts.append("comp_ped.Codigo = %s")
        params.append(idcliente)

    if not parts:
        return "", []
    return " AND " + " AND ".join(parts), params


def _where_remitos(
    sess_user: Dict[str, Any],
    idcliente: Optional[int],
) -> Tuple[str, List[Any]]:
    """Paridad ``relay-remitos.php`` (cliente o idUsuario)."""
    if idcliente is not None:
        return " AND comp_ped.Codigo = %s", [idcliente]
    id_u = to_int_or_none(sess_user.get("id_usuario"))
    if id_u is not None:
        return " AND comp_ped.IdUsuario = %s", [id_u]
    return "", []


def listar_pedidos_relay(
    base_empresa: str,
    body: Dict[str, Any],
    sess_user: Dict[str, Any],
    idcliente: Optional[int],
    limit: int = 500,
) -> List[Dict[str, Any]]:
    where = ["comp_ped.TipoComprobante = %s"]
    params: List[Any] = ["PED"]
    _append_filtros_busqueda(body, "ped", where, params)
    _append_estado(body, where, params)
    extra_sql, extra_p = _where_pedidos(body, sess_user, idcliente)
    where_sql = " AND ".join(where) + extra_sql
    params.extend(extra_p)

    sql = f"""
        SELECT
            comp_ped.CodigoMovimiento AS CodigoMovimiento,
            comp_ped.id_comp_ped AS id,
            DATE_FORMAT(comp_ped.Fecha,'%d/%m/%Y') AS FechaB,
            comp_ped.Fecha AS Fecha,
            comp_ped.NroComprobante AS NroComprobante,
            comp_ped.SubtotalDesc AS SubTotalDesc,
            comp_ped.IVA1 AS IVA1,
            comp_ped.IVA2 AS IVA2,
            comp_ped.Exento AS Exento,
            comp_ped.CondVenta AS CondVenta,
            DATE_FORMAT(comp_ped.FechaEntrega,'%d/%m/%Y') AS FechaEntrega,
            comp_ped.FormaEntrega AS FormaEntrega,
            comp_ped.Estado AS Estado,
            cliente.nombre_cliente AS nombre_cliente,
            cliente.Codigo AS CodigoCliente,
            cliente.id_manual_cli AS id_manual_cli,
            CONCAT(viajantes.CodViajante,' - ',viajantes.Nombre) AS NombViajante,
            comp_ped.TipoPedido AS TipoPedido,
            comp_ped.autorizacion_sistema AS autorizacion_sistema,
            comp_ped.autorizacion_web AS autorizacion_web,
            comp_ped.Anulado AS Anulado,
            (comp_ped.IVA1 + comp_ped.IVA2) AS IVA,
            (comp_ped.SubtotalDesc + comp_ped.IVA1 + comp_ped.IVA2) AS Total
        FROM comp_ped
        LEFT JOIN cliente ON cliente.Codigo = comp_ped.Codigo
        LEFT JOIN viajantes ON viajantes.CodViajante = comp_ped.CodViajante
        WHERE {where_sql}
        ORDER BY comp_ped.Fecha DESC
        LIMIT %s
    """
    params.append(max(1, min(int(limit), 2000)))
    return _fetch_all(base_empresa, sql, params)


def listar_presupuestos_relay(
    base_empresa: str,
    body: Dict[str, Any],
    sess_user: Dict[str, Any],
    idcliente: Optional[int],
    limit: int = 500,
) -> List[Dict[str, Any]]:
    where = ["comp_ped.TipoComprobante = %s"]
    params: List[Any] = ["PRE"]
    _append_filtros_busqueda(body, "pre", where, params)
    _append_estado(body, where, params)
    extra_sql, extra_p = _where_presupuestos(body, sess_user, idcliente)
    where_sql = " AND ".join(where) + extra_sql
    params.extend(extra_p)

    sql = f"""
        SELECT
            comp_ped.CodigoMovimiento AS CodigoMovimiento,
            comp_ped.id_comp_ped AS id,
            DATE_FORMAT(comp_ped.Fecha,'%d/%m/%Y') AS FechaB,
            comp_ped.Fecha AS Fecha,
            comp_ped.NroComprobante AS NroComprobante,
            comp_ped.SubtotalDesc AS SubTotalDesc,
            comp_ped.IVA1 AS IVA1,
            comp_ped.IVA2 AS IVA2,
            comp_ped.Exento AS Exento,
            comp_ped.CondVenta AS CondVenta,
            DATE_FORMAT(comp_ped.FechaEntrega,'%d/%m/%Y') AS FechaEntrega,
            comp_ped.FormaEntrega AS FormaEntrega,
            comp_ped.Estado AS Estado,
            cliente.nombre_cliente AS nombre_cliente,
            cliente.Codigo AS codCliente,
            cliente.id_manual_cli AS codManualCliente,
            viajantes.Nombre AS nombreViajante,
            viajantes.CodViajante AS codViajante,
            comp_ped.TipoPedido AS TipoPedido,
            comp_ped.autorizacion_sistema AS autorizacion_sistema,
            comp_ped.autorizacion_web AS autorizacion_web,
            comp_ped.Anulado AS Anulado,
            (comp_ped.IVA1 + comp_ped.IVA2) AS IVA,
            (comp_ped.SubtotalDesc + comp_ped.IVA1 + comp_ped.IVA2) AS Total
        FROM comp_ped
        LEFT JOIN cliente ON cliente.Codigo = comp_ped.Codigo
        LEFT JOIN viajantes ON viajantes.CodViajante = comp_ped.CodViajante
        WHERE {where_sql}
        ORDER BY comp_ped.Fecha DESC
        LIMIT %s
    """
    params.append(max(1, min(int(limit), 2000)))
    return _fetch_all(base_empresa, sql, params)


def listar_remitos_relay(
    base_empresa: str,
    body: Dict[str, Any],
    sess_user: Dict[str, Any],
    idcliente: Optional[int],
    limit: int = 500,
) -> List[Dict[str, Any]]:
    where = ["comp_ped.TipoComprobante = %s"]
    params: List[Any] = ["REM"]
    _append_tipo_remito(body, where, params)
    _append_filtros_busqueda(body, "rem", where, params)
    _append_estado(body, where, params)
    extra_sql, extra_p = _where_remitos(sess_user, idcliente)
    where_sql = " AND ".join(where) + extra_sql
    params.extend(extra_p)

    sql = f"""
        SELECT
            comp_ped.CodigoMovimiento AS CodigoMovimiento,
            comp_ped.id_comp_ped AS id,
            DATE_FORMAT(comp_ped.Fecha,'%Y%m%d') AS FechaOrd,
            DATE_FORMAT(comp_ped.Fecha,'%d/%m/%Y') AS FechaB,
            comp_ped.Fecha AS Fecha,
            comp_ped.NroComprobante AS NroComprobante,
            comp_ped.CondVenta AS CondVenta,
            comp_ped.SubTotalGral AS SubTotalGral,
            cliente.nombre_cliente AS nombre_cliente,
            viajantes.Nombre AS NombreViajante,
            DATE_FORMAT(comp_ped.FechaEntrega,'%d/%m/%Y') AS FechaEntrega,
            comp_ped.FormaEntrega AS FormaEntrega,
            comp_ped.Estado AS Estado,
            comp_ped.TipoPedido AS TipoPedido,
            comp_ped.Tipo AS Tipo,
            comp_ped.autorizacion_sistema AS autorizacion_sistema,
            comp_ped.autorizacion_web AS autorizacion_web,
            comp_ped.Anulado AS Anulado,
            (comp_ped.IVA1 + comp_ped.IVA2) AS IVA,
            (comp_ped.SubtotalDesc + comp_ped.IVA1 + comp_ped.IVA2) AS Total
        FROM comp_ped
        LEFT JOIN cliente ON cliente.Codigo = comp_ped.Codigo
        LEFT JOIN viajantes ON viajantes.CodViajante = comp_ped.CodViajante
        WHERE {where_sql}
        ORDER BY comp_ped.Fecha DESC
        LIMIT %s
    """
    params.append(max(1, min(int(limit), 2000)))
    return _fetch_all(base_empresa, sql, params)


def _fetch_all(base_empresa: str, sql: str, params: List[Any]) -> List[Dict[str, Any]]:
    pool = get_mysql_pool()
    out: List[Dict[str, Any]] = []
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        cols = [d[0] for d in cursor.description] if cursor.description else []
        for row in cursor.fetchall():
            out.append(_json_safe_row(dict(zip(cols, row))))
    return out


def sugerencias_nro_comp_relay(
    base_empresa: str,
    tipo_comprobante: str,
    query_string: str,
    sess_user: Dict[str, Any],
    idcliente: Optional[int],
    limit: int = 10,
) -> List[str]:
    """
    Paridad ``queryString`` (autocomplete): ``NroCompBusq`` con prefijo.
    ``tipo_comprobante``: PED | PRE | REM.
    """
    q = (query_string or "").strip()
    if len(q) == 0:
        return []
    tc = (tipo_comprobante or "").strip().upper()
    if tc not in ("PED", "PRE", "REM"):
        return []

    where = ["comp_ped.TipoComprobante = %s", "comp_ped.NroCompBusq LIKE %s"]
    params: List[Any] = [tc, f"{q}%"]
    tipousuario = (sess_user.get("tipousuario") or "").strip().lower()
    if tipousuario == "vendedor":
        cv = cod_viajante_desde_sesion_usuario(sess_user)
        if cv is not None:
            where.append("comp_ped.CodViajante = %s")
            params.append(cv)
    elif idcliente is not None:
        where.append("comp_ped.Codigo = %s")
        params.append(idcliente)
    elif tc == "REM":
        id_u = to_int_or_none(sess_user.get("id_usuario"))
        if id_u is not None:
            where.append("comp_ped.IdUsuario = %s")
            params.append(id_u)

    sql = f"""
        SELECT comp_ped.NroCompBusq AS n
        FROM comp_ped
        WHERE {" AND ".join(where)}
        ORDER BY comp_ped.NroCompBusq DESC
        LIMIT %s
    """
    params.append(max(1, min(int(limit), 50)))
    pool = get_mysql_pool()
    out: List[str] = []
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        for row in cursor.fetchall():
            if row[0] is not None:
                out.append(str(row[0]))
    return out
