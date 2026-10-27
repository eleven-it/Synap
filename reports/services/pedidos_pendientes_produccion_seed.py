# -*- coding: utf-8 -*-
"""Seed del informe Pedidos pendientes — Producción / MPR."""
from __future__ import annotations

from typing import Optional, Type

from django.db import connection
from django.utils import timezone

PEDIDOS_PENDIENTES_PRODUCCION_SLUG = "pedidos-pendientes-produccion"


def _report_defaults():
    now = timezone.now()
    return {
        "name": "Pedidos pendientes (Producción)",
        "description": (
            "Pedido pendiente bruto y MPR demanda (saldo neto tras remitos) por artículo, con stock "
            "terminado/producción y columnas MPR (reserva, disponible, reposición, a fabricar). "
            "Filtros por marca y cliente."
        ),
        "category": "operational",
        "config": {
            # Sin métricas de catálogo: los KPI van solo en la sección clara del informe (no resumen genérico).
            "metrics": [],
            "dimensions": ["articulo", "marca"],
            "tags": ["mpr", "pedidos", "produccion", "stock", "listados"],
            "catalog_legacy_section": "listados",
            "filters": {
                "fecha_inicio": {"type": "date", "required": True, "label": "Fecha inicio"},
                "fecha_fin": {"type": "date", "required": True, "label": "Fecha fin"},
                "criterio_pendiente": {
                    "type": "select",
                    "required": False,
                    "label": "Criterio de pendiente",
                    "default": "backorder",
                    "options": [
                        "backorder",
                        "saldo_comercial",
                        "en_preparacion",
                        "saldo_no_entregado",
                    ],
                },
                "marcas_incluidos": {"type": "multi_select", "required": False, "label": "Marcas"},
                "marcas_excluidos": {"type": "multi_select", "required": False, "label": "Marcas excluidas"},
                "clientes_incluir": {"type": "multi_select", "required": False, "label": "Clientes"},
                "clientes_excluidos": {"type": "multi_select", "required": False, "label": "Clientes excluidos"},
                "solo_terminados": {
                    "type": "boolean",
                    "required": False,
                    "label": "Solo artículos terminados (tipo_art_fab)",
                    "default": True,
                },
            },
        },
        "metadata": {
            "created_by": "system",
            "seeded_at": now.isoformat(),
            "catalog_legacy_section": "listados",
            "assumptions": [
                "Pedido pendiente = bruto PED Pendiente (SUM stockp.Cantidad).",
                "MPR demanda = saldo por pedido+artículo (pedido − remitos vía stock.codmov_pedido/remito); MPR derivados usan saldo.",
                "Stock terminado = depósitos Terminado/Consignación; stock producción = armable semi (informativo).",
                "A fabricar = max(0, demanda + reserva − terminado) = backorder + reposición reserva.",
                "Importe neto sin IVA ni descuento de cabecera.",
            ],
        },
        "refresh_interval": "daily",
        "is_active": True,
        "is_visible": True,
    }


def seed_pedidos_pendientes_produccion_report(
    ReportDefinition: Type,
    ReportWidget: Type,
) -> object:
    defaults = _report_defaults()
    try:
        report_def, _ = ReportDefinition.objects.update_or_create(
            slug=PEDIDOS_PENDIENTES_PRODUCCION_SLUG,
            empresa=None,
            defaults=defaults,
        )
    except Exception:
        defaults.pop("is_visible", None)
        report_def, _ = ReportDefinition.objects.update_or_create(
            slug=PEDIDOS_PENDIENTES_PRODUCCION_SLUG,
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
            [PEDIDOS_PENDIENTES_PRODUCCION_SLUG],
        )
    except Exception:
        pass
    finally:
        cursor.close()

    ReportWidget.objects.filter(report=report_def).delete()
    ReportWidget.objects.create(
        report=report_def,
        name="Pedidos pendientes producción",
        widget_type="table",
        order=1,
        layout={"w": 12, "h": 10},
        configuration={"view": "pedidos_pendientes_produccion"},
    )
    return report_def


def ensure_pedidos_pendientes_produccion_report() -> Optional[object]:
    from reports.models import ReportDefinition, ReportWidget

    existing = ReportDefinition.objects.filter(
        slug=PEDIDOS_PENDIENTES_PRODUCCION_SLUG,
        empresa__isnull=True,
        is_active=True,
    ).first()
    if existing:
        return existing
    return seed_pedidos_pendientes_produccion_report(ReportDefinition, ReportWidget)
