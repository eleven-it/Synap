"""Reglas de convivencia AdministraNET ↔ Odoo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from odoo_migracion.services.domains import DOMAIN_SPECS


@dataclass(frozen=True)
class CoexistenceRule:
    dominio: str
    sistema_maestro: str
    descripcion: str
    sync_direccion: str  # adminet_to_odoo | odoo_to_adminet | snapshot | manual


COEXISTENCE_RULES: List[CoexistenceRule] = [
    CoexistenceRule(
        "empresa",
        "adminet",
        "Datos fiscales de empresa: AdministraNET maestro hasta cutover.",
        "adminet_to_odoo",
    ),
    CoexistenceRule(
        "cliente",
        "adminet",
        "Altas y modificaciones de clientes en AdministraNET; sync incremental a Odoo.",
        "adminet_to_odoo",
    ),
    CoexistenceRule(
        "proveedor",
        "adminet",
        "Proveedores maestros en AdministraNET.",
        "adminet_to_odoo",
    ),
    CoexistenceRule(
        "articulo",
        "adminet",
        "Catálogo de artículos maestro en AdministraNET.",
        "adminet_to_odoo",
    ),
    CoexistenceRule(
        "stock_saldo",
        "adminet",
        "Un solo sistema mueve inventario; el otro recibe snapshots. Ajustes Odoo vía wizard.",
        "snapshot",
    ),
    CoexistenceRule(
        "cuenta_cliente",
        "adminet",
        "No re-emitir CAE. Solo histórico + saldos abiertos en Odoo.",
        "manual",
    ),
]


def rules_for_domain(dominio: str) -> CoexistenceRule | None:
    for r in COEXISTENCE_RULES:
        if r.dominio == dominio:
            return r
    for spec in DOMAIN_SPECS:
        if spec.key == dominio:
            return CoexistenceRule(
                spec.key,
                spec.master_system,
                f"Dominio {spec.label}",
                "adminet_to_odoo" if spec.master_system == "adminet" else "manual",
            )
    return None
