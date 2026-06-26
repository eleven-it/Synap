"""
Utilidades compartidas para comprobaciones de esquema MySQL (AdministraNET legacy).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


def columna_existe(cursor, tabla: str, columna: str) -> bool:
    sql = "SHOW COLUMNS FROM `%s` LIKE %%s" % tabla.replace("`", "``")
    cursor.execute(sql, (columna,))
    return cursor.fetchone() is not None


def es_nombre_logico_id_lista_detalle(nombre_columna: str) -> bool:
    """True si el nombre físico corresponde a la PK lógica id_lista_detalle (p. ej. id\\x1f_lista_detalle)."""
    norm = re.sub(r"[^a-z0-9]", "", (nombre_columna or "").lower())
    return norm == "idlistadetalle"


def columna_primary_key(cursor, tabla: str) -> Optional[str]:
    """Devuelve el nombre físico de la columna PRIMARY KEY de ``tabla``, o None."""
    tabla_esc = tabla.replace("`", "``")
    cursor.execute("SHOW COLUMNS FROM `%s`" % tabla_esc)
    for row in cursor.fetchall() or []:
        if isinstance(row, dict):
            field = row.get("Field") or row.get("field")
            key = row.get("Key") or row.get("key")
        else:
            field = row[0] if row else None
            key = row[3] if row and len(row) > 3 else None
        if key == "PRI" and field is not None:
            return str(field).strip()
    return None


def nombre_columna_ci(cursor, tabla: str, nombre_logico: str) -> Optional[str]:
    """
    Devuelve el nombre físico de la columna en ``tabla`` si existe (comparación
    case-insensitive con ``nombre_logico``), o None.

    En servidores MySQL Linux, ``SHOW COLUMNS ... LIKE 'foo'`` distingue mayúsculas;
    si el esquema legado tiene ``Foo`` o ``CANTIDAD_PROMEDIO_BULTO``, ``columna_existe``
    puede fallar en falso negativo. Para lecturas dinámicas (p. ej. ``articulo``) usar
    esta función y referenciar el nombre devuelto entre backticks en el SQL.
    """
    nombre_logico = (nombre_logico or "").strip()
    if not nombre_logico:
        return None
    target = nombre_logico.lower()
    tabla_esc = tabla.replace("`", "``")
    cursor.execute("SHOW COLUMNS FROM `%s`" % tabla_esc)
    for row in cursor.fetchall() or []:
        if isinstance(row, dict):
            field = row.get("Field") or row.get("field")
        else:
            field = row[0] if row else None
        if field is not None and str(field).strip().lower() == target:
            return str(field).strip()
    return None


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
