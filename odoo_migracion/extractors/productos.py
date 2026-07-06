"""Extractor artículos."""

from __future__ import annotations

from typing import Any, Dict, List

from odoo_migracion.extractors.base import BaseExtractor


class ArticuloExtractor(BaseExtractor):
    entity_type = "articulo"

    def count(self) -> int:
        return self._scalar("SELECT COUNT(*) FROM articulo WHERE Discontinuo = 'No'")

    def extract(self, *, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        sql = """
            SELECT a.*,
                   r.NombreRubro AS nombre_rubro,
                   m.NombreMarca AS nombre_marca
            FROM articulo a
            LEFT JOIN rubro r ON r.CodigoRubro = a.CodigoRubro
            LEFT JOIN marca m ON m.CodMarca = a.CodigoMarca
            WHERE a.Discontinuo = 'No'
            ORDER BY a.IDArt
            LIMIT %s OFFSET %s
        """
        return self._execute(sql, [limit, offset])
