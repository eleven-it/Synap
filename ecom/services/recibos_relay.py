"""
Listado de recibos desde ``cuentacliente`` (paridad ``relay-recibos.php`` → ``lista_recibos``).

Solo lectura. Filtros alineados al PHP: vendedor / usuario, fechas, cliente.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

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


def listar_recibos_relay(
    base_empresa: str,
    body: Dict[str, Any],
    sess_user: Dict[str, Any],
    limit: int = 500,
) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """
    Recibos (``TipoComprobante='REC'``), sin movimiento anulador.

    Retorna ``(filas, None)`` o ``(None, mensaje_error)`` si falta ``id_usuario`` cuando aplica.
    """
    id_u_sess = to_int_or_none(sess_user.get("id_usuario"))
    if "filtraVendedor" not in body and id_u_sess is None:
        return None, "Se requiere id_usuario en la sesión para el listado de recibos."

    where: List[str] = [
        "cuentacliente.TipoComprobante = %s",
        "cuentacliente.codigo_movimiento_anul IS NULL",
    ]
    params: List[Any] = ["REC"]

    fv = body.get("filtraVendedor", None)
    if fv is not None and str(fv).strip().lower() != "todos":
        cv = to_int_or_none(fv)
        if cv is not None:
            where.append("cuentacliente.CodViajante = %s")
            params.append(cv)
    elif "filtraVendedor" not in body:
        where.append("cuentacliente.IdUsuario = %s")
        params.append(id_u_sess)

    campo = (body.get("campoBusca") or "").strip()
    if campo == "Fecha":
        fd = (body.get("fechaDesde") or "").strip()
        fh = (body.get("fechaHasta") or "").strip()
        if fd and fh:
            where.append("cuentacliente.Fecha BETWEEN %s AND %s")
            params.extend([fd, fh])

    fc = body.get("filtraCliente")
    if fc is not None and str(fc).strip().lower() != "todos":
        cod = to_int_or_none(fc)
        if cod is not None:
            where.append("cuentacliente.Codigo = %s")
            params.append(cod)

    lim = max(1, min(int(to_int_or_none(body.get("limit")) or limit), 2000))

    sql = f"""
        SELECT
            DATE_FORMAT(cuentacliente.Fecha,'%d/%m/%Y') AS FechaB,
            DATE_FORMAT(cuentacliente.Fecha,'%Y%m%d') AS FechaYmd,
            cuentacliente.TipoComprobante AS TipoComprobante,
            cuentacliente.tiporec AS tipoRecibo,
            cliente.Codigo AS codCliente,
            cliente.id_manual_cli AS codManualCliente,
            cliente.nombre_cliente AS nombre_cliente,
            cuentacliente.NroComprobante AS NroComprobante,
            cuentacliente.TotalImputacionRec AS ImporteTotal,
            cuentacliente.ImporteCobro AS Importe,
            cuentacliente.TotalEfectivoP AS Efectivo,
            cuentacliente.TotalEfectivoD AS Dolar,
            cuentacliente.TotalCheque AS Cheque,
            cuentacliente.TotalRetencion AS Retencion,
            COALESCE(cuentacliente.total_trans, 0) AS Transferencia,
            cuentacliente.Total_Tarjeta AS Tarjeta,
            cuentacliente.TotalDescRec AS Descuento,
            cuentacliente.CodigoMovimiento AS CodigoMovimiento,
            cuentacliente.codigo_movimiento_anul AS codigo_movimiento_anul,
            cuentacliente.Detalle AS Detalle,
            tra.transfDetalle AS transfDetalle,
            CONCAT(viajantes.Nombre,' (Cod: ',viajantes.CodViajante,')') AS viajante,
            cuentacliente.Anulado AS Anulado
        FROM cuentacliente
        LEFT JOIN cliente ON cliente.Codigo = cuentacliente.Codigo
        LEFT JOIN (
            SELECT
                GROUP_CONCAT(
                    CONCAT(
                        banco.Nombre, ' cta: ', cuenta_banco.NroCuenta, '|', transferencia.importe_transf
                    )
                ) AS transfDetalle,
                transferencia.codigo_movimiento AS codigo_movimiento
            FROM transferencia
            LEFT JOIN cuenta_banco ON cuenta_banco.CodCuenta = transferencia.id_cuentabancaria
            LEFT JOIN banco ON banco.CodBanco = cuenta_banco.CodBanco
            GROUP BY transferencia.codigo_movimiento
        ) AS tra ON tra.codigo_movimiento = cuentacliente.CodigoMovimiento
        LEFT JOIN viajantes ON viajantes.CodViajante = cuentacliente.CodViajante
        WHERE {" AND ".join(where)}
        ORDER BY cuentacliente.Fecha DESC, cuentacliente.CodigoMovimiento DESC
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
    return out, None
