"""
Búsqueda de artículos para autocomplete (paridad ``buscarArticulosAutocomplete``
en mayoristapp relay-stock-existencias.php).

Columnas alineadas a tablas AdministraNET habituales: ``IDArt``, ``Codigo``, ``nombre``, ``id_manual``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from core.mysql_pool import get_mysql_pool

logger = logging.getLogger(__name__)


def search_articulos_autocomplete(base_empresa: str, term: str, limit: int = 15) -> List[Dict[str, Any]]:
    """
    Devuelve filas estilo jQuery UI: ``id``, ``label``, ``value``.
    ``term`` vacío → lista vacía (paridad PHP).
    """
    t = (term or "").strip()
    if not t:
        return []

    like = f"%{t}%"
    lim = max(1, min(int(limit), 50))
    params: List[Any] = [like, like, like, lim]

    sql = """
        SELECT
            art.IDArt AS id_articulo,
            art.Codigo AS codigo,
            art.nombre AS nombre,
            art.id_manual AS id_manual
        FROM articulo AS art
        WHERE art.activo = 'Si'
          AND (
              art.Codigo LIKE %s
              OR art.nombre LIKE %s
              OR CAST(art.id_manual AS CHAR) LIKE %s
          )
        GROUP BY art.IDArt, art.Codigo, art.nombre, art.id_manual
        ORDER BY art.nombre
        LIMIT %s
    """

    pool = get_mysql_pool()
    out: List[Dict[str, Any]] = []
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        cols = [d[0] for d in cursor.description] if cursor.description else []
        for row in cursor.fetchall():
            rowd = dict(zip(cols, row))
            codigo = rowd.get("codigo") or ""
            nombre = rowd.get("nombre") or ""
            out.append(
                {
                    "id": rowd.get("id_articulo"),
                    "label": f"{codigo} - {nombre}".strip(" -"),
                    "value": codigo,
                }
            )
    return out
