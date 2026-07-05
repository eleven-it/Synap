"""Imputación armado 1ra (mpr_imputacion_armado)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.utils.administranet_types import str_or_default, to_int_or_none

from mpr.db import mysql_cursor


def sum_cantidad_imputada(base_empresa: str, codigo_movimiento: int) -> int:
    base = (base_empresa or "").strip()
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT COALESCE(SUM(cantidad), 0) AS total
            FROM mpr_imputacion_armado
            WHERE codigo_movimiento = %s
            """,
            [int(codigo_movimiento)],
        )
        row = cursor.fetchone()
        return int(row.get("total") or 0) if row else 0


def sum_imputado_por_pedido_pack(
    base_empresa: str,
    codigo_movimiento_pedido: int,
    id_articulo_pack: int,
) -> int:
    """Suma imputaciones previas de un pack en un pedido PED (ledger mpr_imputacion_armado)."""
    base = (base_empresa or "").strip()
    if not base or not codigo_movimiento_pedido or not id_articulo_pack:
        return 0
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT COALESCE(SUM(cantidad), 0) AS total
            FROM mpr_imputacion_armado
            WHERE codigo_movimiento_pedido = %s AND id_articulo_pack = %s
            """,
            [int(codigo_movimiento_pedido), int(id_articulo_pack)],
        )
        row = cursor.fetchone()
        return int(row.get("total") or 0) if row else 0


def crear_imputacion(
    base_empresa: str,
    codigo_movimiento: int,
    id_articulo_pack: int,
    cantidad: int,
    codigo_movimiento_pedido: int,
    origen_regla: str,
    id_usuario_supervisor: int,
    *,
    id_lista_detalle: Optional[int] = None,
    notas: str = "",
) -> int:
    base = (base_empresa or "").strip()
    with mysql_cursor(base) as cursor:
        cursor.execute(
            """
            INSERT INTO mpr_imputacion_armado
                (codigo_movimiento, id_articulo_pack, cantidad, codigo_movimiento_pedido,
                 id_lista_detalle, origen_regla, id_usuario_supervisor, notas)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                int(codigo_movimiento),
                int(id_articulo_pack),
                int(cantidad),
                int(codigo_movimiento_pedido),
                to_int_or_none(id_lista_detalle),
                str(origen_regla),
                int(id_usuario_supervisor),
                str_or_default(notas, "")[:500],
            ],
        )
        return int(cursor.lastrowid)


def listar_por_codigos_movimiento(
    base_empresa: str,
    codigos: List[int],
) -> List[Dict[str, Any]]:
    base = (base_empresa or "").strip()
    if not codigos:
        return []
    placeholders = ",".join(["%s"] * len(codigos))
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            f"""
            SELECT codigo_movimiento, cantidad, codigo_movimiento_pedido,
                   id_usuario_supervisor, imputado_en
            FROM mpr_imputacion_armado
            WHERE codigo_movimiento IN ({placeholders})
            ORDER BY imputado_en
            """,
            codigos,
        )
        rows = cursor.fetchall() or []
    out: List[Dict[str, Any]] = []
    for row in rows:
        imp = row.get("imputado_en")
        if not isinstance(imp, datetime):
            imp = datetime.now()
        out.append({
            "codigo_movimiento": int(row["codigo_movimiento"]),
            "cantidad": int(row.get("cantidad") or 0),
            "codigo_movimiento_pedido": int(row["codigo_movimiento_pedido"]),
            "id_usuario_supervisor": int(row.get("id_usuario_supervisor") or 0),
            "imputado_en": imp,
        })
    return out
