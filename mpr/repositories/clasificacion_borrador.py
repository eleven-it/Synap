"""Borrador de control de calidad MPR (precarga sin movimiento de stock).

Persiste cantidades semi / 2da / scrap por fecha, turno, artículo, operario y máquina.
No interviene en ``mpr_transicion_lote`` ni en MSTOCK hasta confirmar el CC.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from core.utils.administranet_types import to_decimal_or_none, to_int_or_none

from mpr.db import mysql_cursor

ClaveLineaBorrador = Tuple[int, int, int, int]


def _linea_tiene_cantidad(linea: Dict[str, Any]) -> bool:
    semi = to_decimal_or_none(linea.get("cant_semi")) or Decimal("0")
    seg2da = to_decimal_or_none(linea.get("cant_2da")) or Decimal("0")
    scrap = to_decimal_or_none(linea.get("cant_scrap")) or Decimal("0")
    return semi > 0 or seg2da > 0 or scrap > 0


def upsert_borrador(
    base_empresa: str,
    fecha: date,
    id_mpr_turno: int,
    id_usuario: int,
    lineas: List[Dict[str, Any]],
) -> None:
    """Upsert cabecera por (fecha, turno) y reemplaza líneas con qty > 0.

    Si no quedan líneas con cantidad, elimina el borrador completo.
    """
    base = (base_empresa or "").strip()
    tid = to_int_or_none(id_mpr_turno)
    uid = to_int_or_none(id_usuario)
    if not base or tid is None or uid is None:
        return

    lineas_validas: List[Dict[str, Any]] = []
    for ln in lineas or []:
        aid = to_int_or_none(ln.get("id_articulo"))
        oid = to_int_or_none(ln.get("id_operario"))
        if aid is None or oid is None or oid <= 0:
            continue
        mid = to_int_or_none(ln.get("id_mpr_maquina")) or 0
        payload = {
            "id_articulo": aid,
            "id_operario": oid,
            "id_mpr_maquina": mid,
            "cant_semi": to_decimal_or_none(ln.get("cant_semi")) or Decimal("0"),
            "cant_2da": to_decimal_or_none(ln.get("cant_2da")) or Decimal("0"),
            "cant_scrap": to_decimal_or_none(ln.get("cant_scrap")) or Decimal("0"),
        }
        if _linea_tiene_cantidad(payload):
            lineas_validas.append(payload)

    if not lineas_validas:
        eliminar_borrador(base, fecha, tid)
        return

    with mysql_cursor(base) as cursor:
        cursor.execute(
            """
            INSERT INTO mpr_clasificacion_borrador (fecha_produccion, id_mpr_turno, id_usuario)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                id_usuario = VALUES(id_usuario),
                actualizado_en = CURRENT_TIMESTAMP
            """,
            [fecha, tid, uid],
        )
        cursor.execute(
            """
            SELECT id_mpr_clasificacion_borrador
            FROM mpr_clasificacion_borrador
            WHERE fecha_produccion = %s AND id_mpr_turno = %s
            LIMIT 1
            """,
            [fecha, tid],
        )
        row = cursor.fetchone()
        if not row:
            return
        id_borrador = int(row[0])
        cursor.execute(
            "DELETE FROM mpr_clasificacion_borrador_linea WHERE id_mpr_clasificacion_borrador = %s",
            [id_borrador],
        )
        for ln in lineas_validas:
            cursor.execute(
                """
                INSERT INTO mpr_clasificacion_borrador_linea (
                    id_mpr_clasificacion_borrador, id_articulo, id_operario, id_mpr_maquina,
                    cant_semi, cant_2da, cant_scrap
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    id_borrador,
                    ln["id_articulo"],
                    ln["id_operario"],
                    ln["id_mpr_maquina"],
                    ln["cant_semi"],
                    ln["cant_2da"],
                    ln["cant_scrap"],
                ],
            )


def listar_lineas_borrador(
    base_empresa: str,
    fecha: date,
    id_mpr_turno: Optional[int] = None,
) -> Dict[ClaveLineaBorrador, Dict[str, Decimal]]:
    """Líneas del borrador indexadas por (id_mpr_maquina, id_articulo, id_operario, id_mpr_turno)."""
    base = (base_empresa or "").strip()
    if not base:
        return {}

    params: List[Any] = [fecha]
    filtro_turno = ""
    tid = to_int_or_none(id_mpr_turno)
    if tid is not None:
        filtro_turno = " AND b.id_mpr_turno = %s"
        params.append(tid)

    out: Dict[ClaveLineaBorrador, Dict[str, Decimal]] = {}
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            f"""
            SELECT b.id_mpr_turno, l.id_articulo, l.id_operario, l.id_mpr_maquina,
                   l.cant_semi, l.cant_2da, l.cant_scrap
            FROM mpr_clasificacion_borrador b
            INNER JOIN mpr_clasificacion_borrador_linea l
                ON l.id_mpr_clasificacion_borrador = b.id_mpr_clasificacion_borrador
            WHERE b.fecha_produccion = %s{filtro_turno}
            """,
            params,
        )
        for r in cursor.fetchall() or []:
            mid = to_int_or_none(r.get("id_mpr_maquina")) or 0
            aid = to_int_or_none(r.get("id_articulo"))
            oid = to_int_or_none(r.get("id_operario"))
            turno = to_int_or_none(r.get("id_mpr_turno"))
            if aid is None or oid is None or turno is None:
                continue
            out[(mid, aid, oid, turno)] = {
                "semi": to_decimal_or_none(r.get("cant_semi")) or Decimal("0"),
                "segunda": to_decimal_or_none(r.get("cant_2da")) or Decimal("0"),
                "scrap": to_decimal_or_none(r.get("cant_scrap")) or Decimal("0"),
            }
    return out


def eliminar_borrador(
    base_empresa: str,
    fecha: date,
    id_mpr_turno: int,
) -> None:
    """Elimina cabecera (cascade líneas) para fecha+turno."""
    base = (base_empresa or "").strip()
    tid = to_int_or_none(id_mpr_turno)
    if not base or tid is None:
        return
    with mysql_cursor(base) as cursor:
        cursor.execute(
            """
            DELETE FROM mpr_clasificacion_borrador
            WHERE fecha_produccion = %s AND id_mpr_turno = %s
            """,
            [fecha, tid],
        )


def tiene_borrador(
    base_empresa: str,
    fecha: date,
    id_mpr_turno: Optional[int] = None,
) -> bool:
    """Indica si existe borrador para la fecha (opcionalmente filtrado por turno)."""
    base = (base_empresa or "").strip()
    if not base:
        return False

    params: List[Any] = [fecha]
    filtro_turno = ""
    tid = to_int_or_none(id_mpr_turno)
    if tid is not None:
        filtro_turno = " AND id_mpr_turno = %s"
        params.append(tid)

    with mysql_cursor(base) as cursor:
        cursor.execute(
            f"""
            SELECT 1 FROM mpr_clasificacion_borrador
            WHERE fecha_produccion = %s{filtro_turno}
            LIMIT 1
            """,
            params,
        )
        return cursor.fetchone() is not None
