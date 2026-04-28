"""
Anulación de pedido (paridad ``relay-pedidos.php`` bloque ``anularPedido``).
"""

from __future__ import annotations

from typing import Any, Dict

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import to_int_or_none


def anular_pedido_relay(base_empresa: str, cod_mov_pedido: Any) -> Dict[str, str]:
    cod_mov = to_int_or_none(cod_mov_pedido)
    if cod_mov is None:
        return {"msg": "error", "error": "codMovPedido inválido."}

    pool = get_mysql_pool()
    errores = []
    with pool.get_connection(base_empresa) as conn:
        try:
            conn.autocommit(False)
            cursor = conn.cursor()
            cursor.execute("UPDATE comp_ped SET Anulado='Si' WHERE CodigoMovimiento=%s", [cod_mov])
            cursor.execute("UPDATE stockp SET Anulado='Si' WHERE CodigoMovimiento=%s", [cod_mov])
            cursor.execute("UPDATE percep_cli SET Anulado='Si' WHERE codigo_movimiento=%s", [cod_mov])
            conn.commit()
            return {"msg": "ok", "error": ""}
        except Exception as exc:  # pragma: no cover
            conn.rollback()
            errores.append(str(exc))
            return {"msg": "error", "error": " ".join(errores)}
        finally:
            conn.autocommit(True)

