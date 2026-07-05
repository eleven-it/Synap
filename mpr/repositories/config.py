"""Configuración MPR singleton (mpr_config)."""
from typing import Any, Dict, Optional, Tuple

from mpr.db import mysql_cursor


def obtener_config(base_empresa: str) -> Dict[str, Any]:
    base = (base_empresa or "").strip()
    if not base:
        return {"bloquear_parte_supera_fabricando": True}

    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT bloquear_parte_supera_fabricando
            FROM mpr_config
            ORDER BY id_mpr_config
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if not row:
            return {"bloquear_parte_supera_fabricando": True}
        return {
            "bloquear_parte_supera_fabricando": bool(
                row.get("bloquear_parte_supera_fabricando", 1)
            ),
        }


def actualizar_bloqueo_fabricando(
    base_empresa: str,
    bloquear: bool,
) -> Tuple[bool, Optional[str]]:
    base = (base_empresa or "").strip()
    if not base:
        return False, "Empresa inválida."

    flag = 1 if bloquear else 0
    with mysql_cursor(base) as cursor:
        cursor.execute("SELECT COUNT(*) FROM mpr_config")
        count = (cursor.fetchone() or [0])[0]
        if count:
            cursor.execute(
                """
                UPDATE mpr_config
                SET bloquear_parte_supera_fabricando = %s
                ORDER BY id_mpr_config
                LIMIT 1
                """,
                [flag],
            )
        else:
            cursor.execute(
                """
                INSERT INTO mpr_config (bloquear_parte_supera_fabricando)
                VALUES (%s)
                """,
                [flag],
            )
    return True, None
