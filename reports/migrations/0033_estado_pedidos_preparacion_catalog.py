# Catálogo: estado de pedidos / pantalla preparación (vista ecom)
from django.db import migrations
from django.utils import timezone


def forward(apps, schema_editor):
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")
    now = timezone.now()

    slug = "mayoristapp-estado-pedidos-preparacion"
    report_def, _ = ReportDefinition.objects.update_or_create(
        slug=slug,
        empresa=None,
        defaults={
            "name": "Estado de pedidos — preparación (legacy mayoristapp)",
            "description": (
                "Tablero Kanban: Preparado, En preparación, En remito. "
                "Vista operativa de logística; abre el módulo ecom en Synap."
            ),
            "category": "operational",
            "config": {
                "metrics": ["pedidos"],
                "dimensions": ["estado_preparacion", "sucursal"],
                "tags": ["mayoristapp", "legacy", "listados", "logistica", "ecom"],
                "notes": [
                    "Paridad: mayoristapp/logistica_pantalla_preparacion.php + ajax/json_pantalla_pedidos.php"
                ],
            },
            "metadata": {
                "created_by": "system",
                "seeded_at": now.isoformat(),
                "catalog_legacy_section": "listados",
                "catalog_legacy_order": 85,
                "ecom_catalog_entry": True,
            },
            "refresh_interval": "daily",
            "is_active": True,
        },
    )

    ReportWidget.objects.filter(report=report_def).delete()
    ReportWidget.objects.create(
        report=report_def,
        name="Kanban (vista en ecom)",
        widget_type="pivot-table",
        order=1,
        layout={"w": 12, "h": 8},
        configuration={
            "rows": ["estado_preparacion", "sucursal"],
            "columns": [],
            "values": ["pedidos"],
            "aggregation": "sum",
            "pagination": False,
            "sortable": True,
            "filterable": False,
            "exportable": False,
        },
    )


def backward(apps, schema_editor):
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportDefinition.objects.filter(
        slug="mayoristapp-estado-pedidos-preparacion", empresa__isnull=True
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0032_presupuestos_vendedor_catalog"),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
