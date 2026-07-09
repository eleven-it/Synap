"""Catálogos de máquinas y líneas MPR y su pertenencia versionada.

Tablas: mpr_linea, mpr_maquina, mpr_maquina_linea (una BD = una empresa).
Vigencia half-open [vigencia_desde, vigencia_hasta): vigente(fecha) si
vigencia_desde <= fecha AND (vigencia_hasta IS NULL OR vigencia_hasta > fecha).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from core.utils.administranet_types import to_int_or_none

from mpr.db import mysql_cursor


def _as_date(value: Any) -> Optional[date]:
    """Normaliza un valor DATE de MySQL a objeto date (para filtros de plantilla)."""
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


# --------------------------------------------------------------------------- #
# Líneas
# --------------------------------------------------------------------------- #
def listar_lineas(base_empresa: str, solo_activas: bool = False) -> List[Dict[str, Any]]:
    base = (base_empresa or "").strip()
    if not base:
        return []
    sql = "SELECT id_mpr_linea, nombre, activo FROM mpr_linea"
    if solo_activas:
        sql += " WHERE activo = 1"
    sql += " ORDER BY nombre"
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(sql)
        out: List[Dict[str, Any]] = []
        for row in cursor.fetchall() or []:
            lid = to_int_or_none(row.get("id_mpr_linea"))
            if lid is None:
                continue
            out.append(
                {
                    "id": lid,
                    "nombre": str(row.get("nombre") or ""),
                    "activo": bool(row.get("activo", 1)),
                }
            )
        return out


def obtener_linea(base_empresa: str, id_linea: int) -> Optional[Dict[str, Any]]:
    base = (base_empresa or "").strip()
    lid = to_int_or_none(id_linea)
    if not base or lid is None:
        return None
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            "SELECT id_mpr_linea, nombre, activo FROM mpr_linea WHERE id_mpr_linea = %s",
            [lid],
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": int(row["id_mpr_linea"]),
            "nombre": str(row.get("nombre") or ""),
            "activo": bool(row.get("activo", 1)),
        }


def crear_linea(base_empresa: str, nombre: str) -> int:
    base = (base_empresa or "").strip()
    with mysql_cursor(base) as cursor:
        cursor.execute(
            "INSERT INTO mpr_linea (nombre, activo) VALUES (%s, 1)",
            [nombre.strip()],
        )
        return int(cursor.lastrowid)


def actualizar_linea(base_empresa: str, id_linea: int, nombre: str) -> None:
    base = (base_empresa or "").strip()
    with mysql_cursor(base) as cursor:
        cursor.execute(
            "UPDATE mpr_linea SET nombre = %s WHERE id_mpr_linea = %s",
            [nombre.strip(), int(id_linea)],
        )


def toggle_linea_activa(base_empresa: str, id_linea: int, activa: bool) -> None:
    base = (base_empresa or "").strip()
    with mysql_cursor(base) as cursor:
        cursor.execute(
            "UPDATE mpr_linea SET activo = %s WHERE id_mpr_linea = %s",
            [1 if activa else 0, int(id_linea)],
        )


# --------------------------------------------------------------------------- #
# Máquinas
# --------------------------------------------------------------------------- #
def listar_maquinas(base_empresa: str, solo_activas: bool = False) -> List[Dict[str, Any]]:
    """Máquinas con su línea vigente (LEFT JOIN a mpr_maquina_linea vigente)."""
    base = (base_empresa or "").strip()
    if not base:
        return []
    sql = """
        SELECT m.id_mpr_maquina, m.codigo, m.nombre, m.activo,
               ml.id_mpr_linea AS id_linea_actual, l.nombre AS linea_actual_nombre
        FROM mpr_maquina m
        LEFT JOIN mpr_maquina_linea ml
            ON ml.id_mpr_maquina = m.id_mpr_maquina AND ml.vigencia_hasta IS NULL
        LEFT JOIN mpr_linea l ON l.id_mpr_linea = ml.id_mpr_linea
    """
    if solo_activas:
        sql += " WHERE m.activo = 1"
    sql += " ORDER BY m.codigo"
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(sql)
        out: List[Dict[str, Any]] = []
        for row in cursor.fetchall() or []:
            mid = to_int_or_none(row.get("id_mpr_maquina"))
            if mid is None:
                continue
            out.append(
                {
                    "id": mid,
                    "codigo": str(row.get("codigo") or ""),
                    "nombre": str(row.get("nombre") or ""),
                    "activo": bool(row.get("activo", 1)),
                    "id_linea_actual": to_int_or_none(row.get("id_linea_actual")),
                    "linea_actual_nombre": str(row.get("linea_actual_nombre") or ""),
                }
            )
        return out


def obtener_maquina(base_empresa: str, id_maquina: int) -> Optional[Dict[str, Any]]:
    base = (base_empresa or "").strip()
    mid = to_int_or_none(id_maquina)
    if not base or mid is None:
        return None
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            "SELECT id_mpr_maquina, codigo, nombre, activo FROM mpr_maquina WHERE id_mpr_maquina = %s",
            [mid],
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": int(row["id_mpr_maquina"]),
            "codigo": str(row.get("codigo") or ""),
            "nombre": str(row.get("nombre") or ""),
            "activo": bool(row.get("activo", 1)),
        }


def crear_maquina(base_empresa: str, codigo: str, nombre: str) -> int:
    base = (base_empresa or "").strip()
    with mysql_cursor(base) as cursor:
        cursor.execute(
            "INSERT INTO mpr_maquina (codigo, nombre, activo) VALUES (%s, %s, 1)",
            [codigo.strip(), (nombre or "").strip() or None],
        )
        return int(cursor.lastrowid)


def actualizar_maquina(base_empresa: str, id_maquina: int, codigo: str, nombre: str) -> None:
    base = (base_empresa or "").strip()
    with mysql_cursor(base) as cursor:
        cursor.execute(
            "UPDATE mpr_maquina SET codigo = %s, nombre = %s WHERE id_mpr_maquina = %s",
            [codigo.strip(), (nombre or "").strip() or None, int(id_maquina)],
        )


def toggle_maquina_activa(base_empresa: str, id_maquina: int, activa: bool) -> None:
    base = (base_empresa or "").strip()
    with mysql_cursor(base) as cursor:
        cursor.execute(
            "UPDATE mpr_maquina SET activo = %s WHERE id_mpr_maquina = %s",
            [1 if activa else 0, int(id_maquina)],
        )


# --------------------------------------------------------------------------- #
# Pertenencia máquina->línea (versionada)
# --------------------------------------------------------------------------- #
def linea_vigente_de_maquina(
    base_empresa: str, id_maquina: int, fecha: date
) -> Optional[int]:
    base = (base_empresa or "").strip()
    mid = to_int_or_none(id_maquina)
    if not base or mid is None:
        return None
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT id_mpr_linea FROM mpr_maquina_linea
            WHERE id_mpr_maquina = %s
              AND vigencia_desde <= %s
              AND (vigencia_hasta IS NULL OR vigencia_hasta > %s)
            ORDER BY vigencia_desde DESC
            LIMIT 1
            """,
            [mid, fecha, fecha],
        )
        row = cursor.fetchone()
        return to_int_or_none(row.get("id_mpr_linea")) if row else None


def maquinas_de_linea(base_empresa: str, id_linea: int, fecha: date) -> List[Dict[str, Any]]:
    """Máquinas cuya pertenencia vigente a `fecha` es la línea dada."""
    base = (base_empresa or "").strip()
    lid = to_int_or_none(id_linea)
    if not base or lid is None:
        return []
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT m.id_mpr_maquina, m.codigo, m.nombre
            FROM mpr_maquina_linea ml
            INNER JOIN mpr_maquina m ON m.id_mpr_maquina = ml.id_mpr_maquina
            WHERE ml.id_mpr_linea = %s
              AND ml.vigencia_desde <= %s
              AND (ml.vigencia_hasta IS NULL OR ml.vigencia_hasta > %s)
              AND m.activo = 1
            ORDER BY m.codigo
            """,
            [lid, fecha, fecha],
        )
        return [
            {
                "id": int(r["id_mpr_maquina"]),
                "codigo": str(r.get("codigo") or ""),
                "nombre": str(r.get("nombre") or ""),
            }
            for r in (cursor.fetchall() or [])
            if r.get("id_mpr_maquina") is not None
        ]


def asignar_maquina_linea(
    base_empresa: str, id_maquina: int, id_linea: int, desde: date
) -> None:
    """Cierra la vigencia previa (si existe) e inserta la nueva pertenencia vigente."""
    base = (base_empresa or "").strip()
    mid = int(id_maquina)
    lid = int(id_linea)
    with mysql_cursor(base) as cursor:
        # Cerrar cualquier pertenencia vigente de la máquina en la fecha de corte
        cursor.execute(
            """
            UPDATE mpr_maquina_linea
            SET vigencia_hasta = %s
            WHERE id_mpr_maquina = %s AND vigencia_hasta IS NULL
            """,
            [desde, mid],
        )
        cursor.execute(
            """
            INSERT INTO mpr_maquina_linea (id_mpr_maquina, id_mpr_linea, vigencia_desde, vigencia_hasta)
            VALUES (%s, %s, %s, NULL)
            """,
            [mid, lid, desde],
        )


def listar_historico_maquina_linea(
    base_empresa: str, id_maquina: int
) -> List[Dict[str, Any]]:
    base = (base_empresa or "").strip()
    mid = to_int_or_none(id_maquina)
    if not base or mid is None:
        return []
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT ml.id_mpr_linea, l.nombre AS linea_nombre,
                   ml.vigencia_desde, ml.vigencia_hasta
            FROM mpr_maquina_linea ml
            LEFT JOIN mpr_linea l ON l.id_mpr_linea = ml.id_mpr_linea
            WHERE ml.id_mpr_maquina = %s
            ORDER BY ml.vigencia_desde DESC, ml.id_mpr_maquina_linea DESC
            """,
            [mid],
        )
        return [
            {
                "id_linea": to_int_or_none(r.get("id_mpr_linea")),
                "linea_nombre": str(r.get("linea_nombre") or ""),
                "vigencia_desde": _as_date(r.get("vigencia_desde")),
                "vigencia_hasta": _as_date(r.get("vigencia_hasta")),
            }
            for r in (cursor.fetchall() or [])
        ]
