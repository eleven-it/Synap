"""Transiciones entre etapas MPR (mpr_transicion_lote)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.utils.administranet_types import to_decimal_or_none, to_int_or_none

from mpr.db import mysql_cursor


def crear_transicion_lote(
    base_empresa: str,
    id_articulo: int,
    tipo_origen: str,
    tipo_destino: str,
    cantidad: Decimal,
    codigo_movimiento: Optional[int],
    id_usuario: int,
) -> int:
    base = (base_empresa or "").strip()
    qty = to_decimal_or_none(cantidad) or Decimal("0")
    with mysql_cursor(base) as cursor:
        cursor.execute(
            """
            INSERT INTO mpr_transicion_lote
                (id_articulo, tipo_origen, tipo_destino, cantidad, codigo_movimiento, id_usuario)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            [
                int(id_articulo),
                str(tipo_origen),
                str(tipo_destino),
                qty,
                to_int_or_none(codigo_movimiento),
                int(id_usuario),
            ],
        )
        return int(cursor.lastrowid)


def listar_por_articulo(
    base_empresa: str,
    id_articulo: int,
) -> List[Dict[str, Any]]:
    base = (base_empresa or "").strip()
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT id_mpr_transicion_lote, id_articulo, tipo_origen, tipo_destino,
                   cantidad, codigo_movimiento, id_usuario, creado_en
            FROM mpr_transicion_lote
            WHERE id_articulo = %s
            ORDER BY creado_en
            """,
            [int(id_articulo)],
        )
        rows = cursor.fetchall() or []
    out: List[Dict[str, Any]] = []
    for row in rows:
        creado = row.get("creado_en")
        if isinstance(creado, str):
            try:
                creado = datetime.fromisoformat(creado.replace("Z", "+00:00"))
            except ValueError:
                creado = datetime.now()
        out.append({
            "id": int(row["id_mpr_transicion_lote"]),
            "id_articulo": int(row["id_articulo"]),
            "tipo_origen": str(row.get("tipo_origen") or ""),
            "tipo_destino": str(row.get("tipo_destino") or ""),
            "cantidad": to_decimal_or_none(row.get("cantidad")) or Decimal("0"),
            "codigo_movimiento": to_int_or_none(row.get("codigo_movimiento")),
            "id_usuario": int(row.get("id_usuario") or 0),
            "creado_en": creado or datetime.now(),
        })
    return out
