"""
Seed / ensure del informe Ventas marcas mensual.

Usado por la migración 0033 y en runtime si Staging/local no aplicó migrate
pero el Command Center ya enlaza al slug.
"""
from __future__ import annotations

from typing import Optional, Type

from django.db import connection
from django.utils import timezone

VENTAS_MARCAS_MENSUAL_SLUG = "ventas-marcas-mensual"


def _report_defaults():
    now = timezone.now()
    return {
        "name": "Ventas marcas mensual",
        "description": (
            "Matriz mensual vendedor → cliente por marca: unidades (packs o docenas) "
            "y facturación neta. Filtros por período, marca, SuperArt, sucursal y clientes/vendedores."
        ),
        "category": "operational",
        "config": {
            "metrics": ["unidades", "facturacion", "precio_medio"],
            "dimensions": ["vendedor", "cliente", "anio_mes"],
            "tags": ["ventas", "marcas", "mensual", "listados"],
            "catalog_legacy_section": "listados",
            "preset_hombre": {
                "id_manuales": [],
                "label": "Hombre",
                "nota": "Lista de id_manual SuperArt; editable en UI (Configurar preset) por supervisor.",
            },
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
                    "label": "Marcas",
                },
                "superarts_incluidos": {
                    "type": "multi_select",
                    "required": False,
                    "label": "SuperArt",
                },
                "modo_unidades": {
                    "type": "select",
                    "required": False,
                    "label": "Unidades",
                    "options": ["packs", "docenas"],
                    "default": "packs",
                },
                "modo_comparacion": {
                    "type": "select",
                    "required": False,
                    "label": "Modo marcas",
                    "options": ["una", "comparar"],
                    "default": "una",
                },
                "marca_a": {"type": "select", "required": False, "label": "Marca A"},
                "marca_b": {"type": "select", "required": False, "label": "Marca B"},
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


def seed_ventas_marcas_mensual_report(
    ReportDefinition: Type,
    ReportWidget: Type,
) -> object:
    """Crea o actualiza definición + widget (API usable desde migraciones históricas)."""
    defaults = _report_defaults()
    # Modelos históricos de migración pueden no tener is_visible en defaults
    try:
        report_def, _ = ReportDefinition.objects.update_or_create(
            slug=VENTAS_MARCAS_MENSUAL_SLUG,
            empresa=None,
            defaults=defaults,
        )
    except Exception:
        defaults.pop("is_visible", None)
        report_def, _ = ReportDefinition.objects.update_or_create(
            slug=VENTAS_MARCAS_MENSUAL_SLUG,
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
            [VENTAS_MARCAS_MENSUAL_SLUG],
        )
    except Exception:
        pass
    finally:
        cursor.close()

    ReportWidget.objects.filter(report=report_def).delete()
    ReportWidget.objects.create(
        report=report_def,
        name="Matriz ventas marcas",
        widget_type="table",
        order=1,
        layout={"w": 12, "h": 10},
        configuration={"view": "matriz_mensual"},
    )
    return report_def


def ensure_ventas_marcas_mensual_report() -> Optional[object]:
    """Runtime: asegura la fila global del informe si falta."""
    from reports.models import ReportDefinition, ReportWidget

    existing = ReportDefinition.objects.filter(
        slug=VENTAS_MARCAS_MENSUAL_SLUG,
        empresa__isnull=True,
        is_active=True,
    ).first()
    if existing:
        return existing
    return seed_ventas_marcas_mensual_report(ReportDefinition, ReportWidget)
