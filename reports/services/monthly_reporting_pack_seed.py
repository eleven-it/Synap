# -*- coding: utf-8 -*-
"""Definición y seed de los 6 packs Monthly Reporting."""
from __future__ import annotations

from decimal import Decimal
from typing import Iterable, Type

MONTHLY_REPORTING_PACK_DEFINITIONS: tuple[dict, ...] = (
    {
        "pack_id": "levis_bw",
        "codigo_salida": "LB",
        "marca_anet": "LB",
        "product_group": "Bodywear",
        "template_family": "levis",
        "unit_mode": "dozens",
        "royalty_rate": Decimal("0.200000"),
    },
    {
        "pack_id": "levis_lw_dz",
        "codigo_salida": "LEV",
        "marca_anet": "LEV",
        "product_group": "Legwear",
        "template_family": "levis",
        "unit_mode": "dozens",
        "royalty_rate": Decimal("0.200000"),
    },
    {
        "pack_id": "levis_lw_pk",
        "codigo_salida": "LEV",
        "marca_anet": "LEV",
        "product_group": "Legwear",
        "template_family": "levis",
        "unit_mode": "packs",
        "royalty_rate": Decimal("0.200000"),
    },
    {
        "pack_id": "lw_propia",
        "codigo_salida": "PUM",
        "marca_anet": "PUM",
        "product_group": "LW",
        "template_family": "lw",
        "unit_mode": "dozens",
        "royalty_rate": Decimal("0.130000"),
    },
    {
        "pack_id": "puma_bw",
        "codigo_salida": "PUW",
        "marca_anet": "PUW",
        "product_group": "Men BW",
        "template_family": "puma",
        "unit_mode": "packs",
        "royalty_rate": Decimal("0.130000"),
    },
    {
        "pack_id": "puma_sw",
        "codigo_salida": "PUS",
        "marca_anet": "PUS",
        "product_group": "Men SW / Women SW",
        "template_family": "puma",
        "unit_mode": "packs",
        "royalty_rate": Decimal("0.130000"),
    },
)

MONTHLY_REPORTING_TEMPLATE_FILES: dict[str, str] = {
    "levis_bw": "levis_bw_annual.xlsx",
    "levis_lw_dz": "levis_lw_dz_annual.xlsx",
    "levis_lw_pk": "levis_lw_pk_annual.xlsx",
    "lw_propia": "lw_propia_annual.xlsx",
    "puma_bw": "puma_bw_annual.xlsx",
    "puma_sw": "puma_sw_annual.xlsx",
}


def seed_monthly_reporting_packs(MonthlyReportingPack: Type) -> list[object]:
    """Crea o actualiza los 6 packs canónicos."""
    created: list[object] = []
    for definition in MONTHLY_REPORTING_PACK_DEFINITIONS:
        pack, _ = MonthlyReportingPack.objects.update_or_create(
            pack_id=definition["pack_id"],
            defaults={
                **definition,
                "config_version": 1,
                "active": True,
            },
        )
        created.append(pack)
    return created


def iter_monthly_reporting_pack_ids() -> Iterable[str]:
    for definition in MONTHLY_REPORTING_PACK_DEFINITIONS:
        yield definition["pack_id"]
