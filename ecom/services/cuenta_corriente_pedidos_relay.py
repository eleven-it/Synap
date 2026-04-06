"""
Pedidos del cliente vistos como cuenta corriente (paridad ``relay-cuenta-corriente.php``).

Reutiliza ``listar_pedidos_relay`` en modo cliente, ignorando ``vendedor`` en el cuerpo
(para no permitir ampliar el alcance más allá del ``idcliente`` de sesión).
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import to_int_or_none

from ecom.services.comprobantes_relay import listar_pedidos_relay


def listar_pedidos_cuenta_corriente_relay(
    base_empresa: str,
    body: Dict[str, Any],
    sess_user: Dict[str, Any],
    codigo_cliente: int,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """
    Listado ``comp_ped`` tipo PED solo para ``codigo_cliente``.

    Filtros: ``campoBusca`` (``Fecha``, ``NroComprobante``), ``estadoPedido``, ``limit``.
    Fechas en formato ``YYYY-MM-DD`` (Synap); el PHP antiguo usaba ``dd/mm/yyyy``.
    """
    limpio = {k: v for k, v in body.items() if k != "vendedor"}
    return listar_pedidos_relay(
        base_empresa,
        limpio,
        sess_user,
        codigo_cliente,
        limit=limit,
    )


def sugerencias_nro_pedido_cuenta_corriente_relay(
    base_empresa: str,
    query_string: str,
    codigo_cliente: int,
    limit: int = 10,
) -> List[str]:
    """Autocomplete ``NroCompBusq`` (PED) solo para el cliente en sesión (paridad ``queryString``)."""
    q = (query_string or "").strip()
    if not q:
        return []
    lim = max(1, min(int(to_int_or_none(limit) or 10), 50))
    sql = """
        SELECT comp_ped.NroCompBusq AS n
        FROM comp_ped
        WHERE comp_ped.TipoComprobante = %s
          AND comp_ped.Codigo = %s
          AND comp_ped.NroCompBusq LIKE %s
        ORDER BY comp_ped.NroCompBusq DESC
        LIMIT %s
    """
    pool = get_mysql_pool()
    out: List[str] = []
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, ["PED", codigo_cliente, f"{q}%", lim])
        for row in cursor.fetchall():
            if row[0] is not None:
                out.append(str(row[0]))
    return out
