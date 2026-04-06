"""
Relays de nota de crédito mayoristapp (paridad base ``relay_nota_credito.php``).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import to_int_or_none
from ecom.services.cliente_relay import cod_viajante_desde_sesion_usuario

TIPOS_NC = ("NCA", "NCB", "NCC", "NCM", "NCE")


def _json_safe_row(item: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in list(item.items()):
        if isinstance(v, Decimal):
            item[k] = float(v)
        elif isinstance(v, (date, datetime)):
            item[k] = v.isoformat() if hasattr(v, "isoformat") else str(v)
        elif isinstance(v, bytes):
            item[k] = v.decode("utf-8", errors="replace")
    return item


def _where_nota_credito(
    body: Dict[str, Any],
    sess_user: Dict[str, Any],
    idcliente: Optional[int],
) -> Tuple[List[str], List[Any]]:
    where: List[str] = ["cc.TipoComprobante IN ('NCA','NCB','NCC','NCM','NCE')"]
    params: List[Any] = []

    tipo_fact = (body.get("tipoFact") or "").strip()
    campo = (body.get("campoBusca") or "").strip()
    if campo == "TipoPedido" and tipo_fact and tipo_fact != "-":
        where = ["cc.TipoComprobante = %s"]
        params = [tipo_fact]

    fd = (body.get("fechaDesde") or "").strip()
    fh = (body.get("fechaHasta") or "").strip()
    if fd and fh:
        where.append("cc.Fecha BETWEEN %s AND %s")
        params.extend([fd, fh])

    if campo == "NroComprobante":
        n = (body.get("numeroComp") or "").strip()
        if n:
            where.append("cc.NroCompBusq LIKE %s")
            params.append(f"%{n}%")

    estado = (body.get("estadoFact") or "").strip()
    if estado:
        where.append("cc.Estado = %s")
        params.append(estado)

    vendedor = str(body.get("vendedor") or "").strip().lower() == "true"
    if vendedor:
        todos = str(sess_user.get("todos_clientes") or "No").strip().lower()
        if todos == "no":
            cv = cod_viajante_desde_sesion_usuario(sess_user)
            if cv is not None:
                where.append("cc.CodViajante = %s")
                params.append(cv)
        if str(body.get("listaFact") or "").strip().lower() == "cliente" and idcliente is not None:
            where.append("cc.Codigo = %s")
            params.append(idcliente)
    elif idcliente is not None:
        where.append("cc.Codigo = %s")
        params.append(idcliente)

    return where, params


def listar_nota_credito_relay(
    base_empresa: str,
    body: Dict[str, Any],
    sess_user: Dict[str, Any],
    idcliente: Optional[int],
    limit: int = 60,
) -> List[Dict[str, Any]]:
    where, params = _where_nota_credito(body, sess_user, idcliente)
    lim = max(1, min(int(limit), 2000))
    sql = f"""
        SELECT
            cc.CodigoMovimiento AS CodigoMovimiento,
            cc.id_cuentacliente AS id,
            DATE_FORMAT(cc.Fecha,'%d/%m/%Y') AS FechaB,
            cc.Fecha AS Fecha,
            cc.TipoComprobante AS TipoComprobante,
            cc.NroComprobante AS NroComprobante,
            cc.SubTotalDesc AS SubTotalDesc,
            cc.IVA1 AS IVA1,
            cc.IVA2 AS IVA2,
            IF(cc.fe_comp='si','ELECT','TALON') AS TipoFact,
            cc.Exento AS Exento,
            cc.Estado AS Estado,
            cc.Detalle AS Detalle,
            cc.TipoNC AS TipoNC,
            cc.CondVenta AS CondVenta,
            cliente.nombre_cliente AS nombre_cliente,
            cliente.Codigo AS Codigo,
            cliente.id_manual_cli AS id_manual_cli,
            viajantes.Nombre AS NombreViajante,
            cc.Anulado AS Anulado,
            (cc.IVA1 + cc.IVA2) AS IVA,
            (cc.SubTotalDesc + cc.IVA1 + cc.IVA2) AS Total
        FROM cuentacliente AS cc
        LEFT JOIN cliente ON cliente.Codigo = cc.Codigo
        LEFT JOIN viajantes ON viajantes.CodViajante = cc.CodViajante
        WHERE {" AND ".join(where)}
        ORDER BY cc.Fecha DESC
        LIMIT %s
    """
    params.append(lim)
    pool = get_mysql_pool()
    out: List[Dict[str, Any]] = []
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        cols = [d[0] for d in cursor.description] if cursor.description else []
        for row in cursor.fetchall():
            out.append(_json_safe_row(dict(zip(cols, row))))
    return out


def sugerencias_nro_nota_credito_relay(
    base_empresa: str,
    query_string: str,
    sess_user: Dict[str, Any],
    idcliente: Optional[int],
    limit: int = 10,
) -> List[str]:
    q = (query_string or "").strip()
    if not q:
        return []
    where = ["cc.TipoComprobante IN ('NCA','NCB','NCC','NCM','NCE')", "cc.NroCompBusq LIKE %s"]
    params: List[Any] = [f"{q}%"]
    tipousuario = (sess_user.get("tipousuario") or "").strip().lower()
    if tipousuario == "vendedor":
        cv = cod_viajante_desde_sesion_usuario(sess_user)
        if cv is not None:
            where.append("cc.CodViajante = %s")
            params.append(cv)
    elif idcliente is not None:
        where.append("cc.Codigo = %s")
        params.append(idcliente)
    sql = f"""
        SELECT cc.NroCompBusq AS n
        FROM cuentacliente AS cc
        WHERE {" AND ".join(where)}
        ORDER BY cc.NroCompBusq DESC
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
