"""
Lotes con stock por depósito (paridad mayoristapp relay-lote.php).

MySQL: tablas ``lote``, ``lote_stock``.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List

from core.mysql_pool import get_mysql_pool


def list_lotes_por_articulo_deposito(
    base_empresa: str, id_articulo: int, id_deposito: int
) -> List[Dict[str, Any]]:
    """
    Lotes activos con stock > 0 en el depósito indicado (orden por vencimiento ASC).

    Respuesta alineada al dato que arma el HTML PHP (sin HTML): cada ítem incluye
    ``valor_seleccion`` = ``id_lote|stock_lote`` para radios.
    """
    sql = """
        SELECT
            lote.id_lote,
            lote.cod_lote,
            lote.fecha_vto_lote,
            lote.stock_total_lote,
            lote_stock.stock_lote
        FROM lote
        INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote)
        WHERE lote.id_articulo = %s
          AND lote.anulado = 'No'
          AND lote_stock.stock_lote > 0
          AND lote_stock.id_deposito = %s
        ORDER BY lote.fecha_vto_lote ASC
    """
    pool = get_mysql_pool()
    out: List[Dict[str, Any]] = []
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, [id_articulo, id_deposito])
        cols = [d[0] for d in cursor.description] if cursor.description else []
        for row in cursor.fetchall():
            item = dict(zip(cols, row))
            id_lote = item.get("id_lote")
            stk = item.get("stock_lote")
            if id_lote is not None and stk is not None:
                item["valor_seleccion"] = f"{id_lote}|{stk}"
            else:
                item["valor_seleccion"] = ""
            fv = item.get("fecha_vto_lote")
            if isinstance(fv, datetime):
                item["fecha_vto_lote"] = fv.date().isoformat()
            elif isinstance(fv, date):
                item["fecha_vto_lote"] = fv.isoformat()
            for k, v in list(item.items()):
                if isinstance(v, Decimal):
                    item[k] = float(v)
            out.append(item)
    return out
