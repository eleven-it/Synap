"""
Seed / ensure del informe Ventas por marca y SuperArt.

Usado por la migración 0036 y en runtime si Staging/local no aplicó migrate
pero el Command Center ya enlaza al slug.
"""
from __future__ import annotations

from typing import Optional, Type

from django.db import connection
from django.utils import timezone

VENTAS_MARCA_SUPERART_SLUG = "ventas-marca-superart"


def _report_defaults():
    now = timezone.now()
    return {
        "name": "Ventas por marca y SuperArt",
        "description": (
            "Ventas del período agrupadas Marca → SuperArt → Artículo "
            "con packs, docenas y facturación neta."
        ),
        "category": "operational",
        "config": {
            "metrics": ["packs", "docenas", "facturacion"],
            "dimensions": ["marca", "superart", "articulo"],
            "tags": ["ventas", "marcas", "superart", "listados"],
            "catalog_legacy_section": "listados",
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
                "superarts_incluidos": {
                    "type": "multi_select",
                    "required": False,
                    "label": "SuperArt",
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


def seed_ventas_marca_superart_report(
    ReportDefinition: Type,
    ReportWidget: Type,
) -> object:
    """Crea o actualiza definición + widget (API usable desde migraciones históricas)."""
    defaults = _report_defaults()
    try:
        report_def, _ = ReportDefinition.objects.update_or_create(
            slug=VENTAS_MARCA_SUPERART_SLUG,
            empresa=None,
            defaults=defaults,
        )
    except Exception:
        defaults.pop("is_visible", None)
        report_def, _ = ReportDefinition.objects.update_or_create(
            slug=VENTAS_MARCA_SUPERART_SLUG,
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
            [VENTAS_MARCA_SUPERART_SLUG],
        )
    except Exception:
        pass
    finally:
        cursor.close()

    ReportWidget.objects.filter(report=report_def).delete()
    ReportWidget.objects.create(
        report=report_def,
        name="Jerarquía marca SuperArt",
        widget_type="table",
        order=1,
        layout={"w": 12, "h": 10},
        configuration={"view": "marca_superart_jerarquia"},
    )
    return report_def


def ensure_ventas_marca_superart_report() -> Optional[object]:
    """Runtime: asegura la fila global del informe si falta."""
    from reports.models import ReportDefinition, ReportWidget

    existing = ReportDefinition.objects.filter(
        slug=VENTAS_MARCA_SUPERART_SLUG,
        empresa__isnull=True,
        is_active=True,
    ).first()
    if existing:
        return existing
    return seed_ventas_marca_superart_report(ReportDefinition, ReportWidget)
