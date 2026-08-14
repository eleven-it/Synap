# -*- coding: utf-8 -*-
"""
Seed / ensure del informe Ventas BOM en docenas.
"""
from __future__ import annotations

from typing import Optional, Type

from django.db import connection
from django.utils import timezone

from reports.services.ventas_bom_docenas_rules import VENTAS_BOM_DOCENAS_SLUG


def _report_defaults():
    now = timezone.now()
    return {
        "name": "Ventas BOM en docenas",
        "description": (
            "Artículos BOM (componentes) con salida atribuible a venta facturada: "
            "packs explosionados por receta, en docenas y pares."
        ),
        "category": "operational",
        "config": {
            "metrics": ["pares", "docenas", "articulos_bom"],
            "dimensions": ["articulo_bom", "marca"],
            "tags": ["ventas", "bom", "docenas", "fabricados", "listados"],
            "catalog_legacy_section": "listados",
            "catalog_legacy_order": 45,
            "filters": {
                "fecha_inicio_facturacion": {
                    "type": "date",
                    "required": True,
                    "label": "Fecha inicio",
                },
                "fecha_fin_facturacion": {
                    "type": "date",
                    "required": True,
                    "label": "Fecha fin",
                },
                "sucursales": {
                    "type": "multi_select",
                    "required": False,
                    "label": "Sucursales",
                },
                "punto_venta": {
                    "type": "multi_select",
                    "required": False,
                    "label": "Punto de venta",
                },
                "clientes_excluidos": {
                    "type": "multi_select",
                    "required": False,
                    "label": "Clientes a excluir",
                },
                "clientes_incluir": {
                    "type": "multi_select",
                    "required": False,
                    "label": "Clientes a incluir",
                },
                "marcas_incluidos": {
                    "type": "multi_select",
                    "required": False,
                    "label": "Marcas incluir",
                },
                "marcas_excluidos": {
                    "type": "multi_select",
                    "required": False,
                    "label": "Marcas excluir",
                },
                "rubros_incluidos": {
                    "type": "multi_select",
                    "required": False,
                    "label": "Rubros incluir",
                },
                "rubros_excluidos": {
                    "type": "multi_select",
                    "required": False,
                    "label": "Rubros excluir",
                },
                "subrubros_incluidos": {
                    "type": "multi_select",
                    "required": False,
                    "label": "Subrubros incluir",
                },
                "subrubros_excluidos": {
                    "type": "multi_select",
                    "required": False,
                    "label": "Subrubros excluir",
                },
            },
        },
        "metadata": {
            "created_by": "system",
            "seeded_at": now.isoformat(),
            "catalog_legacy_section": "listados",
            "related_docs": [
                "docs/reports/SPEC_INFORME_VENTAS_BOM_DOCENAS.md",
                "docs/reports/DESIGN_INFORME_VENTAS_BOM_DOCENAS.md",
            ],
        },
        "refresh_interval": "daily",
        "is_active": True,
        "is_visible": True,
    }


def seed_ventas_bom_docenas_report(
    ReportDefinition: Type,
    ReportWidget: Type,
) -> object:
    defaults = _report_defaults()
    try:
        report_def, _ = ReportDefinition.objects.update_or_create(
            slug=VENTAS_BOM_DOCENAS_SLUG,
            empresa=None,
            defaults=defaults,
        )
    except Exception:
        defaults.pop("is_visible", None)
        report_def, _ = ReportDefinition.objects.update_or_create(
            slug=VENTAS_BOM_DOCENAS_SLUG,
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
            [VENTAS_BOM_DOCENAS_SLUG],
        )
    except Exception:
        pass
    finally:
        cursor.close()

    ReportWidget.objects.filter(report=report_def).delete()
    ReportWidget.objects.create(
        report=report_def,
        name="Artículos BOM en docenas",
        widget_type="table",
        order=1,
        layout={"w": 12, "h": 10},
        configuration={
            "view": "ventas_bom_docenas_tabla",
            "table_dimensions": ["codigo_articulo", "nombre_articulo", "nombre_marca"],
            "table_metrics": ["pares", "docenas"],
        },
    )
    return report_def


def ensure_ventas_bom_docenas_report() -> Optional[object]:
    """Runtime: asegura la fila global del informe si falta."""
    from reports.models import ReportDefinition, ReportWidget

    existing = ReportDefinition.objects.filter(
        slug=VENTAS_BOM_DOCENAS_SLUG, empresa__isnull=True
    ).first()
    if existing:
        return existing
    return seed_ventas_bom_docenas_report(ReportDefinition, ReportWidget)
