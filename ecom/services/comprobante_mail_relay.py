"""
Paridad de ``relay-comprobante-a-mail.php`` (preparación de payload hacia fin-comprobante).

Nota v1: este relay no envía email directamente; solo resuelve el comprobante y
genera el token de redirección de manera segura.
"""

from __future__ import annotations

import base64
import json
from decimal import Decimal
from typing import Any, Dict, Optional

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import to_int_or_none


def _json_safe(v: Any) -> Any:
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, bytes):
        return v.decode("utf-8", errors="replace")
    return v


def _encode_token(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def obtener_comprobante_para_mail(
    base_empresa: str,
    cod_mov: int,
    tipo_comp: int,
    idcliente: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Obtiene datos mínimos del comprobante y arma token de redirección.

    ``tipo_comp``:
    - 1: origen ``cuentacliente``
    - 0: origen ``comp_ped``
    """
    if tipo_comp not in (0, 1):
        return None

    params = [cod_mov]
    extra = ""
    if idcliente is not None:
        extra = " AND cc.Codigo = %s"
        params.append(idcliente)

    if tipo_comp == 1:
        sql = f"""
            SELECT
                cc.TipoComprobante AS TipoComprobante,
                cc.NroComprobante AS NroComprobante,
                IF(ISNULL(cc.ImporteVenta), cc.ImporteCobro, cc.ImporteVenta) AS total,
                cc.Codigo AS Codigo
            FROM cuentacliente AS cc
            WHERE cc.CodigoMovimiento = %s
            {extra}
            LIMIT 1
        """
    else:
        sql = f"""
            SELECT
                cc.TipoComprobante AS TipoComprobante,
                cc.NroComprobante AS NroComprobante,
                cc.ImporteVenta AS total,
                cc.Codigo AS Codigo
            FROM comp_ped AS cc
            WHERE cc.CodigoMovimiento = %s
            {extra}
            LIMIT 1
        """

    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        row = cursor.fetchone()
        if not row:
            return None
        item = {
            "TipoComprobante": _json_safe(row[0]),
            "NroComprobante": _json_safe(row[1]),
            "total": _json_safe(row[2]),
            "Codigo": _json_safe(row[3]),
        }

    payload = {
        "numerocomprobante": item["NroComprobante"],
        "tipocomprobante": item["TipoComprobante"],
        "codigomovimiento": cod_mov,
        "codigo": item["Codigo"],
    }
    token = _encode_token(payload)
    return {
        "comprobante": payload,
        "token": token,
        "redirect_path": f"fin-comprobante.php?p={token}",
    }


def parsear_parametros_mail(query_params: Dict[str, Any]) -> Optional[tuple[int, int]]:
    cod_mov = to_int_or_none(query_params.get("codMov"))
    tipo = to_int_or_none(query_params.get("tipocomprobante"))
    if cod_mov is None or tipo is None:
        return None
    return cod_mov, tipo

