"""Extractor datos empresa (datosempresa)."""

from __future__ import annotations

from typing import Any, Dict, List

from odoo_migracion.extractors.base import BaseExtractor


class EmpresaExtractor(BaseExtractor):
    entity_type = "empresa"

    def count(self) -> int:
        return self._scalar("SELECT COUNT(*) FROM datosempresa")

    def extract(self, *, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM datosempresa ORDER BY id_empresa LIMIT %s OFFSET %s"
        return self._execute(sql, [limit, offset])
