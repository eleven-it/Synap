"""
Servicio de vouchers y programa de descuentos (réplica administraNET VB6).
Tablas: sp_desc_programa, sp_cupon_cliente.
"""
import logging
from datetime import date
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple

from self_checkout.db import mysql_cursor

logger = logging.getLogger(__name__)


def listar_vouchers_disponibles(
    base_empresa: str,
    id_cliente: int = 1,
    fecha: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """
    Lista vouchers disponibles para el cliente (sp_cupon_cliente.voucher_usado = 'No'
    y vigencia de sp_desc_programa). Para Consumidor Final (id_cliente=1) puede devolver vacío.
    """
    if fecha is None:
        fecha = date.today()
    fecha_str = fecha.strftime('%Y-%m-%d')
    out = []
    with mysql_cursor(base_empresa, dict_cursor=True) as c:
        try:
            c.execute("""
                SELECT p.id_sp_desc, p.nombre_sp_desc, p.tipo_programa, p.tipo_sp_desc,
                       COALESCE(p.monto_descuento, 0) AS monto_descuento,
                       p.desde, p.hasta,
                       c.id_sp_cupon, c.nro_voucher_serie
                FROM sp_desc_programa p
                INNER JOIN sp_cupon_cliente c ON c.id_sp_desc = p.id_sp_desc
                WHERE COALESCE(p.anulado, 'No') = 'No'
                  AND p.tipo_programa = 'Voucher'
                  AND COALESCE(c.voucher_usado, 'No') = 'No'
                  AND %s BETWEEN COALESCE(p.desde, '1900-01-01') AND COALESCE(p.hasta, '2099-12-31')
                ORDER BY p.nombre_sp_desc, c.id_sp_cupon
                LIMIT 100
            """, [fecha_str])
            for row in c.fetchall():
                out.append({
                    'id_sp_desc': row.get('id_sp_desc'),
                    'id_sp_cupon': row.get('id_sp_cupon'),
                    'nombre_sp_desc': row.get('nombre_sp_desc') or '',
                    'tipo_programa': row.get('tipo_programa') or '',
                    'tipo_sp_desc': row.get('tipo_sp_desc') or '',
                    'monto_descuento': float(row.get('monto_descuento') or 0),
                    'nro_voucher_serie': row.get('nro_voucher_serie') or '',
                })
        except Exception as e:
            if 'doesn\'t exist' in str(e) or 'Unknown column' in str(e):
                return []
            logger.warning("listar_vouchers_disponibles failed: %s", e)
            return []
    return out


def obtener_voucher_y_descuento(
    base_empresa: str,
    id_sp_cupon: int,
) -> Optional[Tuple[Decimal, int]]:
    """
    Valida que el cupón exista, no esté usado y esté vigente.
    Returns: (monto_descuento %, id_sp_desc) o None.
    """
    with mysql_cursor(base_empresa, dict_cursor=True) as c:
        try:
            c.execute("""
                SELECT c.id_sp_desc, COALESCE(p.monto_descuento, 0) AS monto_descuento,
                       COALESCE(c.voucher_usado, 'No') AS voucher_usado,
                       p.desde, p.hasta
                FROM sp_cupon_cliente c
                INNER JOIN sp_desc_programa p ON p.id_sp_desc = c.id_sp_desc
                WHERE c.id_sp_cupon = %s
                LIMIT 1
            """, [id_sp_cupon])
            row = c.fetchone()
        except Exception as e:
            if 'doesn\'t exist' in str(e):
                return None
            raise
        if not row or (row.get('voucher_usado') or '').strip() != 'No':
            return None
        desde, hasta = row.get('desde'), row.get('hasta')
        hoy = date.today()
        if desde and hasattr(desde, 'date'):
            desde = desde.date() if hasattr(desde, 'date') else desde
        if hasta and hasattr(hasta, 'date'):
            hasta = hasta.date() if hasattr(hasta, 'date') else hasta
        if desde and hoy < desde:
            return None
        if hasta and hoy > hasta:
            return None
        monto = Decimal(str(row.get('monto_descuento') or 0))
        id_sp_desc = int(row.get('id_sp_desc') or 0)
        return monto, id_sp_desc
    return None


def marcar_voucher_usado(base_empresa: str, id_sp_cupon: int) -> bool:
    """Marca el cupón como usado (voucher_usado = 'Si')."""
    with mysql_cursor(base_empresa) as c:
        try:
            c.execute(
                "UPDATE sp_cupon_cliente SET voucher_usado = 'Si' WHERE id_sp_cupon = %s",
                [id_sp_cupon],
            )
            return c.rowcount > 0
        except Exception as e:
            if 'doesn\'t exist' in str(e):
                return False
            raise
    return False
