# -*- coding: utf-8 -*-
"""Asignación vendedor ↔ cliente / marca (tablas vendedores_*_asignacion)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Literal, Optional, Tuple

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import str_or_default, to_int_or_none

logger = logging.getLogger(__name__)


def _mensaje_error_sql(exc: Exception) -> str:
    msg = str(exc)
    if "1146" in msg or "doesn't exist" in msg.lower():
        return (
            "Faltan las tablas de asignación en esta base. "
            "Ejecutá la migración «Ventas — asignación vendedor-cliente / vendedor-marca» "
            "en Archivo → Migración esquema MySQL (legacy)."
        )
    return msg


ModoAsignacion = Literal["cliente", "marca"]
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100

_TABLAS = {
    "cliente": {
        "asignacion": "vendedores_clientes_asignacion",
        "id_item": "id_cliente",
        "maestro": "cliente",
        "pk_maestro": "Codigo",
        "nombre_col": "nombre_cliente",
        "activo_where": "cliente.Estado = 'Activo' AND cliente.Codigo <> 1",
        "busqueda_cols": ("cliente.nombre_cliente", "CAST(cliente.Codigo AS CHAR)", "cliente.id_manual_cli"),
    },
    "marca": {
        "asignacion": "vendedores_marcas_asignacion",
        "id_item": "id_marca",
        "maestro": "marca",
        "pk_maestro": "CodMarca",
        "nombre_col": "NombreMarca",
        "activo_where": "COALESCE(marca.anulado, 'No') = 'No'",
        "busqueda_cols": ("marca.NombreMarca", "CAST(marca.CodMarca AS CHAR)"),
    },
}


def _meta(modo: str) -> Dict[str, str]:
    m = (modo or "").strip().lower()
    if m not in _TABLAS:
        raise ValueError("modo_invalido")
    return _TABLAS[m]


def _usuario_mod(sess_user: Optional[Dict[str, Any]]) -> str:
    if not sess_user:
        return "-"
    raw = str_or_default(
        sess_user.get("cod_usuario") or sess_user.get("nombre_usuario"),
        "-",
    )
    return raw[:60] if raw else "-"


def buscar_vendedores_activos(
    base_empresa: str,
    q: str = "",
    limit: int = 50,
) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """Búsqueda predictiva por código o nombre (solo activos)."""
    q = (q or "").strip()
    lim = max(1, min(int(limit), 100))
    try:
        pool = get_mysql_pool()
        where = ["COALESCE(viajantes.anulado, 'No') = 'No'"]
        params: List[Any] = []
        if q:
            q_int = to_int_or_none(q)
            if q_int is not None:
                where.append(
                    "(viajantes.CodViajante = %s OR viajantes.Nombre LIKE %s)"
                )
                params.extend([q_int, f"%{q}%"])
            else:
                where.append("viajantes.Nombre LIKE %s")
                params.append(f"%{q}%")
        sql = f"""
            SELECT viajantes.CodViajante, COALESCE(viajantes.Nombre, '') AS Nombre
            FROM viajantes
            WHERE {' AND '.join(where)}
            ORDER BY viajantes.Nombre ASC
            LIMIT %s
        """
        params.append(lim)
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, params)
                rows = [
                    {
                        "id_vendedor": int(r[0]),
                        "nombre": (r[1] or "").strip(),
                        "etiqueta": f"{(r[1] or '').strip()} (cod: {int(r[0])})",
                    }
                    for r in cursor.fetchall()
                ]
                return True, "", rows
            finally:
                cursor.close()
    except Exception as e:
        logger.exception("buscar_vendedores_activos: %s", e)
        return False, str(e), []


def listar_resumen_vendedores(
    base_empresa: str,
    modo: ModoAsignacion,
    q: str = "",
) -> Tuple[bool, str, List[Dict[str, Any]], int]:
    """Sidebar: vendedores activos con cantidad asignada + total sin asignar."""
    try:
        meta = _meta(modo)
        tbl_a = meta["asignacion"]
        tbl_m = meta["maestro"]
        pk = meta["pk_maestro"]
        activo = meta["activo_where"]
        q = (q or "").strip().lower()

        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                sql_v = f"""
                    SELECT
                        v.CodViajante AS id_vendedor,
                        COALESCE(v.Nombre, '') AS nombre,
                        COUNT(a.id) AS cantidad
                    FROM viajantes v
                    LEFT JOIN {tbl_a} a ON a.id_vendedor = v.CodViajante
                    WHERE COALESCE(v.anulado, 'No') = 'No'
                    GROUP BY v.CodViajante, v.Nombre
                    ORDER BY v.Nombre ASC
                """
                cursor.execute(sql_v)
                vendedores: List[Dict[str, Any]] = []
                for row in cursor.fetchall():
                    item = {
                        "id_vendedor": int(row[0]),
                        "nombre": (row[1] or "").strip(),
                        "cantidad": int(row[2] or 0),
                        "etiqueta": f"{(row[1] or '').strip()} (cod: {int(row[0])})",
                    }
                    if q:
                        hay = q in item["nombre"].lower() or q in str(item["id_vendedor"])
                        if not hay:
                            continue
                    vendedores.append(item)

                sql_sin = f"""
                    SELECT COUNT(*)
                    FROM {tbl_m}
                    WHERE {activo}
                      AND NOT EXISTS (
                        SELECT 1 FROM {tbl_a} a WHERE a.{meta['id_item']} = {tbl_m}.{pk}
                      )
                """
                cursor.execute(sql_sin)
                sin_row = cursor.fetchone()
                sin_asignar = int(sin_row[0] or 0) if sin_row else 0
                return True, "", vendedores, sin_asignar
            finally:
                cursor.close()
    except Exception as e:
        logger.exception("listar_resumen_vendedores: %s", e)
        return False, _mensaje_error_sql(e), [], 0


def listar_items_asignacion(
    base_empresa: str,
    modo: ModoAsignacion,
    *,
    id_vendedor: Optional[int] = None,
    filtro: str = "asignados",
    q: str = "",
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> Tuple[bool, str, List[Dict[str, Any]], int]:
    """
    Tabla paginada de clientes o marcas.

    ``filtro``: asignados | sin_asignar | todos
    ``id_vendedor``: requerido si filtro=asignados (excepto todos con q global)
    """
    try:
        meta = _meta(modo)
        tbl_a = meta["asignacion"]
        tbl_m = meta["maestro"]
        pk = meta["pk_maestro"]
        id_col = meta["id_item"]
        nombre_col = meta["nombre_col"]
        activo = meta["activo_where"]

        page = max(1, int(page))
        page_size = max(5, min(int(page_size), MAX_PAGE_SIZE))
        offset = (page - 1) * page_size
        filtro = (filtro or "asignados").strip().lower()
        q = (q or "").strip()

        where: List[str] = [activo]
        params: List[Any] = []
        joins = f"LEFT JOIN {tbl_a} a ON a.{id_col} = {tbl_m}.{pk} "
        joins += "LEFT JOIN viajantes v ON v.CodViajante = a.id_vendedor "

        if filtro == "sin_asignar":
            where.append(f"NOT EXISTS (SELECT 1 FROM {tbl_a} ax WHERE ax.{id_col} = {tbl_m}.{pk})")
        elif filtro == "asignados":
            if id_vendedor is None:
                return False, "vendedor_requerido", [], 0
            where.append("a.id_vendedor = %s")
            params.append(int(id_vendedor))
        elif filtro == "todos":
            if id_vendedor is not None:
                where.append("(a.id_vendedor = %s OR a.id IS NULL)")
                params.append(int(id_vendedor))
        else:
            return False, "filtro_invalido", [], 0

        if q:
            q_int = to_int_or_none(q)
            parts = []
            if q_int is not None:
                parts.append(f"{tbl_m}.{pk} = %s")
                params.append(q_int)
            like_parts = [f"{col} LIKE %s" for col in meta["busqueda_cols"]]
            parts.extend(like_parts)
            params.extend([f"%{q}%"] * len(like_parts))
            where.append("(" + " OR ".join(parts) + ")")

        where_sql = " AND ".join(where)
        sql_count = f"SELECT COUNT(*) FROM {tbl_m} {joins} WHERE {where_sql}"
        sql_data = f"""
            SELECT
                {tbl_m}.{pk} AS id_item,
                COALESCE({tbl_m}.{nombre_col}, '') AS nombre,
                a.id_vendedor AS id_vendedor,
                COALESCE(v.Nombre, '') AS nombre_vendedor,
                a.id AS id_asignacion
            FROM {tbl_m}
            {joins}
            WHERE {where_sql}
            ORDER BY {tbl_m}.{nombre_col} ASC
            LIMIT %s OFFSET %s
        """
        data_params = list(params) + [page_size, offset]

        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql_count, params)
                total_row = cursor.fetchone()
                total = int(total_row[0] or 0) if total_row else 0
                cursor.execute(sql_data, data_params)
                items = []
                for row in cursor.fetchall():
                    items.append(
                        {
                            "id_item": int(row[0]),
                            "nombre": (row[1] or "").strip(),
                            "id_vendedor": to_int_or_none(row[2]),
                            "nombre_vendedor": (row[3] or "").strip(),
                            "id_asignacion": to_int_or_none(row[4]),
                        }
                    )
                return True, "", items, total
            finally:
                cursor.close()
    except Exception as e:
        logger.exception("listar_items_asignacion: %s", e)
        return False, _mensaje_error_sql(e), [], 0


def asignar_items_bulk(
    base_empresa: str,
    modo: ModoAsignacion,
    ids_item: List[int],
    id_vendedor: Optional[int],
    sess_user: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, str, int]:
    """
    Asigna o desasigna ítems.

    ``id_vendedor`` None o 0 → elimina asignación (desasignar).
    Retorna cantidad de filas afectadas.
    """
    meta = _meta(modo)
    tbl_a = meta["asignacion"]
    id_col = meta["id_item"]
    tbl_m = meta["maestro"]
    pk = meta["pk_maestro"]
    activo = meta["activo_where"]

    ids = []
    for raw in ids_item:
        n = to_int_or_none(raw)
        if n is not None:
            ids.append(int(n))
    ids = list(dict.fromkeys(ids))
    if not ids:
        return False, "sin_items", 0

    vendedor = to_int_or_none(id_vendedor)
    usuario = _usuario_mod(sess_user)

    try:
        pool = get_mysql_pool()
        placeholders = ",".join(["%s"] * len(ids))
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    f"""
                    SELECT {pk} FROM {tbl_m}
                    WHERE {pk} IN ({placeholders}) AND {activo}
                    """,
                    ids,
                )
                valid = {int(r[0]) for r in cursor.fetchall()}
                if not valid:
                    return False, "items_no_validos", 0

                afectados = 0
                if not vendedor:
                    cursor.execute(
                        f"DELETE FROM {tbl_a} WHERE {id_col} IN ({placeholders})",
                        list(valid),
                    )
                    afectados = cursor.rowcount or 0
                else:
                    cursor.execute(
                        """
                        SELECT CodViajante FROM viajantes
                        WHERE CodViajante = %s AND COALESCE(anulado, 'No') = 'No'
                        LIMIT 1
                        """,
                        [vendedor],
                    )
                    if not cursor.fetchone():
                        return False, "vendedor_invalido", 0

                    for item_id in valid:
                        cursor.execute(
                            f"""
                            INSERT INTO {tbl_a} ({id_col}, id_vendedor, usuario_mod)
                            VALUES (%s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                                id_vendedor = VALUES(id_vendedor),
                                usuario_mod = VALUES(usuario_mod),
                                fecha_mod = CURRENT_TIMESTAMP
                            """,
                            [item_id, vendedor, usuario],
                        )
                        afectados += 1

                conn.commit()
                return True, "", afectados
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()
    except Exception as e:
        logger.exception("asignar_items_bulk: %s", e)
        return False, str(e), 0
