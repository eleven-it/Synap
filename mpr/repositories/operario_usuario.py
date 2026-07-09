"""Mapeo operario (sue_abm_empleado) <-> usuario de login (usuarios).

Tabla: mpr_operario_usuario. Un usuario de login resuelve a lo sumo un operario
(UNIQUE en id_usuario). Solo mapeos con activo=1 se consideran vigentes.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.utils.administranet_types import to_int_or_none

from mpr.db import mysql_cursor


def resolver_operario_por_usuario(base_empresa: str, id_usuario: int) -> Optional[int]:
    base = (base_empresa or "").strip()
    uid = to_int_or_none(id_usuario)
    if not base or uid is None:
        return None
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT id_operario FROM mpr_operario_usuario
            WHERE id_usuario = %s AND activo = 1
            LIMIT 1
            """,
            [uid],
        )
        row = cursor.fetchone()
        return to_int_or_none(row.get("id_operario")) if row else None


def map_operario_usuario(base_empresa: str, id_operario: int, id_usuario: int) -> None:
    """Upsert idempotente: un usuario -> un operario (UNIQUE id_usuario)."""
    base = (base_empresa or "").strip()
    with mysql_cursor(base) as cursor:
        cursor.execute(
            """
            INSERT INTO mpr_operario_usuario (id_operario, id_usuario, activo)
            VALUES (%s, %s, 1)
            ON DUPLICATE KEY UPDATE id_operario = VALUES(id_operario), activo = 1
            """,
            [int(id_operario), int(id_usuario)],
        )


def desmapear_usuario(base_empresa: str, id_usuario: int) -> int:
    """Desactiva el mapeo de un usuario. Devuelve filas afectadas."""
    base = (base_empresa or "").strip()
    with mysql_cursor(base) as cursor:
        cursor.execute(
            "UPDATE mpr_operario_usuario SET activo = 0 WHERE id_usuario = %s AND activo = 1",
            [int(id_usuario)],
        )
        return int(cursor.rowcount or 0)


def _tabla(cursor, nombre_lower: str) -> Optional[str]:
    cursor.execute("SHOW TABLES")
    for row in cursor.fetchall() or []:
        nombre = (list(row.values())[0] if isinstance(row, dict) else row[0]) or ""
        nombre = str(nombre).strip()
        if nombre.lower() == nombre_lower:
            return nombre
    return None


def listar_mapeos(base_empresa: str) -> List[Dict[str, Any]]:
    base = (base_empresa or "").strip()
    if not base:
        return []
    with mysql_cursor(base, dict_cursor=True) as cursor:
        emp = _tabla(cursor, "sue_abm_empleado")
        usr = _tabla(cursor, "usuarios")
        join_emp = f"LEFT JOIN `{emp}` e ON e.id_sue_abm_empleado = ou.id_operario" if emp else ""
        col_emp = "COALESCE(e.nombre_empleado, '')" if emp else "''"
        join_usr = f"LEFT JOIN `{usr}` u ON u.id_usuario = ou.id_usuario" if usr else ""
        col_usr = "COALESCE(u.cod_usuario, '')" if usr else "''"
        cursor.execute(
            f"""
            SELECT ou.id_mpr_operario_usuario, ou.id_operario, ou.id_usuario, ou.activo,
                   {col_emp} AS nombre_operario, {col_usr} AS cod_usuario
            FROM mpr_operario_usuario ou
            {join_emp}
            {join_usr}
            WHERE ou.activo = 1
            ORDER BY nombre_operario
            """
        )
        return [
            {
                "id": to_int_or_none(r.get("id_mpr_operario_usuario")),
                "id_operario": to_int_or_none(r.get("id_operario")),
                "id_usuario": to_int_or_none(r.get("id_usuario")),
                "nombre_operario": str(r.get("nombre_operario") or ""),
                "cod_usuario": str(r.get("cod_usuario") or ""),
                "activo": bool(r.get("activo", 1)),
            }
            for r in (cursor.fetchall() or [])
        ]


def listar_usuarios(base_empresa: str, limit: int = 1000) -> List[Dict[str, Any]]:
    """Lista usuarios de login (tabla `usuarios`) para el mapeo."""
    base = (base_empresa or "").strip()
    if not base:
        return []
    try:
        lim = max(1, min(int(limit or 1000), 5000))
    except (TypeError, ValueError):
        lim = 1000
    with mysql_cursor(base, dict_cursor=True) as cursor:
        usr = _tabla(cursor, "usuarios")
        if not usr:
            return []
        cursor.execute(
            f"""
            SELECT id_usuario, COALESCE(cod_usuario, '') AS cod_usuario,
                   TRIM(CONCAT(COALESCE(nombre_usuario, ''), ' ', COALESCE(apellido_usuario, ''))) AS nombre_completo
            FROM `{usr}`
            ORDER BY cod_usuario
            LIMIT %s
            """,
            [lim],
        )
        return [
            {
                "id_usuario": to_int_or_none(r.get("id_usuario")),
                "cod_usuario": str(r.get("cod_usuario") or ""),
                "nombre_completo": str(r.get("nombre_completo") or ""),
            }
            for r in (cursor.fetchall() or [])
            if r.get("id_usuario") is not None
        ]
