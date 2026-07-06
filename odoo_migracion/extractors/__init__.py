"""Extractores MySQL por dominio de migración."""

from odoo_migracion.extractors.empresa import EmpresaExtractor
from odoo_migracion.extractors.maestros import (
    ContribuyenteExtractor,
    DepositoExtractor,
    MarcaExtractor,
    RubroExtractor,
    SubrubroExtractor,
    UomExtractor,
    ViajanteExtractor,
)
from odoo_migracion.extractors.partners import ClienteExtractor, ProveedorExtractor
from odoo_migracion.extractors.productos import ArticuloExtractor
from odoo_migracion.extractors.stock import StockSaldoExtractor
from odoo_migracion.extractors.cuenta_cliente import CuentaClienteAbiertaExtractor

__all__ = [
    "EmpresaExtractor",
    "ContribuyenteExtractor",
    "UomExtractor",
    "RubroExtractor",
    "SubrubroExtractor",
    "MarcaExtractor",
    "ViajanteExtractor",
    "DepositoExtractor",
    "ProveedorExtractor",
    "ClienteExtractor",
    "ArticuloExtractor",
    "StockSaldoExtractor",
    "CuentaClienteAbiertaExtractor",
]
