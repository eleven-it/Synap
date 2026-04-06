"""
Cuenta corriente desde ``cuentacliente`` (paridad ``relay-ctacte.php``).

Solo lectura. Requiere ``idcliente`` en sesión (mismo criterio que PHP).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import to_int_or_none


def _json_safe_row(item: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in list(item.items()):
        if isinstance(v, Decimal):
            item[k] = float(v)
        elif isinstance(v, (date, datetime)):
            item[k] = v.isoformat() if hasattr(v, "isoformat") else str(v)
        elif isinstance(v, bytes):
            item[k] = v.decode("utf-8", errors="replace")
    return item


def listar_movimientos_ctacte_relay(
    base_empresa: str,
    body: Dict[str, Any],
    codigo_cliente: int,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """
    Listado movimientos cuenta corriente para ``Codigo`` = cliente en sesión.

    Filtros: ``campoBusca`` = ``Fecha`` (``fechaDesde``, ``fechaHasta``) | ``NroComprobante`` (``numeroComp`` prefijo).
    """
    where = ["cuentacliente.Codigo = %s"]
    params: List[Any] = [codigo_cliente]

    campo = (body.get("campoBusca") or "-").strip()
    if campo == "Fecha":
        fd = (body.get("fechaDesde") or "").strip()
        fh = (body.get("fechaHasta") or "").strip()
        if fd and fh:
            where.append("cuentacliente.Fecha BETWEEN %s AND %s")
            params.extend([fd, fh])
    elif campo == "NroComprobante":
        num = (body.get("numeroComp") or "").strip()
        if num:
            where.append("CAST(cuentacliente.NroCompBusq AS CHAR) LIKE %s")
            params.append(f"{num}%")

    lim = max(1, min(int(to_int_or_none(body.get("limit")) or limit), 2000))

    sql = f"""
        SELECT
            DATE_FORMAT(cuentacliente.Fecha,'%d/%m/%Y') AS FechaB,
            DATE_FORMAT(cuentacliente.Fecha,'%Y%m%d') AS FechaYmd,
            cuentacliente.Fecha AS Fecha,
            cuentacliente.TipoComprobante AS TipoComprobante,
            cuentacliente.NroComprobante AS NroComprobante,
            cuentacliente.CondVenta AS CondVenta,
            cuentacliente.ImporteVenta AS Debito,
            cuentacliente.ImporteCobro AS Credito,
            cuentacliente.saldo AS saldo,
            DATE_FORMAT(cuentacliente.Vencimiento,'%d/%m/%Y') AS Vencimiento,
            cuentacliente.Vencido AS Vencido,
            cuentacliente.Estado AS Estado,
            cuentacliente.Anulado AS Anulado,
            cuentacliente.Recibo AS Recibo,
            cuentacliente.NroFactura AS NroFactura,
            cuentacliente.Detalle AS Detalle
        FROM cuentacliente
        WHERE {" AND ".join(where)}
        ORDER BY cuentacliente.Fecha DESC
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


def sugerencias_nro_ctacte_relay(
    base_empresa: str,
    query_string: str,
    codigo_cliente: int,
    limit: int = 10,
) -> List[str]:
    """Autocomplete ``NroCompBusq`` (prefijo), mismo cliente que sesión."""
    q = (query_string or "").strip()
    if not q:
        return []
    lim = max(1, min(int(limit), 50))
    sql = """
        SELECT cuentacliente.NroCompBusq AS n
        FROM cuentacliente
        WHERE cuentacliente.Codigo = %s
          AND CAST(cuentacliente.NroCompBusq AS CHAR) LIKE %s
        ORDER BY cuentacliente.NroCompBusq DESC
        LIMIT %s
    """
    pool = get_mysql_pool()
    out: List[str] = []
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, [codigo_cliente, f"{q}%", lim])
        for row in cursor.fetchall():
            if row[0] is not None:
                out.append(str(row[0]))
    return out
