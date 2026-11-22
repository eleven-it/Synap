"""Saldos actuales de clientes visibles en la cartera comercial."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from core.mysql_pool import mysql_cursor
from ecom.services.alcance_comercial import alcance_viajantes_comercial
from ecom.services.pedido_permisos import puede_ver_todos_pedidos


def listar_saldos_clientes(base_empresa: str, sess_user: dict[str, Any]) -> list[dict[str, Any]]:
    """Usa el saldo consolidado de ``cliente``; acota por vendedor cuando corresponde."""
    if not base_empresa:
        return []
    params: list[Any] = []
    filtro_cartera = ""
    if not puede_ver_todos_pedidos(sess_user):
        viajantes = alcance_viajantes_comercial(base_empresa, sess_user)
        if not viajantes:
            return []
        filtro_cartera = f"AND c.CodViajante IN ({','.join(['%s'] * len(viajantes))})"
        params.extend(viajantes)
    sql = f"""
        SELECT c.Codigo, COALESCE(c.nombre_cliente, '') AS nombre_cliente,
               COALESCE(c.CUIT, '') AS cuit,
               COALESCE(c.saldo, 0) AS saldo,
               c.CodViajante, COALESCE(v.Nombre, '') AS vendedor
        FROM cliente AS c
        LEFT JOIN viajantes AS v ON v.CodViajante = c.CodViajante
        WHERE COALESCE(c.Estado, 'Activo') = 'Activo'
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
