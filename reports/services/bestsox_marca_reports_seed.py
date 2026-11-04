# -*- coding: utf-8 -*-
"""Seed de informes BestSox: Producción, Compras, Consignación."""
from __future__ import annotations

from typing import Optional, Type

from django.db import connection
from django.utils import timezone

PRODUCCION_MARCA_SUPERART_SLUG = "produccion-marca-superart"
COMPRAS_MARCA_SUPERART_SLUG = "compras-marca-superart"
CONSIGNACION_STOCK_SLUG = "consignacion-stock"


def _filtros_periodo_marca():
    return {
        "fecha_inicio": {"type": "date", "required": False, "label": "Desde"},
        "fecha_fin": {"type": "date", "required": False, "label": "Hasta"},
        "marcas_incluidos": {"type": "multi_select", "required": False, "label": "Marcas"},
        "marcas_excluidos": {"type": "multi_select", "required": False, "label": "Marcas excluidas"},
        "q_superart": {"type": "multi_select", "required": False, "label": "Superartículos"},
        "superarts_excluidos": {"type": "multi_select", "required": False, "label": "Superartículos excluidos"},
    }


def _persist_catalog(slug: str) -> None:
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            UPDATE reports_reportdefinition
            SET show_in_catalog = TRUE
            WHERE slug = %s AND empresa_id IS NULL
            """,
            [slug],
        )
    except Exception:
        pass
    finally:
        cursor.close()


def _seed_one(
    ReportDefinition: Type,
    ReportWidget: Type,
    *,
    slug: str,
    name: str,
    description: str,
    tags: list,
    view: str,
    legacy_order: int,
    extra_filters: Optional[dict] = None,
) -> object:
    now = timezone.now()
    filters = _filtros_periodo_marca()
    if extra_filters:
        filters.update(extra_filters)
    defaults = {
        "name": name,
        "description": description,
        "category": "operational",
        "config": {
            "metrics": [],
            "dimensions": ["marca", "superart", "articulo", "mes"],
            "tags": tags,
            "catalog_legacy_section": "listados",
            "catalog_legacy_order": legacy_order,
            "filters": filters,
        },
        "metadata": {
            "created_by": "system",
            "seeded_at": now.isoformat(),
            "catalog_legacy_section": "listados",
            "catalog_legacy_order": legacy_order,
        },
        "refresh_interval": "daily",
        "is_active": True,
        "is_visible": True,
        "show_in_catalog": True,
    }
    try:
        report_def, _ = ReportDefinition.objects.update_or_create(
            slug=slug,
            empresa=None,
            defaults=defaults,
        )
    except Exception:
        defaults.pop("is_visible", None)
        report_def, _ = ReportDefinition.objects.update_or_create(
            slug=slug,
            empresa=None,
            defaults=defaults,
        )
    _persist_catalog(slug)
    ReportWidget.objects.filter(report=report_def).delete()
    ReportWidget.objects.create(
        report=report_def,
        name=name,
        widget_type="table",
        order=1,
        layout={"w": 12, "h": 10},
        configuration={"view": view},
    )
    return report_def


def seed_produccion_marca_superart_report(ReportDefinition: Type, ReportWidget: Type) -> object:
    return _seed_one(
        ReportDefinition,
        ReportWidget,
        slug=PRODUCCION_MARCA_SUPERART_SLUG,
        name="Producción por marca y SuperArtículo",
        description=(
            "Producción de 1ra (MPR Producción→Semi elaborado) y fasón Tejeduría en depósito semi, "
            "por marca y superartículo con columnas mensuales (pares y docenas)."
        ),
        tags=["mpr", "produccion", "marca", "superart", "listados", "bestsox"],
        view="produccion_marca_superart",
        legacy_order=36,
    )


def seed_compras_marca_superart_report(ReportDefinition: Type, ReportWidget: Type) -> object:
    return _seed_one(
        ReportDefinition,
        ReportWidget,
        slug=COMPRAS_MARCA_SUPERART_SLUG,
        name="Compras por marca y SuperArtículo",
        description=(
            "Ingresos de producto terminado de terceros (compras, remitos e ingresos internos identificados), "
            "agrupados por marca y superartículo (packs, prendas, docenas)."
        ),
        tags=["compras", "marca", "superart", "listados", "bestsox"],
        view="compras_marca_superart",
        legacy_order=37,
    )


def seed_consignacion_stock_report(ReportDefinition: Type, ReportWidget: Type) -> object:
    return _seed_one(
        ReportDefinition,
        ReportWidget,
        slug=CONSIGNACION_STOCK_SLUG,
        name="Stock en consignación",
        description=(
            "Mercadería en poder del cliente: remitos en consignación menos facturado y devuelto, "
            "por cliente, marca y superartículo, con detalle de remitos."
        ),
        tags=["ventas", "consignacion", "marca", "superart", "listados", "bestsox"],
        view="consignacion_stock",
        legacy_order=38,
        extra_filters={
            "corte_facturas": {
                "type": "date",
                "required": False,
                "label": "Corte facturas/devoluciones",
            },
        },
    )


def seed_all_bestsox_marca_reports(ReportDefinition: Type, ReportWidget: Type) -> None:
    seed_produccion_marca_superart_report(ReportDefinition, ReportWidget)
    seed_compras_marca_superart_report(ReportDefinition, ReportWidget)
    seed_consignacion_stock_report(ReportDefinition, ReportWidget)


def ensure_produccion_marca_superart_report():
    from reports.models import ReportDefinition, ReportWidget

    existing = ReportDefinition.objects.filter(
        slug=PRODUCCION_MARCA_SUPERART_SLUG, empresa__isnull=True, is_active=True
    ).first()
    return existing or seed_produccion_marca_superart_report(ReportDefinition, ReportWidget)


def ensure_compras_marca_superart_report():
    from reports.models import ReportDefinition, ReportWidget

    existing = ReportDefinition.objects.filter(
        slug=COMPRAS_MARCA_SUPERART_SLUG, empresa__isnull=True, is_active=True
    ).first()
    return existing or seed_compras_marca_superart_report(ReportDefinition, ReportWidget)


def ensure_consignacion_stock_report():
    from reports.models import ReportDefinition, ReportWidget

    existing = ReportDefinition.objects.filter(
        slug=CONSIGNACION_STOCK_SLUG, empresa__isnull=True, is_active=True
    ).first()
    return existing or seed_consignacion_stock_report(ReportDefinition, ReportWidget)
