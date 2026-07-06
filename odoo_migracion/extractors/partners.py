"""Extractores clientes y proveedores."""

from __future__ import annotations

from typing import Any, Dict, List

from odoo_migracion.extractors.base import BaseExtractor


class ProveedorExtractor(BaseExtractor):
    entity_type = "proveedor"

    def count(self) -> int:
        return self._scalar(
            "SELECT COUNT(*) FROM proveedor WHERE estado = 'Activo' AND Codigo NOT IN (1, 2)"
        )

    def extract(self, *, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        sql = """
            SELECT p.*, c.nombre AS nombre_iva
            FROM proveedor p
            LEFT JOIN contribuyentes c ON c.idIVA = p.idIVA
            WHERE p.estado = 'Activo' AND p.Codigo NOT IN (1, 2)
            ORDER BY p.Codigo
            LIMIT %s OFFSET %s
        """
        return self._execute(sql, [limit, offset])


class ClienteExtractor(BaseExtractor):
    entity_type = "cliente"

    def count(self) -> int:
        return self._scalar("SELECT COUNT(*) FROM cliente WHERE Estado = 'Activo' AND Codigo <> 1")

    def extract(self, *, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        sql = """
            SELECT cl.*, c.nombre AS nombre_iva
            FROM cliente cl
            LEFT JOIN contribuyentes c ON c.idIVA = cl.IDIva
            WHERE cl.Estado = 'Activo' AND cl.Codigo <> 1
            ORDER BY cl.Codigo
            LIMIT %s OFFSET %s
        """
        return self._execute(sql, [limit, offset])
