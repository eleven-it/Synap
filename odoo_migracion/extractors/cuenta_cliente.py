"""Extractor facturas cuenta corriente cliente con saldo abierto."""

from __future__ import annotations

from typing import Any, Dict, List

from odoo_migracion.extractors.base import BaseExtractor


class CuentaClienteAbiertaExtractor(BaseExtractor):
    entity_type = "cuenta_cliente"

    def count(self) -> int:
        return self._scalar(
            """
            SELECT COUNT(*) FROM cuentacliente
            WHERE Anulado = 'No' AND saldo > 0
              AND TipoComprobante IN ('FA','FB','FC','ND')
            """
        )

    def extract(self, *, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        sql = """
            SELECT cc.*
            FROM cuentacliente cc
            WHERE cc.Anulado = 'No' AND cc.saldo > 0
              AND cc.TipoComprobante IN ('FA','FB','FC','ND')
            ORDER BY cc.id_cuentacliente
            LIMIT %s OFFSET %s
        """
        return self._execute(sql, [limit, offset])
