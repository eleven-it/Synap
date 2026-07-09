"""Línea habitual del operario, versionada (mpr_operario_linea).

Vigencia half-open [vigencia_desde, vigencia_hasta): a lo sumo una línea
habitual vigente por operario en una fecha dada.
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


def linea_habitual_vigente(base_empresa: str, id_operario: int, fecha: date) -> Optional[int]:
    base = (base_empresa or "").strip()
    oid = to_int_or_none(id_operario)
    if not base or oid is None:
        return None
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT id_mpr_linea FROM mpr_operario_linea
            WHERE id_operario = %s
              AND vigencia_desde <= %s
              AND (vigencia_hasta IS NULL OR vigencia_hasta > %s)
            ORDER BY vigencia_desde DESC
            LIMIT 1
            """,
            [oid, fecha, fecha],
        )
        row = cursor.fetchone()
        return to_int_or_none(row.get("id_mpr_linea")) if row else None


def set_linea_habitual(base_empresa: str, id_operario: int, id_linea: int, desde: date) -> None:
    """Cierra la habitual vigente e inserta la nueva a partir de `desde`."""
    base = (base_empresa or "").strip()
    oid = int(id_operario)
    lid = int(id_linea)
    with mysql_cursor(base) as cursor:
        cursor.execute(
            """
            UPDATE mpr_operario_linea
            SET vigencia_hasta = %s
            WHERE id_operario = %s AND vigencia_hasta IS NULL
            """,
            [desde, oid],
        )
        cursor.execute(
            """
            INSERT INTO mpr_operario_linea (id_operario, id_mpr_linea, vigencia_desde, vigencia_hasta)
            VALUES (%s, %s, %s, NULL)
            """,
            [oid, lid, desde],
        )


def listar_historico(base_empresa: str, id_operario: int) -> List[Dict[str, Any]]:
    base = (base_empresa or "").strip()
    oid = to_int_or_none(id_operario)
    if not base or oid is None:
        return []
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT ol.id_mpr_linea, l.nombre AS linea_nombre,
                   ol.vigencia_desde, ol.vigencia_hasta
            FROM mpr_operario_linea ol
            LEFT JOIN mpr_linea l ON l.id_mpr_linea = ol.id_mpr_linea
            WHERE ol.id_operario = %s
            ORDER BY ol.vigencia_desde DESC, ol.id_mpr_operario_linea DESC
            """,
            [oid],
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


def lineas_habituales_vigentes(base_empresa: str, fecha: date) -> Dict[int, int]:
    """Mapa id_operario -> id_linea habitual vigente a `fecha` (para listados)."""
    base = (base_empresa or "").strip()
    if not base:
        return {}
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT id_operario, id_mpr_linea FROM mpr_operario_linea
            WHERE vigencia_desde <= %s
              AND (vigencia_hasta IS NULL OR vigencia_hasta > %s)
            """,
            [fecha, fecha],
        )
        out: Dict[int, int] = {}
        for r in cursor.fetchall() or []:
            oid = to_int_or_none(r.get("id_operario"))
            lid = to_int_or_none(r.get("id_mpr_linea"))
            if oid is not None and lid is not None:
                out[oid] = lid
        return out
