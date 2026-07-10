"""
Anulación de pedido (paridad ``relay-pedidos.php`` bloque ``anularPedido``).
"""

from __future__ import annotations

from typing import Any, Dict

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import to_decimal_or_none, to_int_or_none

from ecom.services.pedido_cabecera_relay import puede_anular_pedido_relay


def _revertir_stock_pedido(cursor, cod_mov: int) -> None:
    """Decrementa ``saldo_pedido_cliente`` según renglones ``stockp`` del PED."""
    cursor.execute(
        """
        SELECT IDArt, Salida, CodDeposito
        FROM stockp
        WHERE CodigoMovimiento = %s AND Anulado = 'No'
        """,
        [cod_mov],
    )
    for row in cursor.fetchall() or []:
        id_art = to_int_or_none(row[0])
        cant = to_decimal_or_none(row[1]) or 0
        id_dep = to_int_or_none(row[2])
        if id_art is None or id_dep is None or int(id_dep) <= 0 or cant <= 0:
            continue
        cursor.execute(
            """
            UPDATE stock_deposito
            SET saldo_pedido_cliente = GREATEST(
                0,
                COALESCE(saldo_pedido_cliente, 0) - %s
            )
            WHERE id_articulo = %s AND id_deposito = %s
            """,
            [cant, id_art, id_dep],
        )


def anular_pedido_relay(
    base_empresa: str,
    cod_mov_pedido: Any,
    *,
    revertir_stock: bool = True,
    motivo: str = "",
) -> Dict[str, str]:
    cod_mov = to_int_or_none(cod_mov_pedido)
    if cod_mov is None:
        return {"msg": "error", "error": "codMovPedido inválido."}
    motivo_txt = str(motivo or "").strip()
    if not motivo_txt:
        return {"msg": "error", "error": "Debe indicar el motivo de anulación."}
    if len(motivo_txt) > 500:
        return {"msg": "error", "error": "El motivo no puede superar 500 caracteres."}

    ok, err = puede_anular_pedido_relay(base_empresa, cod_mov)
    if not ok:
        return {"msg": "error", "error": err}

    pool = get_mysql_pool()
    errores = []
    with pool.get_connection(base_empresa) as conn:
        try:
            conn.autocommit(False)
            cursor = conn.cursor()
            if revertir_stock:
                _revertir_stock_pedido(cursor, cod_mov)
            cursor.execute(
                "UPDATE comp_ped SET Anulado='Si' WHERE CodigoMovimiento=%s",
                [cod_mov],
            )
            cursor.execute(
                """
                UPDATE comp_ped
                SET Detalle = TRIM(CONCAT(COALESCE(Detalle, ''), %s))
                WHERE CodigoMovimiento = %s
                """,
                [f"\n[Anulación Synap: {motivo_txt}]", cod_mov],
            )
            cursor.execute(
                "UPDATE stockp SET Anulado='Si' WHERE CodigoMovimiento=%s",
                [cod_mov],
            )
            cursor.execute(
                "UPDATE percep_cli SET Anulado='Si' WHERE codigo_movimiento=%s",
                [cod_mov],
            )
            conn.commit()
            return {"msg": "ok", "error": ""}
        except Exception as exc:  # pragma: no cover
            conn.rollback()
            errores.append(str(exc))
            return {"msg": "error", "error": " ".join(errores)}
        finally:
            conn.autocommit(True)
