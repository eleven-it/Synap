"""
Artículos más vendidos ecommerce (paridad inventario/includes/mas-vendidos.php).

``relay-mas-vendidos.php`` en PHP no expone lógica en el cuerpo principal; la consulta
canónica usada en pantalla es la de ``mas-vendidos.php`` (top por movimientos ``stock``).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import to_int_or_none


def list_mas_vendidos_ecommerce(
    base_empresa: str,
    *,
    limit: int = 15,
    id_categoria: Optional[int] = None,
    id_rubro: Optional[int] = None,
    id_subrubro: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Ranking por ``COUNT`` de filas ``stock`` por artículo (``TipoComp`` venta / TPV),
    solo artículos ecommerce activos y rubro ecommerce.
    """
    lim = max(1, min(int(limit), 50))

    where_extra: List[str] = []
    params: List[Any] = []

    if id_categoria is not None:
        where_extra.append("rubro.id_categoria = %s")
        params.append(id_categoria)
    if id_rubro is not None:
        where_extra.append("articulo.CodigoRubro = %s")
        params.append(id_rubro)
    if id_subrubro is not None:
        where_extra.append("articulo.IDSubRubro = %s")
        params.append(id_subrubro)

    filtro = ""
    if where_extra:
        filtro = " AND " + " AND ".join(where_extra)

    # Subconsulta de agregación: compatible con ONLY_FULL_GROUP_BY (el PHP agrupaba solo por IDArt).
    sql = f"""
        SELECT
            agg.cuantos AS cuantos,
            articulo.id_manual AS id_manual,
            articulo.IDArt AS id_art,
            articulo.IDSubRubro AS id_subrubro,
            articulo.CodigoSubRubro AS codigo_subrubro,
            articulo.CodigoRubro AS codigo_rubro,
            articulo.NombreArticulo AS nombre_articulo,
            rubro.id_categoria AS id_categoria,
            rubro_categoria.nombre_categoria AS nombre_categoria,
            rubro.NombreRubro AS nombre_rubro,
            subrubro.NombreSubRubro AS nombre_subrubro
        FROM (
            SELECT stock.IDArt AS id_art, COUNT(*) AS cuantos
            FROM stock
            INNER JOIN articulo ON articulo.IDArt = stock.IDArt
            INNER JOIN rubro ON rubro.CodigoRubro = articulo.CodigoRubro
            WHERE articulo.Discontinuo = 'No'
              AND articulo.ecommerce = 'Si'
              AND articulo.tipo_art = 'Articulo'
              AND stock.Anulado = 'No'
              AND rubro.ecommerce = 'Si'
              AND stock.TipoComp IN ('Venta', 'Venta TPV')
              {filtro}
            GROUP BY stock.IDArt
        ) AS agg
        INNER JOIN articulo ON articulo.IDArt = agg.id_art
        LEFT JOIN rubro ON rubro.CodigoRubro = articulo.CodigoRubro
        LEFT JOIN rubro_categoria ON rubro_categoria.id_categoria = rubro.id_categoria
        LEFT JOIN subrubro ON subrubro.IDSubRubro = articulo.IDSubRubro
        ORDER BY agg.cuantos DESC,
                 rubro.id_categoria,
                 rubro.CodigoRubro,
                 subrubro.IDSubRubro ASC
        LIMIT %s
    """
    params.append(lim)

    pool = get_mysql_pool()
    out: List[Dict[str, Any]] = []
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        cols = [d[0] for d in cursor.description] if cursor.description else []
        for row in cursor.fetchall():
            item = dict(zip(cols, row))
            out.append(_json_safe_row(item))
    return out


def _json_safe_row(item: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in list(item.items()):
        if isinstance(v, (date, datetime)):
            item[k] = v.isoformat() if isinstance(v, date) else v.date().isoformat()
        elif isinstance(v, Decimal):
            item[k] = float(v)
        elif isinstance(v, bytes):
            item[k] = v.decode("utf-8", errors="replace")
    return item


def parse_filtros_mas_vendidos(query_params) -> Dict[str, Optional[int]]:
    """Normaliza query params GET para ``list_mas_vendidos_ecommerce``."""
    return {
        "id_categoria": to_int_or_none(query_params.get("id_categoria") or query_params.get("idcategoria")),
        "id_rubro": to_int_or_none(query_params.get("id_rubro") or query_params.get("idrubro")),
        "id_subrubro": to_int_or_none(
            query_params.get("id_subrubro") or query_params.get("idsubrubro") or query_params.get("idSubRubro")
        ),
    }


def parse_limit_mas_vendidos(query_params, default: int = 15) -> int:
    n = to_int_or_none(query_params.get("limit") or query_params.get("limite"))
    if n is None:
        return default
    return max(1, min(int(n), 50))
