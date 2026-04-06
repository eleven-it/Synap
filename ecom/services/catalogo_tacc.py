"""
Opciones TACC / sin TACC (paridad mayoristapp relay-tacc.php).

Si existe la columna ``articulo.sin_tacc``, devuelve el mismo JSON que el PHP;
si no, ``mensaje: sinTacc`` y ``valores`` vacío.
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.mysql_pool import get_mysql_pool


def tacc_relay_payload(base_empresa: str) -> Dict[str, Any]:
    pool = get_mysql_pool()
    hay = False
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) AS c
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'articulo'
              AND COLUMN_NAME = 'sin_tacc'
            """
        )
        row = cursor.fetchone()
        if row and row[0]:
            hay = int(row[0]) > 0

    if not hay:
        return {"mensaje": "sinTacc", "valores": []}

    valores: List[Dict[str, str]] = [
        {"id": "", "name": "- tacc -"},
        {"id": "Si", "name": "Si"},
        {"id": "No", "name": "No"},
    ]
    return {"mensaje": "ok", "valores": valores}
