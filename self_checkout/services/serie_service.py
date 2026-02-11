"""
Servicio de números de serie (réplica administraNET VB6).
Artículos con articulo.serie = 'Si' requieren elegir N series (N = cantidad) desde serie_entrada.
"""
import logging
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple

from self_checkout.db import mysql_cursor

logger = logging.getLogger(__name__)


def articulo_es_seriado(base_empresa: str, id_articulo: int) -> bool:
    """True si articulo.serie = 'Si'."""
    with mysql_cursor(base_empresa, dict_cursor=True) as c:
        try:
            c.execute(
                "SELECT serie FROM articulo WHERE IDArt = %s LIMIT 1",
                [id_articulo],
            )
            row = c.fetchone()
            return row and (row.get('serie') or '').strip() == 'Si'
        except Exception as e:
            if 'Unknown column' in str(e):
                return False
            raise
    return False


def listar_series_disponibles(
    base_empresa: str,
    id_articulo: int,
    id_deposito: int,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """
    Lista series disponibles (serie_entrada.disponible = 'Si') para el artículo y depósito.
    """
    out = []
    with mysql_cursor(base_empresa, dict_cursor=True) as c:
        try:
            c.execute("""
                SELECT id_serie_entrada, nro_serie, COALESCE(desc_serie, '') AS desc_serie,
                       vto_serie, fecha
                FROM serie_entrada
                WHERE id_articulo = %s AND COALESCE(disponible, 'Si') = 'Si'
                  AND (id_deposito = %s OR id_deposito IS NULL)
                ORDER BY nro_serie
                LIMIT %s
            """, [id_articulo, id_deposito, limit])
            for row in c.fetchall():
                vto = row.get('vto_serie')
                if vto and hasattr(vto, 'strftime'):
                    vto = vto.strftime('%Y-%m-%d') if hasattr(vto, 'strftime') else str(vto)
                out.append({
                    'id_serie_entrada': row.get('id_serie_entrada'),
                    'nro_serie': row.get('nro_serie') or '',
                    'desc_serie': row.get('desc_serie') or '',
                    'vto_serie': vto,
                })
        except Exception as e:
            if "doesn't exist" in str(e) or 'Unknown column' in str(e):
                return []
            logger.warning("listar_series_disponibles failed: %s", e)
            return []
    return out


def asignar_series_a_item(
    base_empresa: str,
    cart_id: int,
    item_id: int,
    id_serie_entrada_list: List[int],
    id_deposito: int,
) -> Tuple[bool, Optional[str]]:
    """
    Asigna números de serie a un ítem del carrito.
    - Valida que el ítem exista, sea del cart_id y que cantidad = len(id_serie_entrada_list).
    - Valida que cada id_serie_entrada sea del mismo artículo, depósito y disponible.
    - Borra series previas del ítem, inserta en self_checkout_cart_item_serie y actualiza cart_item.serie, desc_serie.
    """
    with mysql_cursor(base_empresa, dict_cursor=True) as c:
        c.execute("""
            SELECT ci.id, ci.id_articulo, ci.cantidad
            FROM self_checkout_cart_item ci
            WHERE ci.id = %s AND ci.cart_id = %s
        """, [item_id, cart_id])
        row = c.fetchone()
        if not row:
            return False, 'Ítem no encontrado'
        id_articulo = int(row['id_articulo'])
        cantidad = int(Decimal(str(row['cantidad'])))
        if len(id_serie_entrada_list) != cantidad:
            return False, f'Debe seleccionar exactamente {cantidad} número(s) de serie'

        # Validar que cada id_serie_entrada exista, sea del artículo/depósito y disponible
        placeholders = ','.join(['%s'] * len(id_serie_entrada_list))
        c.execute("""
            SELECT id_serie_entrada, nro_serie, desc_serie, vto_serie
            FROM serie_entrada
            WHERE id_articulo = %s AND (id_deposito = %s OR id_deposito IS NULL)
              AND COALESCE(disponible, 'Si') = 'Si'
              AND id_serie_entrada IN (%s)
        """ % placeholders, [id_articulo, id_deposito] + id_serie_entrada_list)
        valid_series = {r['id_serie_entrada']: r for r in c.fetchall()}
        if len(valid_series) != len(id_serie_entrada_list):
            return False, 'Uno o más números de serie no están disponibles o no corresponden al artículo'

        # Borrar previos
        try:
            c.execute("DELETE FROM self_checkout_cart_item_serie WHERE cart_item_id = %s", [item_id])
        except Exception as e:
            if "doesn't exist" in str(e):
                pass
            else:
                raise

        # Construir desc_serie (nro_serie - vto concatenados)
        partes = []
        for id_se in id_serie_entrada_list:
            r = valid_series.get(id_se)
            if not r:
                continue
            nro = (r.get('nro_serie') or '').strip()
            vto = r.get('vto_serie')
            if vto and hasattr(vto, 'strftime'):
                vto = vto.strftime('%Y-%m-%d')
            else:
                vto = str(vto) if vto else ''
            partes.append(f"{nro} - {vto}" if vto else nro)
        desc_serie = ', '.join(partes)[:500]

        # Insertar en cart_item_serie
        for id_se in id_serie_entrada_list:
            r = valid_series[id_se]
            c.execute("""
                INSERT INTO self_checkout_cart_item_serie (cart_item_id, id_serie_entrada, nro_serie, desc_serie, vto_serie)
                VALUES (%s, %s, %s, %s, %s)
            """, [item_id, id_se, r.get('nro_serie'), r.get('desc_serie'), r.get('vto_serie')])

        # Actualizar cart_item
        try:
            c.execute("""
                UPDATE self_checkout_cart_item SET serie = 'Si', desc_serie = %s
                WHERE id = %s AND cart_id = %s
            """, [desc_serie, item_id, cart_id])
        except Exception as e:
            if 'Unknown column' in str(e):
                pass
            else:
                raise

    return True, None


def obtener_series_por_item(base_empresa: str, cart_item_id: int) -> List[Dict[str, Any]]:
    """Lista las series asignadas a un ítem del carrito."""
    out = []
    with mysql_cursor(base_empresa, dict_cursor=True) as c:
        try:
            c.execute("""
                SELECT id_serie_entrada, nro_serie, desc_serie, vto_serie
                FROM self_checkout_cart_item_serie
                WHERE cart_item_id = %s
                ORDER BY id
            """, [cart_item_id])
            for row in c.fetchall():
                vto = row.get('vto_serie')
                if vto and hasattr(vto, 'strftime'):
                    vto = vto.strftime('%Y-%m-%d')
                out.append({
                    'id_serie_entrada': row.get('id_serie_entrada'),
                    'nro_serie': row.get('nro_serie') or '',
                    'desc_serie': row.get('desc_serie') or '',
                    'vto_serie': vto,
                })
        except Exception as e:
            if "doesn't exist" in str(e):
                return []
            raise
    return out


def validar_series_carrito(base_empresa: str, cart_id: int) -> Tuple[bool, Optional[str]]:
    """
    Para cada ítem con serie='Si', verifica que tenga exactamente cantidad series en cart_item_serie.
    Returns (ok, error_msg).
    """
    with mysql_cursor(base_empresa, dict_cursor=True) as c:
        try:
            c.execute("""
                SELECT ci.id, ci.id_articulo, ci.cantidad, ci.descripcion, ci.serie
                FROM self_checkout_cart_item ci
                WHERE ci.cart_id = %s
            """, [cart_id])
            items = c.fetchall()
        except Exception as e:
            if 'Unknown column' in str(e):
                return True, None  # columna serie no existe
            raise
        for it in items:
            if (it.get('serie') or '').strip() != 'Si':
                continue
            cant = int(Decimal(str(it['cantidad'])))
            try:
                c.execute(
                    "SELECT COUNT(*) AS n FROM self_checkout_cart_item_serie WHERE cart_item_id = %s",
                    [it['id']],
                )
                r = c.fetchone()
                n = int(r.get('n', 0) or 0)
            except Exception:
                n = 0
            if n != cant:
                nombre = (it.get('descripcion') or '').strip() or f"Artículo {it.get('id_articulo')}"
                return False, f'"{nombre}": la cantidad de números de serie ({n}) no coincide con la cantidad ({cant}).'
    return True, None
