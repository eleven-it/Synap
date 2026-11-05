# -*- coding: utf-8 -*-
"""Seed del informe Salidas por marca y SuperArtículo."""
from __future__ import annotations

from typing import Optional, Type

from django.db import connection
from django.utils import timezone

SALIDAS_MARCA_SUPERART_SLUG = "salidas-marca-superart"


def _report_defaults():
    now = timezone.now()
    return {
        "name": "Salidas por marca y SuperArtículo",
        "description": (
            "Salidas netas de producto terminado (depósito Terminado): remitos de salida, "
            "facturas directas y devoluciones NCA, agrupadas por marca, superartículo y mes."
        ),
        "category": "operational",
        "config": {
            "metrics": [],
            "dimensions": ["marca", "superart", "articulo", "mes", "via_trazabilidad"],
            "tags": ["salidas", "marcas", "superart", "bestsox", "listados", "stock"],
            "catalog_legacy_section": "listados",
            "filters": {
                "fecha_inicio": {"type": "date", "required": False, "label": "Desde"},
                "fecha_fin": {"type": "date", "required": False, "label": "Hasta"},
                "marcas_incluidos": {"type": "multi_select", "required": False, "label": "Marcas"},
                "q_superart": {"type": "multi_select", "required": False, "label": "Superartículos"},
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


def seed_salidas_marca_superart_report(
    ReportDefinition: Type,
    ReportWidget: Type,
) -> object:
    defaults = _report_defaults()
    try:
        report_def, _ = ReportDefinition.objects.update_or_create(
            slug=SALIDAS_MARCA_SUPERART_SLUG,
            empresa=None,
            defaults=defaults,
        )
    except Exception:
        defaults.pop("is_visible", None)
        report_def, _ = ReportDefinition.objects.update_or_create(
            slug=SALIDAS_MARCA_SUPERART_SLUG,
            empresa=None,
            defaults=defaults,
        )

    cfg = dict(report_def.config or {})
    cfg["metrics"] = []
    report_def.config = cfg
    report_def.save(update_fields=["config"])

    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            UPDATE reports_reportdefinition
            SET show_in_catalog = TRUE
            WHERE slug = %s AND empresa_id IS NULL
            """,
            [SALIDAS_MARCA_SUPERART_SLUG],
        )
    except Exception:
        pass
    finally:
        cursor.close()

    ReportWidget.objects.filter(report=report_def).delete()
    ReportWidget.objects.create(
        report=report_def,
        name="Salidas por marca y SuperArtículo",
        widget_type="table",
        order=1,
        layout={"w": 12, "h": 10},
        configuration={"view": "salidas_marca_superart"},
    )
    return report_def


def ensure_salidas_marca_superart_report() -> Optional[object]:
    from reports.models import ReportDefinition, ReportWidget

    existing = ReportDefinition.objects.filter(
        slug=SALIDAS_MARCA_SUPERART_SLUG,
        empresa__isnull=True,
        is_active=True,
    ).first()
    if existing:
        return existing
    return seed_salidas_marca_superart_report(ReportDefinition, ReportWidget)
