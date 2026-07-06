"""Registro de loaders por dominio."""

from __future__ import annotations

from typing import Type

from odoo_migracion.loaders.base import (
    AccountMoveLoader,
    BaseOdooLoader,
    PartnerLoader,
    PassthroughLoader,
    ProductCategoryLoader,
    ProductTemplateLoader,
    StockQuantLoader,
)
from odoo_migracion.models import OdooConnection
from odoo_migracion.services.odoo_client import OdooJson2Client


def get_loader_for_domain(
    domain_key: str,
    connection: OdooConnection,
    client: OdooJson2Client | None = None,
) -> BaseOdooLoader:
    from odoo_migracion.services.domains import DOMAIN_BY_KEY

    spec = DOMAIN_BY_KEY[domain_key]
    cls = _LOADER_CLASSES.get(domain_key, BaseOdooLoader)
    loader = cls(connection, client)
    loader.entity_type = spec.key
    loader.odoo_model = spec.odoo_model
    return loader


_LOADER_CLASSES: dict[str, Type[BaseOdooLoader]] = {
    "empresa": BaseOdooLoader,
    "contribuyente": PassthroughLoader,
    "uom": BaseOdooLoader,
    "rubro": ProductCategoryLoader,
    "subrubro": ProductCategoryLoader,
    "marca": BaseOdooLoader,
    "viajante": PartnerLoader,
    "deposito": BaseOdooLoader,
    "proveedor": PartnerLoader,
    "cliente": PartnerLoader,
    "articulo": ProductTemplateLoader,
    "stock_saldo": StockQuantLoader,
    "cuenta_cliente": AccountMoveLoader,
}
