# -*- coding: utf-8 -*-
"""
Seed / ensure del informe Ventas Mensuales Licenciatarios.

Hermano de ventas-marcas-mensual: pack Monthly Reporting a marcas.
"""
from __future__ import annotations

from typing import Optional, Type

from django.db import connection
from django.utils import timezone

VENTAS_MENSUALES_LICENCIATARIOS_SLUG = "ventas-mensuales-licenciatarios"


def _report_defaults():
    now = timezone.now()
    return {
        "name": "Ventas Mensuales Licenciatarios",
        "description": (
            "Pack Monthly Reporting por marca/línea (Levi’s, Puma, LW): "
            "detalle cliente×mes + resumen FY y regalías. "
            "Datos híbridos: seed histórico + AdministraNET desde el cutover."
        ),
        "category": "operational",
        "config": {
            "metrics": ["unidades", "facturacion", "regalias"],
            "dimensions": ["cliente", "anio_mes", "pack"],
            "tags": ["ventas", "licenciatarios", "mensual", "listados", "marcas"],
            "catalog_legacy_section": "listados",
            "sibling_of": "ventas-marcas-mensual",
            "cutover_date": "2026-07-22",
            "packs": [
                "levis_bw",
                "levis_lw_dz",
                "levis_lw_pk",
                "lw_propia",
                "puma_bw",
                "puma_sw",
            ],
            "filters": {
                "pack_id": {
                    "type": "select",
                    "required": True,
                    "label": "Pack licenciatario",
                    "options": [
                        "levis_bw",
                        "levis_lw_dz",
                        "levis_lw_pk",
                        "lw_propia",
                        "puma_bw",
                        "puma_sw",
                    ],
                },
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
            },
        },
        "metadata": {
            "created_by": "system",
            "seeded_at": now.isoformat(),
            "catalog_legacy_section": "listados",
            "phase": "0_stub",
        },
        "refresh_interval": "daily",
        "is_active": True,
        "is_visible": True,
    }


def seed_ventas_mensuales_licenciatarios_report(
    ReportDefinition: Type,
    ReportWidget: Type,
) -> object:
    """Crea o actualiza definición + widget."""
    defaults = _report_defaults()
    try:
        report_def, _ = ReportDefinition.objects.update_or_create(
            slug=VENTAS_MENSUALES_LICENCIATARIOS_SLUG,
            empresa=None,
            defaults=defaults,
        )
    except Exception:
        defaults.pop("is_visible", None)
        report_def, _ = ReportDefinition.objects.update_or_create(
            slug=VENTAS_MENSUALES_LICENCIATARIOS_SLUG,
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
            [VENTAS_MENSUALES_LICENCIATARIOS_SLUG],
        )
    except Exception:
        pass
    finally:
        cursor.close()

    ReportWidget.objects.filter(report=report_def).delete()
    ReportWidget.objects.create(
        report=report_def,
        name="Monthly Reporting licenciatarios",
        widget_type="table",
        order=1,
        layout={"w": 12, "h": 8},
        configuration={"view": "monthly_reporting_stub"},
    )
    return report_def


def ensure_ventas_mensuales_licenciatarios_report() -> Optional[object]:
    """Runtime: asegura la fila global del informe si falta."""
    from reports.models import ReportDefinition, ReportWidget

    existing = ReportDefinition.objects.filter(
        slug=VENTAS_MENSUALES_LICENCIATARIOS_SLUG,
        empresa__isnull=True,
        is_active=True,
    ).first()
    if existing:
        return existing
    return seed_ventas_mensuales_licenciatarios_report(ReportDefinition, ReportWidget)
