"""Extractores catálogos maestros."""

from __future__ import annotations

from typing import Any, Dict, List

from odoo_migracion.extractors.base import BaseExtractor


class ContribuyenteExtractor(BaseExtractor):
    entity_type = "contribuyente"

    def count(self) -> int:
        return self._scalar("SELECT COUNT(*) FROM contribuyentes")

    def extract(self, *, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM contribuyentes ORDER BY idIVA LIMIT %s OFFSET %s"
        return self._execute(sql, [limit, offset])


class UomExtractor(BaseExtractor):
    entity_type = "uom"

    def count(self) -> int:
        return self._scalar("SELECT COUNT(*) FROM unidmed WHERE anulado = 'No'")

    def extract(self, *, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        sql = """
            SELECT id_unimed, nombre_unimed, abreviatura, anulado
            FROM unidmed
            WHERE anulado = 'No'
            ORDER BY id_unimed
            LIMIT %s OFFSET %s
        """
        return self._execute(sql, [limit, offset])


class RubroExtractor(BaseExtractor):
    entity_type = "rubro"

    def count(self) -> int:
        return self._scalar("SELECT COUNT(*) FROM rubro WHERE anulado = 'No'")

    def extract(self, *, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        sql = """
            SELECT CodigoRubro, NombreRubro, anulado, tipo_rubro
            FROM rubro WHERE anulado = 'No'
            ORDER BY CodigoRubro LIMIT %s OFFSET %s
        """
        return self._execute(sql, [limit, offset])


class SubrubroExtractor(BaseExtractor):
    entity_type = "subrubro"

    def count(self) -> int:
        return self._scalar("SELECT COUNT(*) FROM subrubro WHERE anulado = 'No'")

    def extract(self, *, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        sql = """
            SELECT IDSubRubro, CodigoRubro, CodigoSubRubro, NombreSubRubro, anulado
            FROM subrubro WHERE anulado = 'No'
            ORDER BY IDSubRubro LIMIT %s OFFSET %s
        """
        return self._execute(sql, [limit, offset])


class MarcaExtractor(BaseExtractor):
    entity_type = "marca"

    def count(self) -> int:
        return self._scalar("SELECT COUNT(*) FROM marca WHERE anulado = 'No'")

    def extract(self, *, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        sql = """
            SELECT CodMarca, NombreMarca, anulado
            FROM marca WHERE anulado = 'No'
            ORDER BY CodMarca LIMIT %s OFFSET %s
        """
        return self._execute(sql, [limit, offset])


class ViajanteExtractor(BaseExtractor):
    entity_type = "viajante"

    def count(self) -> int:
        return self._scalar("SELECT COUNT(*) FROM viajantes WHERE Anulado = 'No'")

    def extract(self, *, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        sql = """
            SELECT CodViajante, Nombre, ComisionVta, ComisionCob, cobrador, Anulado
            FROM viajantes WHERE Anulado = 'No'
            ORDER BY CodViajante LIMIT %s OFFSET %s
        """
        return self._execute(sql, [limit, offset])


class DepositoExtractor(BaseExtractor):
    entity_type = "deposito"

    def count(self) -> int:
        return self._scalar("SELECT COUNT(*) FROM deposito WHERE anulado = 'No'")

    def extract(self, *, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        sql = """
            SELECT id_deposito, nombre_deposito, anulado, id_sucursal
            FROM deposito WHERE anulado = 'No'
            ORDER BY id_deposito LIMIT %s OFFSET %s
        """
        return self._execute(sql, [limit, offset])
