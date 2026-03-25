"""
StockService: validación de DISPONIBLE (no saldo bruto).
disponible = max(0, stock_deposito.saldo - stock_deposito.saldo_pedido_cliente)

Concurrencia: En confirmación, ConfirmationService revalida dentro de transacción
con UPDATE condicional (WHERE saldo - saldo_pedido_cliente >= cantidad).
codmov y talonarios usan SELECT ... FOR UPDATE.
"""
import logging
from decimal import Decimal
from typing import Dict, List, Tuple, Optional

from self_checkout.db import mysql_cursor

logger = logging.getLogger(__name__)


class StockService:
    def __init__(self, base_empresa: str):
        self.base_empresa = base_empresa

    def get_disponible(self, id_articulo: int, id_deposito: int) -> Decimal:
        """Calcula stock disponible para un artículo en un depósito."""
        with mysql_cursor(self.base_empresa, dict_cursor=True) as cursor:
            cursor.execute("""
                SELECT 
                    COALESCE(saldo, 0) as saldo,
                    COALESCE(saldo_pedido_cliente, 0) as saldo_pedido_cliente
                FROM stock_deposito
                WHERE id_articulo = %s AND id_deposito = %s
            """, [id_articulo, id_deposito])
            row = cursor.fetchone()
            if not row:
                return Decimal('0')
            saldo = Decimal(str(row['saldo'] or 0))
            reservado = Decimal(str(row['saldo_pedido_cliente'] or 0))
            return max(Decimal('0'), saldo - reservado)

    def get_disponible_map(self, id_articulos: List[int], id_deposito: int) -> Dict[int, Decimal]:
        """Una consulta IN: disponible por id_articulo en el depósito (no listados → 0)."""
        ids = sorted({int(x) for x in id_articulos if x is not None})
        if not ids:
            return {}
        out: Dict[int, Decimal] = {i: Decimal('0') for i in ids}
        placeholders = ','.join(['%s'] * len(ids))
        sql = f"""
            SELECT id_articulo,
                   COALESCE(saldo, 0) AS saldo,
                   COALESCE(saldo_pedido_cliente, 0) AS saldo_pedido_cliente
            FROM stock_deposito
            WHERE id_deposito = %s AND id_articulo IN ({placeholders})
        """
        with mysql_cursor(self.base_empresa, dict_cursor=True) as cursor:
            cursor.execute(sql, [id_deposito] + ids)
            for row in cursor.fetchall():
                ia = int(row['id_articulo'])
                saldo = Decimal(str(row['saldo'] or 0))
                reservado = Decimal(str(row['saldo_pedido_cliente'] or 0))
                out[ia] = max(Decimal('0'), saldo - reservado)
        return out

    def validar_disponible_items(
        self, items: List[dict], id_deposito: int
    ) -> Tuple[bool, Optional[dict]]:
        """
        Valida que todos los ítems tengan stock disponible suficiente.
        DISPONIBLE = max(0, saldo - saldo_pedido_cliente) desde stock_deposito.
        items: [{'id_articulo': int, 'cantidad': Decimal}, ...]
        Returns: (ok, error_item) - si not ok, error_item tiene:
            id_articulo, cantidad_solicitada, disponible, faltante, sugerencia
        """
        for item in items:
            id_art = item.get('id_articulo')
            cant = Decimal(str(item.get('cantidad', 0)))
            if cant <= 0:
                continue
            disp = self.get_disponible(id_art, id_deposito)
            if disp < cant:
                faltante = cant - disp
                sugerencia = f"reducir cantidad a {disp}" if disp > 0 else "sin stock"
                err_item = {
                    'id_articulo': id_art,
                    'cantidad_solicitada': cant,
                    'disponible': disp,
                    'faltante': faltante,
                    'sugerencia': sugerencia,
                }
                logger.warning(
                    'STOCK_INSUFFICIENT: id_articulo=%s cantidad_solicitada=%s disponible=%s id_deposito=%s',
                    id_art, cant, disp, id_deposito,
                )
                return False, err_item
        return True, None

    def validate_disponible(
        self, items: List[dict], id_deposito: int
    ) -> Tuple[bool, Optional[dict]]:
        """Alias de validar_disponible_items (nomenclatura spec)."""
        return self.validar_disponible_items(items, id_deposito)
