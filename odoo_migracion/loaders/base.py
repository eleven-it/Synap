"""Carga idempotente en Odoo vía JSON-2."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Optional

from odoo_migracion.models import MigrationEntityMapping
from odoo_migracion.services.change_detection import row_payload_hash
from odoo_migracion.services.external_id import ref_adminet
from odoo_migracion.services.odoo_client import OdooJson2Client

if TYPE_CHECKING:
    from odoo_migracion.models import OdooConnection

logger = logging.getLogger(__name__)


@dataclass
class LoadResult:
    adminet_id: str
    action: str  # created | updated | skipped | error
    odoo_id: Optional[int] = None
    error: Optional[str] = None


class BaseOdooLoader:
    entity_type: str = ""
    odoo_model: str = ""
    search_field: str = "ref"

    def __init__(self, connection: "OdooConnection", client: Optional[OdooJson2Client] = None):
        self.connection = connection
        self.client = client or OdooJson2Client(connection)

    def resolve_mapping(self, adminet_id: str) -> Optional[MigrationEntityMapping]:
        return MigrationEntityMapping.objects.filter(
            conexion=self.connection,
            entity_type=self.entity_type,
            adminet_id=str(adminet_id),
        ).first()

    def _find_odoo_id_by_ref(self, ref: str) -> Optional[int]:
        rows = self.client.search_read(
            self.odoo_model,
            domain=[[self.search_field, "=", ref]],
            fields=["id"],
            limit=1,
        )
        if rows:
            return int(rows[0]["id"])
        return None

    def _save_mapping(
        self,
        adminet_id: str,
        external_id: str,
        odoo_id: int,
        row_hash: str,
        *,
        sync_state: str = MigrationEntityMapping.SyncState.OK,
    ) -> None:
        MigrationEntityMapping.objects.update_or_create(
            conexion=self.connection,
            entity_type=self.entity_type,
            adminet_id=str(adminet_id),
            defaults={
                "external_id": external_id,
                "odoo_model": self.odoo_model,
                "odoo_id": odoo_id,
                "last_hash": row_hash,
                "sync_state": sync_state,
            },
        )

    def prepare_vals(self, vals: Dict[str, Any]) -> Dict[str, Any]:
        """Hook: quitar claves internas ``_`` antes de enviar a Odoo."""
        return {k: v for k, v in vals.items() if not k.startswith("_")}

    def load_row(self, adminet_id: str, vals: Dict[str, Any], row: Dict[str, Any]) -> LoadResult:
        ref = vals.get("ref") or ref_adminet(self.entity_type, adminet_id)
        row_hash = row_payload_hash(row)
        mapping = self.resolve_mapping(adminet_id)

        if mapping and mapping.last_hash == row_hash and mapping.odoo_id:
            return LoadResult(adminet_id, "skipped", mapping.odoo_id)

        odoo_vals = self.prepare_vals(vals)
        try:
            odoo_id = mapping.odoo_id if mapping else None
            if not odoo_id:
                odoo_id = self._find_odoo_id_by_ref(ref)

            if odoo_id:
                self.client.write(self.odoo_model, [int(odoo_id)], odoo_vals)
                action = "updated"
            else:
                created = self.client.create(self.odoo_model, odoo_vals)
                odoo_id = int(created) if created else None
                action = "created"

            if odoo_id:
                self._save_mapping(adminet_id, ref, odoo_id, row_hash)
            return LoadResult(adminet_id, action, odoo_id)
        except Exception as exc:
            logger.warning("Error cargando %s %s: %s", self.entity_type, adminet_id, exc)
            if mapping:
                mapping.sync_state = MigrationEntityMapping.SyncState.ERROR
                mapping.save(update_fields=["sync_state", "updated_at"])
            return LoadResult(adminet_id, "error", error=str(exc)[:500])


class PartnerLoader(BaseOdooLoader):
    pass


class ProductCategoryLoader(BaseOdooLoader):
    def prepare_vals(self, vals: Dict[str, Any]) -> Dict[str, Any]:
        out = super().prepare_vals(vals)
        parent_rubro = vals.get("_parent_rubro_id")
        if parent_rubro and self.entity_type == "subrubro":
            parent_map = MigrationEntityMapping.objects.filter(
                conexion=self.connection,
                entity_type="rubro",
                adminet_id=str(parent_rubro),
            ).first()
            if parent_map and parent_map.odoo_id:
                out["parent_id"] = parent_map.odoo_id
        return out


class ProductTemplateLoader(BaseOdooLoader):
    def prepare_vals(self, vals: Dict[str, Any]) -> Dict[str, Any]:
        out = super().prepare_vals(vals)
        for field, entity in (
            ("_marca_adminet_id", "marca"),
            ("_uom_adminet_id", "uom"),
        ):
            adminet_ref = vals.get(field)
            if not adminet_ref:
                continue
            if entity == "marca":
                m = MigrationEntityMapping.objects.filter(
                    conexion=self.connection, entity_type="marca", adminet_id=str(adminet_ref)
                ).first()
                if m and m.odoo_id:
                    out["adm_brand_id"] = m.odoo_id
            elif entity == "uom":
                m = MigrationEntityMapping.objects.filter(
                    conexion=self.connection, entity_type="uom", adminet_id=str(adminet_ref)
                ).first()
                if m and m.odoo_id:
                    out["uom_id"] = m.odoo_id
        categ_id = vals.get("_subrubro_adminet_id") or vals.get("_rubro_adminet_id")
        entity = "subrubro" if vals.get("_subrubro_adminet_id") else "rubro"
        if categ_id:
            m = MigrationEntityMapping.objects.filter(
                conexion=self.connection, entity_type=entity, adminet_id=str(categ_id)
            ).first()
            if m and m.odoo_id:
                out["categ_id"] = m.odoo_id
        return out


class StockQuantLoader(BaseOdooLoader):
    """Registra intención de ajuste; aplicación real vía wizard Odoo en fase posterior."""

    def load_row(self, adminet_id: str, vals: Dict[str, Any], row: Dict[str, Any]) -> LoadResult:
        ref = vals.get("ref") or ref_adminet(self.entity_type, adminet_id)
        row_hash = row_payload_hash(row)
        mapping = self.resolve_mapping(adminet_id)
        if mapping and mapping.last_hash == row_hash:
            return LoadResult(adminet_id, "skipped", mapping.odoo_id)
        # Sin escritura directa en stock.quant: persistir mapping pendiente
        self._save_mapping(
            adminet_id,
            ref,
            mapping.odoo_id if mapping else 0,
            row_hash,
            sync_state=MigrationEntityMapping.SyncState.PENDIENTE,
        )
        return LoadResult(adminet_id, "pending_wizard", mapping.odoo_id if mapping else None)


class AccountMoveLoader(BaseOdooLoader):
    """Facturas históricas: solo registro de mapping + metadatos (sin postear en Odoo automáticamente)."""

    def load_row(self, adminet_id: str, vals: Dict[str, Any], row: Dict[str, Any]) -> LoadResult:
        if vals.get("_historico_sin_cae"):
            ref = vals.get("ref") or ref_adminet(self.entity_type, adminet_id)
            row_hash = row_payload_hash(row)
            mapping = self.resolve_mapping(adminet_id)
            if mapping and mapping.last_hash == row_hash:
                return LoadResult(adminet_id, "skipped", mapping.odoo_id)
            self._save_mapping(
                adminet_id,
                ref,
                mapping.odoo_id if mapping and mapping.odoo_id else 0,
                row_hash,
                sync_state=MigrationEntityMapping.SyncState.PENDIENTE,
            )
            return LoadResult(adminet_id, "pending_manual", mapping.odoo_id if mapping else None)
        return super().load_row(adminet_id, vals, row)


class PassthroughLoader(BaseOdooLoader):
    """Dominios de solo referencia (contribuyente → catálogo Odoo)."""

    def load_row(self, adminet_id: str, vals: Dict[str, Any], row: Dict[str, Any]) -> LoadResult:
        return LoadResult(adminet_id, "skipped")
