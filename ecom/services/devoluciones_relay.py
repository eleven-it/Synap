"""
Relay de devoluciones (paridad relay-devoluciones.php, modo solo lectura).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Tuple

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


def _append_filtrar_por(where: List[str], params: List[Any], filtrar_por: str, usa_id_manual: bool) -> None:
    # Formato PHP: "cliente|123||rubro|4||subrubro|9"
    if not filtrar_por:
        return
    fields = {
        "cliente": "cliente.id_manual_cli" if usa_id_manual else "comp_ped.Codigo",
        "vendedor": "comp_ped.CodViajante",
        "articulo": "articulo.id_manual" if usa_id_manual else "articulo.IDArt",
        "rubro": "rubro.CodigoRubro",
        "subrubro": "subrubro.IDSubRubro",
        "proveedor": "articulo_prov.CodProveedor",
    }
    grouped: Dict[str, List[str]] = {}
    for raw in str(filtrar_por).split("||"):
        part = raw.strip()
        if "|" not in part:
            continue
        key, value = part.split("|", 1)
        col = fields.get(key.strip().lower())
        if not col:
            continue
        v = value.strip()
        if not v:
            continue
        grouped.setdefault(col, []).append(v)
    for col, vals in grouped.items():
        if len(vals) == 1:
            where.append(f"{col} = %s")
            params.append(vals[0])
        else:
            placeholders = ",".join(["%s"] * len(vals))
            where.append(f"{col} IN ({placeholders})")
            params.extend(vals)


def listar_devoluciones_relay(
    *,
    base_empresa: str,
    body: Dict[str, Any],
    usa_id_manual: bool,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    where: List[str] = ["comp_ped.TipoComprobante = %s"]
    params: List[Any] = ["DEV"]

    campo = str(body.get("campoBusca") or "1").strip()
    if campo == "Fecha":
        fd = str(body.get("fechaDesde") or "").strip()
        fh = str(body.get("fechaHasta") or "").strip()
        if fd and fh:
            where.append("comp_ped.Fecha BETWEEN %s AND %s")
            params.extend([fd, fh])
    elif campo == "NroComprobante":
        num = str(body.get("numeroComp") or "").strip()
        if num:
            where.append("comp_ped.NroCompBusq LIKE %s")
            params.append(f"%{num}%")

    filtrar_por = str(body.get("filtrarPor") or "").strip()
    if filtrar_por and filtrar_por != "1":
        _append_filtrar_por(where, params, filtrar_por, usa_id_manual=usa_id_manual)

    estado = str(body.get("estadoPedido") or "1").strip()
    if estado not in ("", "1"):
        where.append("comp_ped.Estado = %s")
        params.append(estado)

    sql = f"""
        SELECT
            comp_ped.CodigoMovimiento AS CodigoMovimiento,
            comp_ped.id_comp_ped AS id,
            DATE_FORMAT(comp_ped.Fecha,'%d/%m/%Y') AS FechaB,
            comp_ped.Fecha AS Fecha,
            punto_venta.nro_punto_venta AS nro_punto_venta,
            comp_ped.NroCompBusq AS NroCompBusq,
            comp_ped.NroComprobante AS NroComprobante,
            comp_ped.SubTotalDesc AS SubTotalDesc,
            comp_ped.IVA1 AS IVA1,
            comp_ped.IVA2 AS IVA2,
            comp_ped.Exento AS Exento,
            comp_ped.CondVenta AS CondVenta,
            DATE_FORMAT(comp_ped.FechaEntrega,'%d/%m/%Y') AS FechaEntrega,
            comp_ped.FormaEntrega AS FormaEntrega,
            comp_ped.Estado AS Estado,
            comp_ped.Detalle AS Detalle,
            cliente.nombre_cliente AS nombre_cliente,
            cliente.Codigo AS Codigo,
            cliente.id_manual_cli AS idManual,
            viajantes.Nombre AS viajante,
            comp_ped.TipoPedido AS TipoPedido,
            comp_ped.autorizacion_sistema AS autorizacion_sistema,
            comp_ped.autorizacion_web AS autorizacion_web,
            comp_ped.Anulado AS Anulado,
            (comp_ped.IVA1 + comp_ped.IVA2) AS IVA,
            (comp_ped.SubTotalDesc + comp_ped.IVA1 + comp_ped.IVA2) AS Total
        FROM comp_ped
        LEFT JOIN cliente ON cliente.Codigo = comp_ped.Codigo
        LEFT JOIN viajantes ON viajantes.CodViajante = comp_ped.CodViajante
        LEFT JOIN stockp ON stockp.CodigoMovimiento = comp_ped.CodigoMovimiento
        LEFT JOIN articulo ON articulo.IDArt = stockp.IDArt
        LEFT JOIN subrubro ON subrubro.IDSubRubro = articulo.IDSubRubro
        LEFT JOIN rubro ON rubro.CodigoRubro = articulo.CodigoRubro
        LEFT JOIN articulo_prov ON (articulo_prov.IDArt = articulo.IDArt AND articulo_prov.CodProveedor = articulo.CodigoProveedor)
        LEFT JOIN punto_venta ON punto_venta.id_punto_venta = comp_ped.id_pv
        WHERE {" AND ".join(where)}
        GROUP BY comp_ped.CodigoMovimiento
        ORDER BY comp_ped.Fecha DESC
        LIMIT %s
    """
    params.append(max(1, min(int(limit), 2000)))
    out: List[Dict[str, Any]] = []
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        c = conn.cursor()
        c.execute(sql, params)
        cols = [d[0] for d in c.description] if c.description else []
        for row in c.fetchall():
            out.append(_json_safe_row(dict(zip(cols, row))))
    return out


def sugerencias_nro_devoluciones_relay(
    *,
    base_empresa: str,
    query_string: str,
    tipousuario: str,
    cod_viajante: Any = None,
    idcliente: Any = None,
    limit: int = 10,
) -> List[str]:
    q = (query_string or "").strip()
    if not q:
        return []
    where = ["comp_ped.TipoComprobante = 'DEV'", "comp_ped.NroCompBusq LIKE %s"]
    params: List[Any] = [f"{q}%"]
    if (tipousuario or "").strip().lower() == "vendedor":
        cv = to_int_or_none(cod_viajante)
        if cv is not None:
            where.append("comp_ped.CodViajante = %s")
            params.append(cv)
    else:
        idc = to_int_or_none(idcliente)
        if idc is not None:
            where.append("comp_ped.Codigo = %s")
            params.append(idc)
    sql = f"""
        SELECT comp_ped.NroCompBusq AS n
        FROM comp_ped
        WHERE {" AND ".join(where)}
        ORDER BY comp_ped.NroCompBusq DESC
        LIMIT %s
    """
    params.append(max(1, min(int(limit), 50)))
    out: List[str] = []
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        c = conn.cursor()
        c.execute(sql, params)
        for row in c.fetchall():
            if row[0] is not None:
                out.append(str(row[0]))
    return out

