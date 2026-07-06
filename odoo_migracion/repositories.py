"""
Repositorios de lectura MySQL AdministraNET.
Delegación a extractores por dominio.
"""

from odoo_migracion.extractors import (
    ArticuloExtractor,
    ClienteExtractor,
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
from odoo_migracion.extractors.discovery import run_discovery

__all__ = [
    "run_discovery",
    "EmpresaExtractor",
    "RubroExtractor",
    "SubrubroExtractor",
    "MarcaExtractor",
    "ViajanteExtractor",
    "DepositoExtractor",
    "UomExtractor",
    "ProveedorExtractor",
    "ClienteExtractor",
    "ArticuloExtractor",
    "StockSaldoExtractor",
    "CuentaClienteAbiertaExtractor",
]
