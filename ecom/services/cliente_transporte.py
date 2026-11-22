"""Transporte por domicilio de entrega del cliente."""

from __future__ import annotations

from core.mysql_pool import mysql_cursor, get_mysql_pool


def consultar_transportes_cliente(base_empresa: str, codigo_cliente: int) -> dict:
    with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
        cursor.execute(
            "SELECT id_transporte AS id, nombre_transporte AS nombre "
            "FROM transporte WHERE anulado = 'No' ORDER BY nombre_transporte"
        )
        transportes = list(cursor.fetchall() or [])
        cursor.execute(
            "SELECT cm.id_cliente_domicilio AS id, cm.Calle AS calle, "
            "cm.NroCalle AS numero, cm.id_transporte AS id_transporte "
            "FROM cliente_domicilio cm "
            "WHERE cm.id_cliente = %s AND cm.anulado = 'No' "
            "ORDER BY cm.id_cliente_domicilio",
            [codigo_cliente],
        )
        domicilios = list(cursor.fetchall() or [])
    return {"transportes": transportes, "domicilios": domicilios}


def fijar_transporte_cliente(
    base_empresa: str, codigo_cliente: int, id_domicilio: int, id_transporte: int
) -> bool:
    """Actualiza el transporte predeterminado solo si el catálogo y domicilio están activos."""
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT 1 FROM transporte WHERE id_transporte = %s AND anulado = 'No' LIMIT 1",
                [id_transporte],
            )
            if cursor.fetchone() is None:
                return False
            cursor.execute(
                "UPDATE cliente_domicilio SET id_transporte = %s "
                "WHERE id_cliente_domicilio = %s AND id_cliente = %s AND anulado = 'No'",
                [id_transporte, id_domicilio, codigo_cliente],
            )
            actualizado = cursor.rowcount == 1
            if actualizado:
                conn.commit()
            return actualizado
        finally:
            cursor.close()
