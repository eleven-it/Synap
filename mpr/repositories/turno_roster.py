"""Turnos y roster MPR (mpr_turno, mpr_roster_dia)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from core.utils.administranet_types import to_date_or_none, to_int_or_none

from mpr.db import mysql_cursor
from mpr.repositories.records import TurnoRecord, _coerce_time


def _row_to_turno(base_empresa: str, row: Dict[str, Any]) -> TurnoRecord:
    return TurnoRecord(
        id_mpr_turno=int(row["id_mpr_turno"]),
        nombre=str(row.get("nombre") or ""),
        hora_inicio=row.get("hora_inicio"),
        hora_fin=row.get("hora_fin"),
        activo=bool(row.get("activo", 1)),
        base_empresa=base_empresa,
    )


def listar_turnos_dict(
    base_empresa: str,
    solo_activos: bool = True,
) -> List[Dict[str, Any]]:
    base = (base_empresa or "").strip()
    if not base:
        return []
    sql = """
        SELECT id_mpr_turno, nombre, hora_inicio, hora_fin, activo
        FROM mpr_turno
    """
    params: List[Any] = []
    if solo_activos:
        sql += " WHERE activo = 1"
    sql += " ORDER BY nombre"
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(sql, params)
        out: List[Dict[str, Any]] = []
        for row in cursor.fetchall() or []:
            tid = to_int_or_none(row.get("id_mpr_turno"))
            if tid is None:
                continue
            hi = _coerce_time(row.get("hora_inicio"))
            hf = _coerce_time(row.get("hora_fin"))
            out.append({
                "id": tid,
                "nombre": str(row.get("nombre") or ""),
                "hora_inicio": hi.strftime("%H:%M"),
                "hora_fin": hf.strftime("%H:%M"),
                "activo": bool(row.get("activo", 1)),
            })
        return out


def obtener_turno_record(
    base_empresa: str,
    id_turno: int,
) -> Optional[TurnoRecord]:
    base = (base_empresa or "").strip()
    tid = to_int_or_none(id_turno)
    if not base or tid is None:
        return None
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT id_mpr_turno, nombre, hora_inicio, hora_fin, activo
            FROM mpr_turno WHERE id_mpr_turno = %s
            """,
            [tid],
        )
        row = cursor.fetchone()
        if not row:
            return None
        return _row_to_turno(base, row)


def crear_turno_mysql(
    base_empresa: str,
    nombre: str,
    hora_inicio: Any,
    hora_fin: Any,
) -> int:
    base = (base_empresa or "").strip()
    hi = _coerce_time(hora_inicio)
    hf = _coerce_time(hora_fin)
    with mysql_cursor(base) as cursor:
        cursor.execute(
            """
            INSERT INTO mpr_turno (nombre, hora_inicio, hora_fin, activo)
            VALUES (%s, %s, %s, 1)
            """,
            [nombre.strip(), hi, hf],
        )
        return int(cursor.lastrowid)


def guardar_turno_record(
    base_empresa: str,
    turno: TurnoRecord,
    update_fields=None,
) -> None:
    base = (base_empresa or "").strip()
    fields = set(update_fields or ["nombre", "hora_inicio", "hora_fin", "activo"])
    sets: List[str] = []
    params: List[Any] = []
    if "nombre" in fields:
        sets.append("nombre = %s")
        params.append(turno.nombre)
    if "hora_inicio" in fields:
        sets.append("hora_inicio = %s")
        params.append(turno.hora_inicio)
    if "hora_fin" in fields:
        sets.append("hora_fin = %s")
        params.append(turno.hora_fin)
    if "activo" in fields:
        sets.append("activo = %s")
        params.append(1 if turno.activo else 0)
    if not sets:
        return
    params.append(turno.id_mpr_turno)
    with mysql_cursor(base) as cursor:
        cursor.execute(
            f"UPDATE mpr_turno SET {', '.join(sets)} WHERE id_mpr_turno = %s",
            params,
        )


def toggle_turno_activo_mysql(
    base_empresa: str,
    id_turno: int,
    activo: bool,
) -> None:
    base = (base_empresa or "").strip()
    with mysql_cursor(base) as cursor:
        cursor.execute(
            "UPDATE mpr_turno SET activo = %s WHERE id_mpr_turno = %s",
            [1 if activo else 0, int(id_turno)],
        )


def listar_roster_rango(
    base_empresa: str,
    fecha_desde: date,
    fecha_hasta: date,
) -> List[Dict[str, Any]]:
    base = (base_empresa or "").strip()
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT r.fecha, r.id_operario, r.id_mpr_turno, t.nombre AS nombre_turno,
                   r.id_mpr_linea, l.nombre AS nombre_linea
            FROM mpr_roster_dia r
            INNER JOIN mpr_turno t ON t.id_mpr_turno = r.id_mpr_turno
            LEFT JOIN mpr_linea l ON l.id_mpr_linea = r.id_mpr_linea
            WHERE r.fecha >= %s AND r.fecha <= %s
            ORDER BY r.fecha, r.id_operario
            """,
            [fecha_desde, fecha_hasta],
        )
        return list(cursor.fetchall() or [])


def listar_operarios_roster_dia_turno(
    base_empresa: str,
    fecha: date,
    id_mpr_turno: int,
) -> List[int]:
    base = (base_empresa or "").strip()
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT id_operario FROM mpr_roster_dia
            WHERE fecha = %s AND id_mpr_turno = %s
            ORDER BY id_operario
            """,
            [fecha, int(id_mpr_turno)],
        )
        return [
            int(r["id_operario"])
            for r in (cursor.fetchall() or [])
            if r.get("id_operario") is not None
        ]


def upsert_roster(
    base_empresa: str,
    fecha: date,
    id_operario: int,
    id_mpr_turno: int,
    id_mpr_linea: Optional[int] = None,
) -> None:
    """Alta/actualización de la asignación diaria por (fecha, operario, turno).

    ``id_mpr_linea`` es override opcional: si el INSERT trae NULL, en conflicto
    se conserva el valor existente (COALESCE). Para limpiar override usar
    ``update_roster_linea(..., id_mpr_linea=None)``.
    """
    base = (base_empresa or "").strip()
    linea = to_int_or_none(id_mpr_linea)
    with mysql_cursor(base) as cursor:
        cursor.execute(
            """
            INSERT INTO mpr_roster_dia (fecha, id_operario, id_mpr_turno, id_mpr_linea)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                id_mpr_linea = IF(
                    VALUES(id_mpr_linea) IS NOT NULL,
                    VALUES(id_mpr_linea),
                    id_mpr_linea
                )
            """,
            [fecha, int(id_operario), int(id_mpr_turno), linea],
        )


def turnos_del_operario_dia(
    base_empresa: str,
    id_operario: int,
    fecha: date,
) -> List[int]:
    """Lista de ``id_mpr_turno`` asignados al operario en ``fecha`` (orden estable)."""
    base = (base_empresa or "").strip()
    oid = to_int_or_none(id_operario)
    if not base or oid is None:
        return []
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT id_mpr_turno FROM mpr_roster_dia
            WHERE fecha = %s AND id_operario = %s
            ORDER BY id_mpr_turno
            """,
            [fecha, oid],
        )
        out: List[int] = []
        for row in cursor.fetchall() or []:
            tid = to_int_or_none(row.get("id_mpr_turno"))
            if tid is not None:
                out.append(tid)
        return out


def turno_del_operario_dia(
    base_empresa: str,
    id_operario: int,
    fecha: date,
) -> Optional[int]:
    """Compat transitoria: primer turno del día o None. Preferir ``turnos_del_operario_dia``."""
    turnos = turnos_del_operario_dia(base_empresa, id_operario, fecha)
    return turnos[0] if turnos else None


def roster_turno_asignado(
    base_empresa: str,
    fecha: date,
    id_operario: int,
    id_mpr_turno: int,
) -> bool:
    """Indica si el operario tiene ese turno asignado en la fecha."""
    tid = to_int_or_none(id_mpr_turno)
    if tid is None:
        return False
    return tid in turnos_del_operario_dia(base_empresa, id_operario, fecha)


def override_linea_roster(
    base_empresa: str,
    fecha: date,
    id_operario: int,
    id_mpr_turno: Optional[int] = None,
) -> Optional[int]:
    """Override de línea del roster para fecha+operario (+ turno si se indica).

    Con ``id_mpr_turno=None`` mantiene comportamiento legacy (LIMIT 1) para
    callers que aún no pasan turno.
    """
    base = (base_empresa or "").strip()
    oid = to_int_or_none(id_operario)
    tid = to_int_or_none(id_mpr_turno)
    if not base or oid is None:
        return None
    sql = """
        SELECT id_mpr_linea FROM mpr_roster_dia
        WHERE fecha = %s AND id_operario = %s
    """
    params: List[Any] = [fecha, oid]
    if tid is not None:
        sql += " AND id_mpr_turno = %s"
        params.append(tid)
    sql += " LIMIT 1"
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return to_int_or_none(row.get("id_mpr_linea")) if row else None


def update_roster_linea(
    base_empresa: str,
    fecha: date,
    id_operario: int,
    id_mpr_turno: int,
    id_mpr_linea: Optional[int],
) -> int:
    """Actualiza explícitamente ``id_mpr_linea`` (NULL permitido = quitar override)."""
    base = (base_empresa or "").strip()
    linea = to_int_or_none(id_mpr_linea)
    with mysql_cursor(base) as cursor:
        cursor.execute(
            """
            UPDATE mpr_roster_dia
            SET id_mpr_linea = %s
            WHERE fecha = %s AND id_operario = %s AND id_mpr_turno = %s
            """,
            [linea, fecha, int(id_operario), int(id_mpr_turno)],
        )
        return int(cursor.rowcount or 0)


def eliminar_roster_turno(
    base_empresa: str,
    fecha: date,
    id_operario: int,
    id_turno: int,
) -> int:
    """Elimina la asignación de un turno concreto (fecha + operario + turno)."""
    base = (base_empresa or "").strip()
    with mysql_cursor(base) as cursor:
        cursor.execute(
            """
            DELETE FROM mpr_roster_dia
            WHERE fecha = %s AND id_operario = %s AND id_mpr_turno = %s
            """,
            [fecha, int(id_operario), int(id_turno)],
        )
        return int(cursor.rowcount or 0)


def eliminar_roster(
    base_empresa: str,
    fecha: date,
    id_operario: int,
) -> int:
    """Elimina **todos** los turnos del operario en esa fecha. Preferir ``eliminar_roster_turno``."""
    base = (base_empresa or "").strip()
    with mysql_cursor(base) as cursor:
        cursor.execute(
            """
            DELETE FROM mpr_roster_dia
            WHERE fecha = %s AND id_operario = %s
            """,
            [fecha, int(id_operario)],
        )
        return int(cursor.rowcount or 0)
