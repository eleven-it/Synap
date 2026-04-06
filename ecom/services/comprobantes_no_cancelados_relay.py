"""
Comprobantes no cancelados (paridad ``relay-comprobantes-ncancelados.php`` y
``relay-comp-no-cancelados-resumen.php``).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.mysql_pool import get_mysql_pool


def _json_safe_row(item: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in list(item.items()):
        if isinstance(v, Decimal):
            item[k] = float(v)
        elif isinstance(v, (date, datetime)):
            item[k] = v.isoformat() if hasattr(v, "isoformat") else str(v)
        elif isinstance(v, bytes):
            item[k] = v.decode("utf-8", errors="replace")
    return item


def _where(body: Dict[str, Any], idcliente: int, prefijo_nro: bool) -> tuple[List[str], List[Any]]:
    where = [
        "recibo_factura.TipoComprobante <> 'INIC'",
        "recibo_factura.TipoComprobante <> 'INID'",
        "recibo_factura.Saldo <> 0",
        "recibo_factura.Codigo = %s",
        "recibo_factura.Anulado = 'No'",
        "recibo_factura.Estado = 'N/Canc'",
    ]
    params: List[Any] = [idcliente]
    campo = (body.get("campoBusca") or "").strip()
    if campo == "Fecha":
        fd = (body.get("fechaDesde") or "").strip()
        fh = (body.get("fechaHasta") or "").strip()
        if fd and fh:
            where.append("recibo_factura.Fecha BETWEEN %s AND %s")
            params.extend([fd, fh])
    elif campo == "NroComprobante":
        num = (body.get("numeroComp") or "").strip()
        if num:
            where.append("recibo_factura.NroComprobante LIKE %s")
            params.append(f"{num}%" if prefijo_nro else f"%{num}%")
    return where, params


def _saldo_signed(tipo: str, saldo: float) -> float:
    if (tipo or "").strip().upper() in ("AJC", "REC", "NCA", "NCB", "NCC", "NCM", "NCE"):
        return float(saldo or 0) * -1
    return float(saldo or 0)


def listar_no_cancelados_relay(
    base_empresa: str,
    body: Dict[str, Any],
    idcliente: int,
    limit: int = 1000,
) -> Dict[str, Any]:
    where, params = _where(body, idcliente, prefijo_nro=False)
    sql = f"""
        SELECT
            DATE_FORMAT(recibo_factura.Fecha,'%d/%m/%Y') AS FechaB,
            recibo_factura.Fecha AS Fecha,
            recibo_factura.TipoComprobante AS TipoComprobante,
            recibo_factura.Cancelado AS Cancelado,
            recibo_factura.NroComprobante AS NroComprobante,
            recibo_factura.Importe AS Importe,
            recibo_factura.CondVenta AS CondVenta,
            recibo_factura.Saldo AS Saldo
        FROM recibo_factura
        WHERE {" AND ".join(where)}
        ORDER BY recibo_factura.Fecha ASC
        LIMIT %s
    """
    params.append(max(1, min(int(limit), 5000)))
    pool = get_mysql_pool()
    filas: List[Dict[str, Any]] = []
    saldo_acum = 0.0
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        cols = [d[0] for d in cursor.description] if cursor.description else []
        for row in cursor.fetchall():
            item = _json_safe_row(dict(zip(cols, row)))
            saldo_signed = _saldo_signed(str(item.get("TipoComprobante") or ""), float(item.get("Saldo") or 0))
            saldo_acum += saldo_signed
            item["SaldoSigned"] = saldo_signed
            item["SaldoAcum"] = saldo_acum
            filas.append(item)
    return {"filas": filas, "saldo_al_dia": saldo_acum}


def listar_no_cancelados_resumen_relay(
    base_empresa: str,
    body: Dict[str, Any],
    idcliente: int,
    limit: int = 1000,
) -> Dict[str, Any]:
    where, params = _where(body, idcliente, prefijo_nro=True)
    sql = f"""
        SELECT
            DATE_FORMAT(recibo_factura.Fecha,'%d/%m/%Y') AS FechaB,
            recibo_factura.Fecha AS Fecha,
            recibo_factura.TipoComprobante AS TipoComprobante,
            recibo_factura.Cancelado AS Cancelado,
            recibo_factura.NroComprobante AS NroComprobante,
            recibo_factura.Importe AS Importe,
            recibo_factura.CondVenta AS CondVenta,
            recibo_factura.Saldo AS Saldo
        FROM recibo_factura
        WHERE {" AND ".join(where)}
        ORDER BY recibo_factura.Fecha ASC
        LIMIT %s
    """
    params.append(max(1, min(int(limit), 5000)))
    pool = get_mysql_pool()
    filas: List[Dict[str, Any]] = []
    saldo_acum = 0.0
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        cols = [d[0] for d in cursor.description] if cursor.description else []
        for row in cursor.fetchall():
            item = _json_safe_row(dict(zip(cols, row)))
            saldo_signed = _saldo_signed(str(item.get("TipoComprobante") or ""), float(item.get("Saldo") or 0))
            saldo_acum += saldo_signed
            item["SaldoSigned"] = saldo_signed
            item["Resumen"] = f"${item.get('Importe')} | ${item.get('Cancelado')} | ${saldo_signed}"
            filas.append(item)
    return {"filas": filas, "saldo_al_dia": saldo_acum}

