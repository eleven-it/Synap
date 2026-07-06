"""Registro de dominios de migración (orden DAG)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Type

from odoo_migracion.extractors.base import BaseExtractor
from odoo_migracion.extractors import (
    ArticuloExtractor,
    ClienteExtractor,
    ContribuyenteExtractor,
    CuentaClienteAbiertaExtractor,
    DepositoExtractor,
    EmpresaExtractor,
    MarcaExtractor,
    ProveedorExtractor,
    RubroExtractor,
    StockSaldoExtractor,
    SubrubroExtractor,
    UomExtractor,
    ViajanteExtractor,
)
from odoo_migracion.mappers import (
    map_articulo,
    map_cliente,
    map_cuenta_cliente,
    map_deposito,
    map_empresa,
    map_marca,
    map_proveedor,
    map_rubro,
    map_stock_saldo,
    map_subrubro,
    map_uom,
    map_viajante,
)


def _map_contribuyente_passthrough(row):
    aid = str(row.get("idIVA") or row.get("id_iva") or "")
    return aid, {}


@dataclass(frozen=True)
class DomainSpec:
    key: str
    label: str
    orden: int
    extractor_cls: Type[BaseExtractor]
    mapper: Callable
    odoo_model: str
    fase: str
    master_system: str = "adminet"  # adminet | odoo | dual


DOMAIN_SPECS: list[DomainSpec] = [
    DomainSpec("empresa", "Datos empresa", 10, EmpresaExtractor, map_empresa, "res.company", "F3"),
    DomainSpec("contribuyente", "Condición IVA", 20, ContribuyenteExtractor, _map_contribuyente_passthrough, "l10n_ar.afip.responsibility.type", "F3", "odoo"),
    DomainSpec("uom", "Unidades de medida", 30, UomExtractor, map_uom, "uom.uom", "F3"),
    DomainSpec("rubro", "Rubros", 40, RubroExtractor, map_rubro, "product.category", "F3"),
    DomainSpec("subrubro", "Subrubros", 50, SubrubroExtractor, map_subrubro, "product.category", "F3"),
    DomainSpec("marca", "Marcas", 60, MarcaExtractor, map_marca, "adm.product.brand", "F3"),
    DomainSpec("viajante", "Vendedores", 70, ViajanteExtractor, map_viajante, "res.partner", "F3"),
    DomainSpec("deposito", "Depósitos", 80, DepositoExtractor, map_deposito, "stock.warehouse", "F4"),
    DomainSpec("proveedor", "Proveedores", 90, ProveedorExtractor, map_proveedor, "res.partner", "F3"),
    DomainSpec("cliente", "Clientes", 100, ClienteExtractor, map_cliente, "res.partner", "F3"),
    DomainSpec("articulo", "Artículos", 110, ArticuloExtractor, map_articulo, "product.template", "F4"),
    DomainSpec("stock_saldo", "Saldos stock", 120, StockSaldoExtractor, map_stock_saldo, "stock.quant", "F4", "adminet"),
    DomainSpec("cuenta_cliente", "Facturas CC abiertas", 130, CuentaClienteAbiertaExtractor, map_cuenta_cliente, "account.move", "F5", "adminet"),
]

DOMAIN_BY_KEY = {s.key: s for s in DOMAIN_SPECS}


def ordered_domain_keys() -> list[str]:
    return [s.key for s in sorted(DOMAIN_SPECS, key=lambda x: x.orden)]
