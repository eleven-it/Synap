# -*- coding: utf-8 -*-
"""
Seed / ensure del informe Inventario por depósito (artículo × depósito).

Usado por migración 0038 y en runtime si Staging/local no aplicó migrate.
"""
from __future__ import annotations

from typing import Optional, Type

from django.db import connection
from django.utils import timezone

INVENTARIO_DEPOSITO_SLUG = "inventario-deposito-articulo"


def _report_defaults():
    now = timezone.now()
    return {
        "name": "Inventario por depósito",
        "description": (
            "Stock por depósito y artículo con medidas en unidades de inventario y docenas. "
            "Filtros por fecha de corte, depósitos, marcas y búsqueda de artículo."
        ),
        "category": "operational",
        "config": {
            "metrics": ["stock_um", "docenas"],
            "dimensions": ["deposito", "marca", "articulo", "talle"],
            "tags": ["mpr", "stock", "listados"],
            "catalog_legacy_section": "listados",
            "filters": {
                "fecha_corte": {
                    "type": "date",
                    "required": False,
                    "label": "Fecha de corte",
                },
                "depositos": {
                    "type": "multi_select",
                    "required": False,
                    "label": "Depósitos",
                },
                "marcas_incluidos": {
                    "type": "multi_select",
                    "required": False,
                    "label": "Marcas",
                },
                "q": {
                    "type": "text",
                    "required": False,
                    "label": "Buscar artículo",
                },
                "incluir_2da": {
                    "type": "boolean",
                    "required": False,
                    "label": "Incluir 2da selección",
                    "default": False,
                },
            },
        },
        "metadata": {
            "created_by": "system",
            "seeded_at": now.isoformat(),
            "catalog_legacy_section": "listados",
        },
        "refresh_interval": "daily",
        "is_active": True,
        "is_visible": True,
    }


def seed_inventario_deposito_report(
    ReportDefinition: Type,
    ReportWidget: Type,
) -> object:
    """Crea o actualiza definición + widget (API usable desde migraciones históricas)."""
    defaults = _report_defaults()
    try:
        report_def, _ = ReportDefinition.objects.update_or_create(
            slug=INVENTARIO_DEPOSITO_SLUG,
            empresa=None,
            defaults=defaults,
        )
    except Exception:
        defaults.pop("is_visible", None)
        report_def, _ = ReportDefinition.objects.update_or_create(
            slug=INVENTARIO_DEPOSITO_SLUG,
            empresa=None,
            defaults=defaults,
        )

    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            UPDATE reports_reportdefinition
            SET show_in_catalog = TRUE
            WHERE slug = %s AND empresa_id IS NULL
            """,
            [INVENTARIO_DEPOSITO_SLUG],
        )
    except Exception:
        pass
    finally:
        cursor.close()

    ReportWidget.objects.filter(report=report_def).delete()
    ReportWidget.objects.create(
        report=report_def,
        name="Inventario por depósito",
        widget_type="table",
        order=1,
        layout={"w": 12, "h": 10},
        configuration={"view": "inventario_deposito"},
    )
    return report_def


def ensure_inventario_deposito_report() -> Optional[object]:
    """Runtime: asegura la fila global del informe si falta."""
    from reports.models import ReportDefinition, ReportWidget

    existing = ReportDefinition.objects.filter(
        slug=INVENTARIO_DEPOSITO_SLUG,
        empresa__isnull=True,
        is_active=True,
    ).first()
    if existing:
        return existing
    return seed_inventario_deposito_report(ReportDefinition, ReportWidget)
