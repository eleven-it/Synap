"""
Utilidades compartidas para comprobaciones de esquema MySQL (AdministraNET legacy).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def columna_existe(cursor, tabla: str, columna: str) -> bool:
    sql = "SHOW COLUMNS FROM `%s` LIKE %%s" % tabla.replace("`", "``")
    cursor.execute(sql, (columna,))
    return cursor.fetchone() is not None


def nombre_tabla_real(cursor, nombre_lower: str) -> Optional[str]:
    cursor.execute("SHOW TABLES")
    for row in cursor.fetchall():
        nombre = (row[0] if row else "").strip() if hasattr(row[0], "strip") else str(row[0] or "").strip()
        if nombre and nombre.lower() == nombre_lower:
            return nombre
    return None


def indice_existe(cursor, tabla: str, indice: str) -> bool:
    cursor.execute(
        "SHOW INDEX FROM `{}` WHERE Key_name = %s".format(tabla.replace("`", "``")),
        (indice,),
    )
    return cursor.fetchone() is not None


def fk_existe(cursor, tabla: str, fk_name: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM information_schema.TABLE_CONSTRAINTS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND CONSTRAINT_NAME = %s AND CONSTRAINT_TYPE = 'FOREIGN KEY'",
        (tabla, fk_name),
    )
    return cursor.fetchone() is not None


def resultado_vacio() -> Dict[str, Any]:
    return {
        "success": True,
        "message": "",
        "migrations_applied": [],
        "migrations_failed": [],
    }


def merge_resultados(
    base: Dict[str, Any],
    otro: Dict[str, Any],
) -> Dict[str, Any]:
    base["migrations_applied"].extend(otro.get("migrations_applied") or [])
    base["migrations_failed"].extend(otro.get("migrations_failed") or [])
    if not otro.get("success", True):
        base["success"] = False
    return base


def mensaje_final(applied: List[str], failed: List[str]) -> str:
    if applied and not failed:
        return "Migraciones aplicadas: " + ", ".join(applied)
    if applied and failed:
        return (
            "Aplicadas: "
            + ", ".join(applied)
            + ". Fallidas: "
            + "; ".join(failed)
        )
    if failed:
        return "Migraciones fallidas: " + "; ".join(failed)
    return "La estructura está actualizada. No se requirieron cambios."
