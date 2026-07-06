"""Identificadores externos AdministraNET ↔ Odoo (idempotencia)."""

from __future__ import annotations


MODULE_XML = "adminet_mig"


def ref_adminet(entity_type: str, adminet_id: str | int) -> str:
    """Referencia legible en campo ``ref`` de Odoo."""
    return f"adminet/{entity_type}/{adminet_id}"


def xml_id_name(entity_type: str, adminet_id: str | int) -> str:
    """Nombre de ``ir.model.data`` (módulo ``adminet_mig``)."""
    safe = str(adminet_id).replace(".", "_").replace("-", "_")
    return f"{entity_type}_{safe}"


def full_xml_id(entity_type: str, adminet_id: str | int) -> str:
    return f"{MODULE_XML}.{xml_id_name(entity_type, adminet_id)}"
