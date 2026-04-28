"""
Contactos de cliente (paridad ``relay-contacto-cliente.php``; respuesta Synap en JSON).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import str_or_default


def lista_contactos_cliente(base_empresa: str, id_cliente: int) -> List[Dict[str, Any]]:
    sql = """
        SELECT
            contacto.nombre_cliente_contacto AS nombre,
            contacto.tipo_doc,
            contacto.nro_doc,
            contacto.id_cliente_contacto AS codigo
        FROM cliente_contacto AS contacto
        WHERE contacto.id_cliente = %s
          AND (contacto.anulado IS NULL OR contacto.anulado = 'No')
        ORDER BY contacto.nombre_cliente_contacto ASC
    """
    pool = get_mysql_pool()
    out: List[Dict[str, Any]] = []
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, [id_cliente])
        cols = [d[0] for d in cursor.description] if cursor.description else []
        for row in cursor.fetchall():
            out.append(dict(zip(cols, row)))
    return out


def alta_contacto_relay(
    base_empresa: str,
    *,
    id_cliente: int,
    completo: str,
    nombre_contacto: str,
    tipo_doc: str,
    nro_doc: str,
    telefono_contacto: str = "",
    email_contacto: str = "",
) -> Tuple[bool, Optional[str]]:
    comp = (completo or "No").strip()
    if comp == "No":
        sql = """
            INSERT INTO cliente_contacto (
                nombre_cliente_contacto, tipo_doc, nro_doc, id_cliente, anulado
            ) VALUES (%s, %s, %s, %s, 'No')
        """
        params = [
            str_or_default(nombre_contacto, "-"),
            str_or_default(tipo_doc, "-"),
            str_or_default(nro_doc, "-"),
            float(id_cliente),
        ]
    else:
        tel = str_or_default(telefono_contacto, "-")
        sql = """
            INSERT INTO cliente_contacto (
                nombre_cliente_contacto, tipo_doc, nro_doc,
                CelularContacto, TelefonoContacto, EmailContacto,
                id_cliente, anulado
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'No')
        """
        params = [
            str_or_default(nombre_contacto, "-"),
            str_or_default(tipo_doc, "-"),
            str_or_default(nro_doc, "-"),
            tel,
            tel,
            str_or_default(email_contacto, "-"),
            float(id_cliente),
        ]
    pool = get_mysql_pool()
    try:
        with pool.get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            conn.commit()
        return True, None
    except Exception as exc:
        return False, str(exc)
