"""Habilitación versionada máquina->artículo (varios artículos vigentes por máquina).

Tabla: mpr_maquina_articulo. Vigencia half-open [vigencia_desde, vigencia_hasta):
vigente(fecha) si vigencia_desde <= fecha AND (vigencia_hasta IS NULL OR vigencia_hasta > fecha).
El detalle del artículo (código manual, descripción) se lee de la tabla `articulo`.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from core.utils.administranet_types import to_int_or_none

from mpr.db import mysql_cursor


def _as_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()[:10]
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _tabla_articulo(cursor) -> Optional[str]:
    """Resuelve el nombre real de la tabla `articulo` (case-insensitive)."""
    cursor.execute("SHOW TABLES")
    for row in cursor.fetchall() or []:
        nombre = (list(row.values())[0] if isinstance(row, dict) else row[0]) or ""
        nombre = str(nombre).strip()
        if nombre.lower() == "articulo":
            return nombre
    return None


_COLS_ART = (
    "a.IDArt AS id_articulo, "
    "COALESCE(a.id_manual, '') AS codigo_manual, "
    "COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS codigo_articulo, "
    "COALESCE(a.NombreArticulo, '') AS descripcion_articulo"
)


def _map_articulo(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id_articulo": to_int_or_none(row.get("id_articulo")),
        "codigo_manual": str(row.get("codigo_manual") or ""),
        "codigo_articulo": str(row.get("codigo_articulo") or ""),
        "descripcion_articulo": str(row.get("descripcion_articulo") or ""),
    }


# --------------------------------------------------------------------------- #
# Búsqueda de artículos (para el buscador de la UI)
# --------------------------------------------------------------------------- #
def buscar_articulos(base_empresa: str, q: str, limit: int = 25) -> List[Dict[str, Any]]:
    base = (base_empresa or "").strip()
    if not base:
        return []
    try:
        lim = max(1, min(int(limit or 25), 50))
    except (TypeError, ValueError):
        lim = 25
    q = (q or "").strip()
    with mysql_cursor(base, dict_cursor=True) as cursor:
        tbl = _tabla_articulo(cursor)
        if not tbl:
            return []
        params: List[Any] = []
        filtro = ""
        if q:
            like = f"%{q}%"
            filtro = (
                " WHERE (COALESCE(a.id_manual,'') LIKE %s"
                " OR COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR),'') LIKE %s"
                " OR COALESCE(a.NombreArticulo,'') LIKE %s"
                " OR CAST(a.IDArt AS CHAR) LIKE %s)"
            )
            params = [like, like, like, like]
        params.append(lim)
        cursor.execute(
            f"SELECT {_COLS_ART} FROM `{tbl}` a{filtro} "
            f"ORDER BY codigo_articulo, a.IDArt LIMIT %s",
            params,
        )
        return [_map_articulo(r) for r in (cursor.fetchall() or []) if r.get("IDArt") is not None or r.get("id_articulo") is not None]


def articulos_por_ids(base_empresa: str, ids: List[int]) -> Dict[int, Dict[str, Any]]:
    base = (base_empresa or "").strip()
    id_list = sorted({x for x in (to_int_or_none(i) for i in (ids or [])) if x is not None})
    if not base or not id_list:
        return {}
    with mysql_cursor(base, dict_cursor=True) as cursor:
        tbl = _tabla_articulo(cursor)
        if not tbl:
            return {}
        ph = ",".join(["%s"] * len(id_list))
        cursor.execute(
            f"SELECT {_COLS_ART} FROM `{tbl}` a WHERE a.IDArt IN ({ph})",
            id_list,
        )
        out: Dict[int, Dict[str, Any]] = {}
        for r in cursor.fetchall() or []:
            info = _map_articulo(r)
            if info["id_articulo"] is not None:
                out[info["id_articulo"]] = info
        return out


# --------------------------------------------------------------------------- #
# Habilitación versionada
# --------------------------------------------------------------------------- #
def articulo_vigente(base_empresa: str, id_maquina: int, id_articulo: int, fecha: date) -> bool:
    base = (base_empresa or "").strip()
    mid = to_int_or_none(id_maquina)
    aid = to_int_or_none(id_articulo)
    if not base or mid is None or aid is None:
        return False
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT 1 FROM mpr_maquina_articulo
            WHERE id_mpr_maquina = %s AND id_articulo = %s
              AND vigencia_desde <= %s
              AND (vigencia_hasta IS NULL OR vigencia_hasta > %s)
            LIMIT 1
            """,
            [mid, aid, fecha, fecha],
        )
        return cursor.fetchone() is not None


def habilitar_articulo(base_empresa: str, id_maquina: int, id_articulo: int, desde: date) -> None:
    base = (base_empresa or "").strip()
    with mysql_cursor(base) as cursor:
        cursor.execute(
            """
            INSERT INTO mpr_maquina_articulo (id_mpr_maquina, id_articulo, vigencia_desde, vigencia_hasta)
            VALUES (%s, %s, %s, NULL)
            """,
            [int(id_maquina), int(id_articulo), desde],
        )


def deshabilitar_articulo(base_empresa: str, id_maquina: int, id_articulo: int, hasta: date) -> int:
    """Cierra la(s) vigencia(s) abierta(s) del artículo en la máquina. Devuelve filas afectadas."""
    base = (base_empresa or "").strip()
    with mysql_cursor(base) as cursor:
        cursor.execute(
            """
            UPDATE mpr_maquina_articulo
            SET vigencia_hasta = %s
            WHERE id_mpr_maquina = %s AND id_articulo = %s AND vigencia_hasta IS NULL
            """,
            [hasta, int(id_maquina), int(id_articulo)],
        )
        return int(cursor.rowcount or 0)


def listar_articulos_vigentes(
    base_empresa: str, id_maquina: int, fecha: date
) -> List[Dict[str, Any]]:
    """Artículos habilitados vigentes a `fecha` para una máquina, con detalle."""
    base = (base_empresa or "").strip()
    mid = to_int_or_none(id_maquina)
    if not base or mid is None:
        return []
    with mysql_cursor(base, dict_cursor=True) as cursor:
        tbl = _tabla_articulo(cursor)
        if not tbl:
            return []
        cursor.execute(
            f"""
            SELECT {_COLS_ART}, ma.vigencia_desde AS vigencia_desde
            FROM mpr_maquina_articulo ma
            INNER JOIN `{tbl}` a ON a.IDArt = ma.id_articulo
            WHERE ma.id_mpr_maquina = %s
              AND ma.vigencia_desde <= %s
              AND (ma.vigencia_hasta IS NULL OR ma.vigencia_hasta > %s)
            ORDER BY codigo_articulo, a.IDArt
            """,
            [mid, fecha, fecha],
        )
        out: List[Dict[str, Any]] = []
        for r in cursor.fetchall() or []:
            info = _map_articulo(r)
            info["vigencia_desde"] = _as_date(r.get("vigencia_desde"))
            out.append(info)
        return out


def historico_maquina_articulo(base_empresa: str, id_maquina: int) -> List[Dict[str, Any]]:
    base = (base_empresa or "").strip()
    mid = to_int_or_none(id_maquina)
    if not base or mid is None:
        return []
    with mysql_cursor(base, dict_cursor=True) as cursor:
        tbl = _tabla_articulo(cursor)
        join_art = f"LEFT JOIN `{tbl}` a ON a.IDArt = ma.id_articulo" if tbl else ""
        cols_art = _COLS_ART if tbl else (
            "ma.id_articulo AS id_articulo, '' AS codigo_manual, "
            "'' AS codigo_articulo, '' AS descripcion_articulo"
        )
        cursor.execute(
            f"""
            SELECT {cols_art}, ma.vigencia_desde AS vigencia_desde, ma.vigencia_hasta AS vigencia_hasta
            FROM mpr_maquina_articulo ma
            {join_art}
            WHERE ma.id_mpr_maquina = %s
            ORDER BY ma.vigencia_desde DESC, ma.id_mpr_maquina_articulo DESC
            """,
            [mid],
        )
        out: List[Dict[str, Any]] = []
        for r in cursor.fetchall() or []:
            info = _map_articulo(r)
            info["vigencia_desde"] = _as_date(r.get("vigencia_desde"))
            info["vigencia_hasta"] = _as_date(r.get("vigencia_hasta"))
            out.append(info)
        return out
