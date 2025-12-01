from django.db import migrations
from django.utils import timezone


def create_pending_orders_report(apps, schema_editor):
    """Crea el reporte de Pedidos pendientes."""
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")

    now = timezone.now()

    report_def, _ = ReportDefinition.objects.update_or_create(
        slug="pending_orders",
        empresa=None,
        defaults={
            "name": "Pedidos pendientes",
            "description": "Listado de pedidos pendientes de preparación. Muestra todos los pedidos (TipoComprobante = PED) que están en estado 'En preparación' o 'Preparado' y no han sido anulados, con su valor total (SubtotalDesc).",
            "category": "operational",
            "config": {
                "metrics": ["subtotal_desc"],
                "dimensions": ["fecha", "nro_comprobante", "estado", "tipo_comprobante"],
                "tags": ["pedidos", "preparacion", "pendientes", "operational"],
                "notes": [
                    "Fuente: tabla comp_ped",
                    "Filtros: TipoComprobante = 'PED', Anulado = 'No', Estado IN ('En preparación', 'Preparado')",
                    "Valor: SubtotalDesc",
                ],
                "filters": {
                    "fecha_inicio": {"type": "date", "required": True, "label": "Fecha Inicio"},
                    "fecha_fin": {"type": "date", "required": True, "label": "Fecha Fin"},
                    "dia_actual": {"type": "boolean", "required": False, "label": "Día en curso", "default": False},
                    "mes_actual": {"type": "boolean", "required": False, "label": "Mes en curso", "default": False},
                    "año_actual": {"type": "boolean", "required": False, "label": "Año en curso", "default": False},
                    "periodo_tipo": {"type": "select", "required": False, "label": "Tipo de Período", "options": ["dia_actual", "mes_actual", "año_actual", "personalizado"]},
                },
            },
            "metadata": {
                "created_by": "system",
                "seeded_at": now.isoformat(),
                "tags": ["pedidos", "preparacion", "pendientes", "operational"],
                "related_reports": [],
            },
            "refresh_interval": "daily",
            "is_active": True,
            "is_visible": True,
        },
    )

    # Eliminar widgets existentes y crear nuevos
    ReportWidget.objects.filter(report=report_def).delete()
    
    # Widget principal: Tabla de pedidos (sin gráfico)
    ReportWidget.objects.create(
        report=report_def,
        name="Tabla de Pedidos pendientes",
        widget_type="pivot-table",
        order=1,
        layout={"w": 12, "h": 10},
        configuration={
            "rows": ["fecha", "nro_comprobante", "estado", "tipo_comprobante"],
            "columns": [],
            "values": ["subtotal_desc"],
            "aggregation": "sum",
            "pagination": True,
            "page_size": 50,
            "sortable": True,
            "filterable": True,
            "exportable": True,
        },
    )


def delete_pending_orders_report(apps, schema_editor):
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportDefinition.objects.filter(slug="pending_orders", empresa__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0014_add_uninvoiced_remitos_report"),
    ]

    operations = [
        migrations.RunPython(create_pending_orders_report, delete_pending_orders_report),
    ]

