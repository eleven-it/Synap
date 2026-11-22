"""Saldos actuales de clientes visibles en la cartera comercial."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from core.mysql_pool import mysql_cursor
from ecom.services.cliente_relay import _sesion_para_cartera
from ecom.services.vendedor_asignacion_sql import where_vendedor_cliente


def listar_saldos_clientes(base_empresa: str, sess_user: dict[str, Any]) -> list[dict[str, Any]]:
    """Usa el saldo consolidado de ``cliente``; acota por vendedor cuando corresponde."""
    if not base_empresa:
        return []
    filtro_cartera, params = where_vendedor_cliente(
        base_empresa, _sesion_para_cartera(sess_user, True)
    )
    sql = f"""
        SELECT cliente.Codigo, COALESCE(cliente.nombre_cliente, '') AS nombre_cliente,
               COALESCE(cliente.CUIT, '') AS cuit,
               COALESCE(cliente.saldo, 0) AS saldo,
               cliente.CodViajante, COALESCE(v.Nombre, '') AS vendedor
        FROM cliente AS cliente
        LEFT JOIN viajantes AS v ON v.CodViajante = cliente.CodViajante
        WHERE COALESCE(cliente.Estado, 'Activo') = 'Activo'
          {filtro_cartera}
        ORDER BY c.nombre_cliente, c.Codigo
    """
    with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall() or []
    return [
        {
            "codigo": int(row["Codigo"]),
            "nombre": str(row["nombre_cliente"] or "").strip(),
            "cuit": str(row["cuit"] or "").strip(),
            "saldo": Decimal(str(row["saldo"] or 0)),
            "vendedor": str(row["vendedor"] or "").strip(),
        }
        for row in rows
    ]
