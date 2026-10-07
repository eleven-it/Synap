"""Condición de IVA del cliente para la toma de pedidos."""

from core.mysql_pool import get_connection
from core.utils.administranet_types import to_int_or_none


IVA_NO_RESPONSABLE_ID = 9


def es_cliente_iva_no_responsable(base_empresa: str, id_cliente: int | None) -> bool:
    """Consulta la categoría vigente del cliente en contribuyentes (IDIva 9)."""
    codigo = to_int_or_none(id_cliente)
    if codigo is None:
        return False
    with get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT contribuyentes.IDIva
                FROM cliente
                INNER JOIN contribuyentes ON contribuyentes.IDIva = cliente.IDIva
                WHERE cliente.Codigo = %s
                LIMIT 1
                """,
                [codigo],
            )
            row = cursor.fetchone()
        finally:
            cursor.close()
    return bool(row and to_int_or_none(row[0]) == IVA_NO_RESPONSABLE_ID)
