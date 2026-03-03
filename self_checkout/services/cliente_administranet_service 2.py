"""
Consulta clientes dados de alta en administraNET (tabla cliente).
Búsqueda por CUIT para reutilizar datos (nombre, email) y comparar con padrón AFIP.
"""
import logging
from typing import Optional, Dict, Any

from self_checkout.db import mysql_cursor

logger = logging.getLogger(__name__)


def _normalize_cuit(cuit: str) -> str:
    return (cuit or "").replace("-", "").replace(" ", "").strip()


def buscar_cliente_por_cuit(base_empresa: str, cuit: str) -> Optional[Dict[str, Any]]:
    """
    Busca un cliente en administraNET por CUIT (normalizado).
    Returns: dict con Codigo (id_cliente), nombre_cliente, CUIT, email (si existe columna)
    o None si no existe.
    """
    cuit_clean = _normalize_cuit(cuit)
    if len(cuit_clean) != 11 or not cuit_clean.isdigit():
        return None
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cur:
            cur.execute(
                """
                SELECT Codigo, nombre_cliente, CUIT
                FROM cliente
                WHERE REPLACE(REPLACE(TRIM(COALESCE(CUIT,'')), '-', ''), ' ', '') = %s
                  AND (Codigo IS NULL OR Codigo <> 1)
                LIMIT 1
                """,
                [cuit_clean],
            )
            row = cur.fetchone()
        if not row:
            return None
        out = {
            "id_cliente": row.get("Codigo"),
            "nombre_cliente": (row.get("nombre_cliente") or "").strip(),
            "cuit": (row.get("CUIT") or "").strip(),
        }
        # Email: puede no existir en todas las bases (columna opcional)
        try:
            with mysql_cursor(base_empresa, dict_cursor=True) as cur2:
                cur2.execute(
                    "SELECT email FROM cliente WHERE Codigo = %s LIMIT 1",
                    [out["id_cliente"]],
                )
                r2 = cur2.fetchone()
                out["email"] = (r2.get("email") or "").strip() or None if r2 else None
        except Exception:
            out["email"] = None
        return out
    except Exception as e:
        logger.warning("buscar_cliente_por_cuit: %s", e)
        return None


def actualizar_cliente_denominacion(base_empresa: str, id_cliente: int, denominacion_afip: str) -> bool:
    """
    Actualiza nombre_cliente en administraNET con la denominación devuelta por AFIP.
    Returns: True si se actualizó al menos una fila.
    """
    if not id_cliente or id_cliente == 1:
        return False
    denom = (denominacion_afip or "").strip()
    if not denom:
        return False
    try:
        with mysql_cursor(base_empresa) as c:
            c.execute(
                "UPDATE cliente SET nombre_cliente = %s WHERE Codigo = %s",
                [denom[:255], id_cliente],  # nombre_cliente suele tener límite
            )
            return c.rowcount > 0
    except Exception as e:
        logger.warning("actualizar_cliente_denominacion: %s", e)
        return False
