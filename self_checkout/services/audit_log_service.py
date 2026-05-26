"""
Registro en self_checkout_audit_log para trazabilidad (sin datos sensibles).
"""
import json
import logging
from typing import Any, Dict, Optional

from self_checkout.db import mysql_cursor

logger = logging.getLogger(__name__)


def registrar_evento_carrito(
    base_empresa: str,
    cart_id: int,
    accion: str,
    detalle: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Inserta una fila de auditoría ligada al carrito (kiosk/sucursal/PV desde el propio carrito).
    Fallas de BD no propagan; solo se registran en log.
    """
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as c:
            c.execute(
                """
                SELECT kiosk_id, id_sucursal, id_punto_venta
                FROM self_checkout_cart WHERE id = %s
                """,
                [cart_id],
            )
            row = c.fetchone()
        if not row:
            return
        payload = json.dumps(detalle or {}, ensure_ascii=False)[:4000]
        with mysql_cursor(base_empresa) as c:
            c.execute(
                """
                INSERT INTO self_checkout_audit_log (kiosk_id, id_sucursal, id_punto_venta, cart_id, accion, detalle)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                [
                    row.get('kiosk_id'),
                    row.get('id_sucursal'),
                    row.get('id_punto_venta'),
                    cart_id,
                    accion[:64],
                    payload,
                ],
            )
    except Exception as e:
        if "doesn't exist" in str(e) or 'Unknown table' in str(e):
            return
        logger.warning("registrar_evento_carrito omitido: %s", e)
