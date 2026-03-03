"""
CartService: crear carrito, agregar/quitar ítem, aplicar RFID confirm, recalcular totales.
Reglas: no agregar cantidad que exceda DISPONIBLE; revalidar stock al confirmar.
"""
import logging
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple

from self_checkout.db import mysql_cursor
from .stock_service import StockService

logger = logging.getLogger(__name__)


def _importes_con_descuento_renglon(
    cantidad: Decimal, precio_unitario: Decimal, alicuota_iva: Decimal, porcentaje_descuento: Decimal
) -> Tuple[Decimal, Decimal]:
    """Descuento por renglón (como TPV VB6): descuento sobre neto, luego IVA sobre neto con descuento.
    Returns: (importe_iva, importe_total)."""
    neto_sin_desc = cantidad * precio_unitario
    pct = porcentaje_descuento if porcentaje_descuento is not None else Decimal('0')
    neto = neto_sin_desc * (Decimal('100') - pct) / Decimal('100')
    imp_iva = neto * (alicuota_iva / Decimal('100'))
    return imp_iva, neto + imp_iva


class CartService:
    def __init__(self, base_empresa: str):
        self.base_empresa = base_empresa
        self.stock_service = StockService(base_empresa)

    def crear_carrito(
        self,
        kiosk_id: str,
        id_sucursal: int,
        id_punto_venta: int,
        id_deposito: int,
    ) -> Optional[int]:
        """Crea carrito en estado borrador. Retorna cart_id o None."""
        with mysql_cursor(self.base_empresa) as cursor:
            cursor.execute("""
                INSERT INTO self_checkout_cart 
                (kiosk_id, id_sucursal, id_punto_venta, id_deposito, estado, subtotal, total)
                VALUES (%s, %s, %s, %s, 'borrador', 0, 0)
            """, [kiosk_id, id_sucursal, id_punto_venta, id_deposito])
            return cursor.lastrowid

    def obtener_carrito_activo(self, kiosk_id: str) -> Optional[Dict]:
        """Obtiene carrito en borrador o pago_pendiente para el kiosco."""
        with mysql_cursor(self.base_empresa, dict_cursor=True) as cursor:
            cursor.execute("""
                SELECT * FROM self_checkout_cart
                WHERE kiosk_id = %s AND estado IN ('borrador', 'pago_pendiente')
                ORDER BY id DESC LIMIT 1
            """, [kiosk_id])
            return cursor.fetchone()

    def agregar_item(
        self,
        cart_id: int,
        id_articulo: int,
        codigo_articulo: str,
        descripcion: str,
        cantidad: Decimal,
        precio_unitario: Decimal,
        alicuota_iva: Decimal,
        origen: str = 'scan',
        rfid_event_id: Optional[int] = None,
        codigo_barras: Optional[str] = None,
        porcentaje_descuento: Optional[Decimal] = None,
        promocion: Optional[str] = None,
        promocion_por: Optional[Decimal] = None,
        promocion_tipo: Optional[str] = None,
        promocion_cant: Optional[Decimal] = None,
        detalle: Optional[str] = None,
    ) -> Tuple[Optional[int], Optional[str]]:
        """
        Agrega ítem al carrito. Valida stock DISPONIBLE antes de agregar.
        No se permite cantidad que exceda disponible.
        Returns: (item_id, error_msg) - si error_msg, no se agregó.
        """
        if cantidad <= 0:
            return None, 'Cantidad debe ser mayor a 0'

        with mysql_cursor(self.base_empresa, dict_cursor=True) as cursor:
            cursor.execute("SELECT id_deposito FROM self_checkout_cart WHERE id = %s", [cart_id])
            row = cursor.fetchone()
            if not row:
                return None, 'Carrito no encontrado'
            id_deposito = row['id_deposito']

            cursor.execute("""
                SELECT id_articulo, cantidad FROM self_checkout_cart_item WHERE cart_id = %s
            """, [cart_id])
            # Sumar cantidades por artículo (puede haber varias filas del mismo artículo)
            existing = {}
            for r in cursor.fetchall():
                id_a = r['id_articulo']
                existing[id_a] = existing.get(id_a, Decimal('0')) + Decimal(str(r['cantidad']))

        # Cantidad total por artículo (existentes + nuevo)
        cant_actual = existing.get(id_articulo, Decimal('0'))
        cant_total = cant_actual + cantidad

        ok, err = self.stock_service.validar_disponible_items(
            [{'id_articulo': id_articulo, 'cantidad': cant_total}],
            id_deposito,
        )
        if not ok:
            sug = err.get('sugerencia', f"disponible {err['disponible']}")
            nombre = (descripcion or '').strip() or f"artículo {err['id_articulo']}"
            return None, f"Stock insuficiente: {nombre}. {sug}"

        # Normalizar a Decimal (DB/API pueden devolver float)
        qty = Decimal(str(cantidad))
        pu = Decimal(str(precio_unitario))
        iva = Decimal(str(alicuota_iva))
        pdesc = porcentaje_descuento if porcentaje_descuento is not None else Decimal('0')

        with mysql_cursor(self.base_empresa, dict_cursor=True) as cursor:
            # Si el artículo ya está en el carrito, actualizar cantidad (una línea por artículo)
            cursor.execute("""
                SELECT id, cantidad, precio_unitario, alicuota_iva, COALESCE(porcentaje_descuento, 0) AS porcentaje_descuento
                FROM self_checkout_cart_item
                WHERE cart_id = %s AND id_articulo = %s
                LIMIT 1
            """, [cart_id, id_articulo])
            existing_row = cursor.fetchone()
            if existing_row:
                item_id = existing_row['id']
                cant_nueva = Decimal(str(existing_row['cantidad'])) + qty
                pu_ex = Decimal(str(existing_row['precio_unitario']))
                iva_ex = Decimal(str(existing_row['alicuota_iva']))
                pdesc_ex = Decimal(str(existing_row.get('porcentaje_descuento') or 0))
                imp_iva, imp_total = _importes_con_descuento_renglon(cant_nueva, pu_ex, iva_ex, pdesc_ex)
                cursor.execute("""
                    UPDATE self_checkout_cart_item
                    SET cantidad = %s, importe_iva = %s, importe_total = %s
                    WHERE id = %s AND cart_id = %s
                """, [cant_nueva, imp_iva, imp_total, item_id, cart_id])
                self._recalcular_totales(cursor, cart_id)
                return item_id, None

            # Artículo nuevo en el carrito: INSERT (incluye campos TPV si existen en la tabla)
            importe_iva, importe_total = _importes_con_descuento_renglon(qty, pu, iva, pdesc)
            cod_bar = (codigo_barras or codigo_articulo or '')[:64] if codigo_barras is not None else (codigo_articulo or '')[:64]
            cursor.execute("SELECT COALESCE(MAX(orden), 0) AS max_orden FROM self_checkout_cart_item WHERE cart_id = %s", [cart_id])
            row = cursor.fetchone()
            orden = int(row.get('max_orden') or 0) + 1
            prom_por = promocion_por if promocion_por is not None else None
            prom_tipo = (str(promocion_tipo)[:64] if promocion_tipo else None) or None
            prom_cant = promocion_cant if promocion_cant is not None else None
            try:
                cursor.execute("""
                    INSERT INTO self_checkout_cart_item 
                    (cart_id, id_articulo, codigo_articulo, codigo_barras, descripcion, cantidad, precio_unitario,
                     alicuota_iva, importe_iva, importe_total, porcentaje_descuento, promocion, promocion_por, promocion_tipo, promocion_cant, detalle, origen, rfid_event_id, orden)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, [cart_id, id_articulo, codigo_articulo, cod_bar or None, descripcion, qty, pu, iva,
                      importe_iva, importe_total, pdesc, promocion, prom_por, prom_tipo, prom_cant, detalle, origen, rfid_event_id, orden])
            except Exception as e:
                if 'Unknown column' in str(e):
                    try:
                        cursor.execute("""
                            INSERT INTO self_checkout_cart_item 
                            (cart_id, id_articulo, codigo_articulo, codigo_barras, descripcion, cantidad, precio_unitario,
                             alicuota_iva, importe_iva, importe_total, porcentaje_descuento, promocion, detalle, origen, rfid_event_id, orden)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, [cart_id, id_articulo, codigo_articulo, cod_bar or None, descripcion, qty, pu, iva,
                              importe_iva, importe_total, pdesc, promocion, detalle, origen, rfid_event_id, orden])
                    except Exception as e2:
                        if 'Unknown column' in str(e2):
                            cursor.execute("""
                                INSERT INTO self_checkout_cart_item 
                                (cart_id, id_articulo, codigo_articulo, descripcion, cantidad, precio_unitario,
                                 alicuota_iva, importe_iva, importe_total, origen, rfid_event_id, orden)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, [cart_id, id_articulo, codigo_articulo, descripcion, qty, pu, iva,
                                  importe_iva, importe_total, origen, rfid_event_id, orden])
                        else:
                            raise
                else:
                    raise
            item_id = cursor.lastrowid
            self._recalcular_totales(cursor, cart_id)
            return item_id, None

    def quitar_item(self, cart_id: int, item_id: int) -> bool:
        """Elimina ítem del carrito."""
        with mysql_cursor(self.base_empresa) as cursor:
            cursor.execute("DELETE FROM self_checkout_cart_item WHERE id = %s AND cart_id = %s", [item_id, cart_id])
            if cursor.rowcount > 0:
                self._recalcular_totales(cursor, cart_id)
                return True
            return False

    def actualizar_descuento_item(
        self, cart_id: int, item_id: int, porcentaje_descuento: Decimal
    ) -> Tuple[bool, Optional[str]]:
        """Actualiza el porcentaje de descuento de un ítem y recalcula importe_iva e importe_total.
        Returns: (ok, error_msg)."""
        if porcentaje_descuento < 0 or porcentaje_descuento > 100:
            return False, 'El descuento debe estar entre 0 y 100 %'
        pdesc = Decimal(str(porcentaje_descuento))
        with mysql_cursor(self.base_empresa, dict_cursor=True) as cursor:
            cursor.execute("""
                SELECT cantidad, precio_unitario, alicuota_iva
                FROM self_checkout_cart_item
                WHERE id = %s AND cart_id = %s
            """, [item_id, cart_id])
            row = cursor.fetchone()
            if not row:
                return False, 'Ítem no encontrado'
            cant = Decimal(str(row['cantidad']))
            pu = Decimal(str(row['precio_unitario']))
            iva = Decimal(str(row['alicuota_iva']))
            imp_iva, imp_total = _importes_con_descuento_renglon(cant, pu, iva, pdesc)
            try:
                cursor.execute("""
                    UPDATE self_checkout_cart_item
                    SET porcentaje_descuento = %s, importe_iva = %s, importe_total = %s
                    WHERE id = %s AND cart_id = %s
                """, [pdesc, imp_iva, imp_total, item_id, cart_id])
            except Exception as e:
                if 'Unknown column' in str(e):
                    cursor.execute("""
                        UPDATE self_checkout_cart_item
                        SET importe_iva = %s, importe_total = %s
                        WHERE id = %s AND cart_id = %s
                    """, [imp_iva, imp_total, item_id, cart_id])
                else:
                    raise
            self._recalcular_totales(cursor, cart_id)
        return True, None

    def _recalcular_totales(self, cursor, cart_id: int):
        """Recalcula subtotal y total del carrito. Si hay voucher aplicado, total = subtotal * (1 - monto_descuento_voucher/100)."""
        cursor.execute("""
            SELECT COALESCE(SUM(importe_total - COALESCE(importe_iva, 0)), 0) as sub,
                   COALESCE(SUM(importe_total), 0) as tot
            FROM self_checkout_cart_item WHERE cart_id = %s
        """, [cart_id])
        row = cursor.fetchone()
        if isinstance(row, dict):
            sub, tot = (row.get('sub', 0) or 0), (row.get('tot', 0) or 0)
        else:
            sub, tot = (row[0] or 0, row[1] or 0) if row else (0, 0)
        try:
            cursor.execute(
                "SELECT id_sp_cupon, monto_descuento_voucher FROM self_checkout_cart WHERE id = %s",
                [cart_id],
            )
            cart_row = cursor.fetchone()
            if cart_row:
                pct_val = cart_row.get('monto_descuento_voucher') if isinstance(cart_row, dict) else cart_row[1]
                if pct_val is not None:
                    pct = float(pct_val)
                    if 0 < pct <= 100:
                        tot = float(sub) * (1 - pct / 100.0)
        except Exception:
            pass
        cursor.execute("UPDATE self_checkout_cart SET subtotal = %s, total = %s WHERE id = %s", [sub, tot, cart_id])

    def aplicar_voucher(
        self, cart_id: int, id_sp_cupon: int, monto_descuento_pct: Decimal
    ) -> Tuple[bool, Optional[str]]:
        """Aplica un voucher al carrito: guarda id_sp_cupon y % descuento, recalcula total."""
        if monto_descuento_pct < 0 or monto_descuento_pct > 100:
            return False, 'Porcentaje de descuento inválido'
        with mysql_cursor(self.base_empresa, dict_cursor=True) as cursor:
            cursor.execute("SELECT id FROM self_checkout_cart WHERE id = %s", [cart_id])
            if not cursor.fetchone():
                return False, 'Carrito no encontrado'
            try:
                cursor.execute("""
                    UPDATE self_checkout_cart SET id_sp_cupon = %s, monto_descuento_voucher = %s
                    WHERE id = %s
                """, [id_sp_cupon, monto_descuento_pct, cart_id])
            except Exception as e:
                if 'Unknown column' in str(e):
                    return False, 'Vouchers no disponibles en este sistema'
                raise
        self._recalcular_totales_with_voucher(cart_id, monto_descuento_pct)
        return True, None

    def _recalcular_totales_with_voucher(self, cart_id: int, monto_descuento_pct: Decimal):
        """Fuerza recálculo de total con descuento voucher."""
        with mysql_cursor(self.base_empresa, dict_cursor=True) as cursor:
            cursor.execute(
                "SELECT COALESCE(SUM(importe_total - COALESCE(importe_iva, 0)), 0) as sub FROM self_checkout_cart_item WHERE cart_id = %s",
                [cart_id],
            )
            row = cursor.fetchone()
            sub = float(row.get('sub', 0) or 0) if row else 0
            tot = sub * (1 - float(monto_descuento_pct) / 100.0)
            cursor.execute("UPDATE self_checkout_cart SET subtotal = %s, total = %s WHERE id = %s", [sub, tot, cart_id])

    def quitar_voucher(self, cart_id: int) -> Tuple[bool, Optional[str]]:
        """Quita el voucher aplicado al carrito y recalcula total."""
        with mysql_cursor(self.base_empresa) as cursor:
            try:
                cursor.execute(
                    "UPDATE self_checkout_cart SET id_sp_cupon = NULL, monto_descuento_voucher = NULL WHERE id = %s",
                    [cart_id],
                )
            except Exception as e:
                if 'Unknown column' in str(e):
                    return True, None
                raise
            self._recalcular_totales(cursor, cart_id)
        return True, None

    def aplicar_descuento_pie(
        self, cart_id: int, porcentaje_descuento: Decimal
    ) -> Tuple[bool, Optional[str]]:
        """
        Aplica descuento masivo al pie (PorDesc1) a toda la factura.
        Pone monto_descuento_voucher = porcentaje y id_sp_cupon = NULL (descuento manual, no voucher).
        Recalcula total = subtotal * (1 - porcentaje/100).
        """
        if porcentaje_descuento < 0 or porcentaje_descuento > 100:
            return False, 'El descuento debe estar entre 0 y 100 %'
        with mysql_cursor(self.base_empresa, dict_cursor=True) as cursor:
            cursor.execute("SELECT id FROM self_checkout_cart WHERE id = %s", [cart_id])
            if not cursor.fetchone():
                return False, 'Carrito no encontrado'
            try:
                cursor.execute("""
                    UPDATE self_checkout_cart SET monto_descuento_voucher = %s, id_sp_cupon = NULL
                    WHERE id = %s
                """, [porcentaje_descuento, cart_id])
            except Exception as e:
                if 'Unknown column' in str(e):
                    return False, 'Columna monto_descuento_voucher no disponible'
                raise
        self._recalcular_totales_with_voucher(cart_id, porcentaje_descuento)
        return True, None

    def obtener_items(self, cart_id: int) -> List[Dict]:
        """Lista ítems del carrito."""
        with mysql_cursor(self.base_empresa, dict_cursor=True) as cursor:
            cursor.execute("""
                SELECT * FROM self_checkout_cart_item WHERE cart_id = %s ORDER BY orden
            """, [cart_id])
            return list(cursor.fetchall())

    def validar_stock_y_preparar_pago(self, cart_id: int) -> tuple:
        """
        Valida DISPONIBLE para todos los ítems. Si ok, pasa a pago_pendiente.
        Returns: (ok, error_msg)
        """
        with mysql_cursor(self.base_empresa, dict_cursor=True) as cursor:
            cursor.execute("SELECT id_deposito FROM self_checkout_cart WHERE id = %s", [cart_id])
            row = cursor.fetchone()
            if not row:
                return False, 'Carrito no encontrado'
            id_deposito = row['id_deposito']

            cursor.execute("""
                SELECT id_articulo, cantidad FROM self_checkout_cart_item WHERE cart_id = %s
            """, [cart_id])
            items = [{'id_articulo': r['id_articulo'], 'cantidad': r['cantidad']} for r in cursor.fetchall()]

        ok, err = self.stock_service.validar_disponible_items(items, id_deposito)
        if not ok:
            logger.warning(
                'STOCK_INSUFFICIENT en validar_stock_y_preparar_pago: cart_id=%s id_articulo=%s disponible=%s',
                cart_id, err['id_articulo'], err['disponible'],
            )
            return False, f"Stock insuficiente: artículo {err['id_articulo']}, disponible {err['disponible']}"

        with mysql_cursor(self.base_empresa) as cursor:
            cursor.execute(
                "UPDATE self_checkout_cart SET estado = 'pago_pendiente' WHERE id = %s AND estado = 'borrador'",
                [cart_id]
            )
            if cursor.rowcount == 0:
                return False, 'No se pudo cambiar estado'
        return True, None

    def aplicar_rfid_confirm(
        self,
        cart_id: int,
        items_propuesta: List[Dict],
        sesion_id: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Aplica ítems confirmados desde RFID al carrito.
        Valida stock por cada ítem (agregar_item valida).
        items_propuesta: [{'id_articulo', 'codigo_articulo', 'descripcion', 'cantidad', 'precio_unitario', 'alicuota_iva'}, ...]
        Returns: (ok, error_msg)
        """
        for item in items_propuesta:
            item_id, err = self.agregar_item(
                cart_id=cart_id,
                id_articulo=item['id_articulo'],
                codigo_articulo=item.get('codigo_articulo', ''),
                descripcion=item.get('descripcion', ''),
                cantidad=Decimal(str(item['cantidad'])),
                precio_unitario=Decimal(str(item['precio_unitario'])),
                alicuota_iva=Decimal(str(item.get('alicuota_iva', 0))),
                origen='rfid',
            )
            if err:
                return False, err
        return True, None
