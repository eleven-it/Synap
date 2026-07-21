"""Habilitación versionada máquina->artículo (varios artículos vigentes por máquina).

Tabla: mpr_maquina_articulo. Vigencia half-open [vigencia_desde, vigencia_hasta):
vigente(fecha) si vigencia_desde <= fecha AND (vigencia_hasta IS NULL OR vigencia_hasta > fecha).
El detalle del artículo (código manual, descripción) se lee de la tabla `articulo`.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from core.utils.administranet_types import str_codigo_manual_articulo, to_int_or_none

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


def _as_iso_datetime(value: Any) -> Optional[str]:
    """Serializa DATETIME MySQL a string ISO estable para JSON/UI."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%S")
    s = str(value).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s[:19], fmt).strftime("%Y-%m-%dT%H:%M:%S")
        except (ValueError, TypeError):
            continue
    return s[:19].replace(" ", "T") if len(s) >= 19 else s


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
    "a.id_manual AS id_manual, "
    "COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS codigo_articulo, "
    "COALESCE(a.NombreArticulo, '') AS descripcion_articulo"
)


def _map_articulo(row: Dict[str, Any]) -> Dict[str, Any]:
    # Código de usuario = articulo.id_manual (no CodigoArticulo / CodigoArticuloT).
    codigo = str_codigo_manual_articulo(row.get("id_manual") or row.get("codigo_manual"))
    talle = str(row.get("talle") or "").strip()
    color = str(row.get("color") or "").strip()
    if talle in ("-",):
        talle = ""
    if color in ("-",):
        color = ""
    return {
        "id_articulo": to_int_or_none(row.get("id_articulo")),
        "codigo_manual": "" if codigo == "-" else codigo,
        "codigo_articulo": str(row.get("codigo_articulo") or ""),
        "descripcion_articulo": str(row.get("descripcion_articulo") or ""),
        "talle": talle,
        "color": color,
    }


def _slots_talle_color(cursor) -> tuple[Optional[int], Optional[int]]:
    """Resuelve id_articulo_ce de TALLES y COLOR por caption (no hardcodear slots)."""
    try:
        cursor.execute("SELECT id_articulo_ce, caption FROM articulo_ce")
    except Exception:
        return None, None
    talle_slot: Optional[int] = None
    color_slot: Optional[int] = None
    for r in cursor.fetchall() or []:
        cap = str(r.get("caption") or "").strip().upper()
        sid = to_int_or_none(r.get("id_articulo_ce"))
        if sid is None:
            continue
        if talle_slot is None and cap in ("TALLES", "TALLE"):
            talle_slot = sid
        if color_slot is None and cap == "COLOR":
            color_slot = sid
    return talle_slot, color_slot


def _sql_joins_ce(talle_slot: Optional[int], color_slot: Optional[int]) -> tuple[str, str]:
    """JOIN + columnas CE; params se agregan aparte si hay slots."""
    joins = ""
    cols = ", '' AS talle, '' AS color"
    if talle_slot is not None and color_slot is not None:
        joins = (
            " LEFT JOIN articulo_val_ce vt"
            " ON vt.id_articulo = a.IDArt AND vt.id_articulo_ce = %s"
            " LEFT JOIN articulo_val_ce vc"
            " ON vc.id_articulo = a.IDArt AND vc.id_articulo_ce = %s"
        )
        cols = (
            ", COALESCE(vt.valor_ce, '') AS talle"
            ", COALESCE(vc.valor_ce, '') AS color"
        )
    elif talle_slot is not None:
        joins = (
            " LEFT JOIN articulo_val_ce vt"
            " ON vt.id_articulo = a.IDArt AND vt.id_articulo_ce = %s"
        )
        cols = ", COALESCE(vt.valor_ce, '') AS talle, '' AS color"
    elif color_slot is not None:
        joins = (
            " LEFT JOIN articulo_val_ce vc"
            " ON vc.id_articulo = a.IDArt AND vc.id_articulo_ce = %s"
        )
        cols = ", '' AS talle, COALESCE(vc.valor_ce, '') AS color"
    return joins, cols


def _params_ce(talle_slot: Optional[int], color_slot: Optional[int]) -> List[Any]:
    params: List[Any] = []
    if talle_slot is not None:
        params.append(talle_slot)
    if color_slot is not None:
        params.append(color_slot)
    return params


# --------------------------------------------------------------------------- #
# Búsqueda de artículos (para el buscador de la UI)
# --------------------------------------------------------------------------- #
def buscar_articulos(
    base_empresa: str,
    q: str,
    limit: int = 25,
    tipo_art_fab: Optional[str] = None,
) -> List[Dict[str, Any]]:
    base = (base_empresa or "").strip()
    if not base:
        return []
    try:
        lim = max(1, min(int(limit or 25), 50))
    except (TypeError, ValueError):
        lim = 25
    q = (q or "").strip()
    tipo_filtro = (tipo_art_fab or "").strip()
    with mysql_cursor(base, dict_cursor=True) as cursor:
        tbl = _tabla_articulo(cursor)
        if not tbl:
            return []
        params: List[Any] = []
        condiciones: List[str] = []
        if q:
            like = f"%{q}%"
            condiciones.append(
                "(COALESCE(a.id_manual,'') LIKE %s"
                " OR COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR),'') LIKE %s"
                " OR COALESCE(a.NombreArticulo,'') LIKE %s"
                " OR CAST(a.IDArt AS CHAR) LIKE %s)"
            )
            params.extend([like, like, like, like])
        if tipo_filtro:
            condiciones.append("COALESCE(TRIM(a.tipo_art_fab),'') = %s")
            params.append(tipo_filtro)
        filtro = ""
        if condiciones:
            filtro = " WHERE " + " AND ".join(condiciones)
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
        talle_slot, color_slot = _slots_talle_color(cursor)
        joins_ce, cols_ce = _sql_joins_ce(talle_slot, color_slot)
        params: List[Any] = _params_ce(talle_slot, color_slot) + [mid, fecha, fecha]
        cursor.execute(
            f"""
            SELECT {_COLS_ART}, ma.vigencia_desde AS vigencia_desde,
                   ma.creado_en AS creado_en, ma.id_mpr_maquina_articulo AS id_mpr_maquina_articulo{cols_ce}
            FROM mpr_maquina_articulo ma
            INNER JOIN `{tbl}` a ON a.IDArt = ma.id_articulo
            {joins_ce}
            WHERE ma.id_mpr_maquina = %s
              AND ma.vigencia_desde <= %s
              AND (ma.vigencia_hasta IS NULL OR ma.vigencia_hasta > %s)
            ORDER BY ma.vigencia_desde ASC, ma.creado_en ASC, ma.id_mpr_maquina_articulo ASC
            """,
            params,
        )
        out: List[Dict[str, Any]] = []
        for r in cursor.fetchall() or []:
            info = _map_articulo(r)
            info["vigencia_desde"] = _as_date(r.get("vigencia_desde"))
            info["creado_en"] = _as_iso_datetime(r.get("creado_en"))
            info["id_mpr_maquina_articulo"] = to_int_or_none(r.get("id_mpr_maquina_articulo"))
            out.append(info)
        return out


def listar_articulos_vigentes_todas_maquinas(
    base_empresa: str, fecha: date
) -> Dict[int, List[Dict[str, Any]]]:
    """Artículos habilitados vigentes a `fecha`, agrupados por id_mpr_maquina."""
    base = (base_empresa or "").strip()
    if not base:
        return {}
    with mysql_cursor(base, dict_cursor=True) as cursor:
        tbl = _tabla_articulo(cursor)
        if not tbl:
            return {}
        talle_slot, color_slot = _slots_talle_color(cursor)
        joins_ce, cols_ce = _sql_joins_ce(talle_slot, color_slot)
        params: List[Any] = _params_ce(talle_slot, color_slot) + [fecha, fecha]
        cursor.execute(
            f"""
            SELECT ma.id_mpr_maquina, {_COLS_ART}, ma.vigencia_desde AS vigencia_desde,
                   ma.creado_en AS creado_en, ma.id_mpr_maquina_articulo AS id_mpr_maquina_articulo{cols_ce}
            FROM mpr_maquina_articulo ma
            INNER JOIN `{tbl}` a ON a.IDArt = ma.id_articulo
            {joins_ce}
            WHERE ma.vigencia_desde <= %s
              AND (ma.vigencia_hasta IS NULL OR ma.vigencia_hasta > %s)
            ORDER BY ma.id_mpr_maquina, ma.vigencia_desde ASC, ma.creado_en ASC, ma.id_mpr_maquina_articulo ASC
            """,
            params,
        )
        out: Dict[int, List[Dict[str, Any]]] = {}
        for r in cursor.fetchall() or []:
            mid = to_int_or_none(r.get("id_mpr_maquina"))
            if mid is None:
                continue
            info = _map_articulo(r)
            info["vigencia_desde"] = _as_date(r.get("vigencia_desde"))
            info["creado_en"] = _as_iso_datetime(r.get("creado_en"))
            info["id_mpr_maquina_articulo"] = to_int_or_none(r.get("id_mpr_maquina_articulo"))
            out.setdefault(mid, []).append(info)
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
            "ma.id_articulo AS id_articulo, NULL AS id_manual, "
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
