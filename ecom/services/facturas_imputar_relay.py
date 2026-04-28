"""
Relays de facturas para imputar (paridad base ``relay_facturas_imputar.php``).
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from core.mysql_pool import get_mysql_pool

TIPOS_IMPUTABLES = ("FA", "FB", "FM", "FC", "FE", "NDA", "NDM", "NDC", "NDE", "NDB", "AJD", "INID")


def _json_safe_row(item: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in list(item.items()):
        if isinstance(v, Decimal):
            item[k] = float(v)
        elif isinstance(v, (date, datetime)):
            item[k] = v.isoformat() if hasattr(v, "isoformat") else str(v)
        elif isinstance(v, bytes):
            item[k] = v.decode("utf-8", errors="replace")
    return item


def _where_facturas_imputar(
    body: Dict[str, Any],
    idcliente: int,
) -> Tuple[List[str], List[Any]]:
    where: List[str] = [
        "rf.Estado = 'N/Canc'",
        "rf.TipoComprobante IN ('FA','FB','FM','FC','FE','NDA','NDM','NDC','NDE','NDB','AJD','INID')",
        "rf.Saldo <> 0",
        "rf.Anulado = 'No'",
        "rf.Codigo = %s",
    ]
    params: List[Any] = [idcliente]

    campo = (body.get("campoBusca") or "").strip()
    if campo == "Fecha":
        fd = (body.get("fechaDesde") or "").strip()
        fh = (body.get("fechaHasta") or "").strip()
        if fd and fh:
            where.append("rf.Fecha BETWEEN %s AND %s")
            params.extend([fd, fh])
    elif campo == "NroComprobante":
        num = (body.get("numeroComp") or "").strip()
        if num:
            where.append("rf.NroComprobante LIKE %s")
            params.append(f"%{num}%")
    elif campo == "TipoPedido":
        tp = (body.get("tipoPedido") or "").strip()
        if tp:
            where.append("rf.TipoComprobante = %s")
            params.append(tp)

    return where, params


def listar_facturas_imputar_relay(
    base_empresa: str,
    body: Dict[str, Any],
    idcliente: int,
    limit: int = 60,
) -> List[Dict[str, Any]]:
    where, params = _where_facturas_imputar(body, idcliente)
    lim = max(1, min(int(limit), 2000))
    sql = f"""
        SELECT
            rf.id_recibo_factura AS id_recibo_factura,
            rf.TipoComprobante AS TipoComprobante,
            rf.Fecha AS Fecha,
            DATE_FORMAT(rf.Fecha,'%d/%m/%Y') AS FechaB,
            rf.NroComprobante AS NroComprobante,
            rf.CodigoMovimiento AS CodigoMovimiento,
            rf.Importe AS Importe,
            rf.ImporteNC AS ImporteNC,
            rf.Cancelado AS Cancelado,
            rf.Saldo AS Saldo,
            rf.Neto AS Neto
        FROM recibo_factura AS rf
        WHERE {" AND ".join(where)}
        ORDER BY rf.Fecha DESC
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
            item = _json_safe_row(dict(zip(cols, row)))
            # Paridad con hidden JSON del PHP para seleccionar comprobantes a imputar.
            item["payload_json"] = json.dumps(item, ensure_ascii=False, separators=(",", ":"))
            out.append(item)
    return out


def sugerencias_nro_facturas_imputar_relay(
    base_empresa: str,
    query_string: str,
    idcliente: int,
    limit: int = 10,
) -> List[str]:
    q = (query_string or "").strip()
    if not q:
        return []
    sql = """
        SELECT rf.NroCompBusq AS n
        FROM recibo_factura AS rf
        WHERE rf.Estado = 'N/Canc'
          AND rf.TipoComprobante IN ('FA','FB','FM','FC','FE','NDA','NDM','NDC','NDE','NDB','AJD','INID')
          AND rf.Saldo <> 0
          AND rf.Anulado = 'No'
          AND rf.Codigo = %s
          AND rf.NroComprobante LIKE %s
        ORDER BY rf.CodigoMovimiento ASC
        LIMIT %s
    """
    pool = get_mysql_pool()
    out: List[str] = []
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, [idcliente, f"%{q}%", max(1, min(int(limit), 50))])
        for row in cursor.fetchall():
            if row[0] is not None:
                out.append(str(row[0]))
    return out
