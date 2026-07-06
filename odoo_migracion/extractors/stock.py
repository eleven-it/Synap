"""Extractor saldos por depósito."""

from __future__ import annotations

from typing import Any, Dict, List

from odoo_migracion.extractors.base import BaseExtractor


class StockSaldoExtractor(BaseExtractor):
    entity_type = "stock_saldo"

    def count(self) -> int:
        return self._scalar(
            """
            SELECT COUNT(*) FROM stock_deposito sd
            INNER JOIN articulo a ON a.IDArt = sd.id_articulo
            WHERE sd.saldo <> 0 AND a.Discontinuo = 'No'
            """
        )

    def extract(self, *, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        sql = """
            SELECT sd.id_stock_deposito, sd.id_articulo, sd.id_deposito,
                   sd.saldo, sd.saldo_pedido_cliente, sd.saldo_pedido_proveedor,
                   a.CodigoArticulo, a.NombreArticulo
            FROM stock_deposito sd
            INNER JOIN articulo a ON a.IDArt = sd.id_articulo
            WHERE sd.saldo <> 0 AND a.Discontinuo = 'No'
            ORDER BY sd.id_stock_deposito
            LIMIT %s OFFSET %s
        """
        return self._execute(sql, [limit, offset])
