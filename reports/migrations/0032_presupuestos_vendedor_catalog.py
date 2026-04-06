# Catálogo: presupuestos por vendedor (vista ecom mayoristapp)
from django.db import migrations
from django.utils import timezone


def forward(apps, schema_editor):
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")
    now = timezone.now()

    slug = "mayoristapp-presupuestos-vendedor"
    report_def, _ = ReportDefinition.objects.update_or_create(
        slug=slug,
        empresa=None,
        defaults={
            "name": "Presupuestos por vendedor (legacy mayoristapp)",
            "description": (
                "Listado de presupuestos por vendedor alineado a mayoristapp. "
                "Abre la vista en Synap (módulo ecom)."
            ),
            "category": "operational",
            "config": {
                "metrics": ["presupuestos"],
                "dimensions": ["vendedor", "estado"],
                "tags": ["mayoristapp", "legacy", "listados", "ecom"],
                "notes": [
                    "Entrada de catálogo: la URL del dashboard redirige a /ecom/mayoristapp/presupuestos-vendedor/."
                ],
            },
            "metadata": {
                "created_by": "system",
                "seeded_at": now.isoformat(),
                "catalog_legacy_section": "listados",
                "catalog_legacy_order": 80,
                "ecom_catalog_entry": True,
            },
            "refresh_interval": "daily",
            "is_active": True,
        },
    )

    ReportWidget.objects.filter(report=report_def).delete()
    ReportWidget.objects.create(
        report=report_def,
        name="Tabla (vista en ecom)",
        widget_type="pivot-table",
        order=1,
        layout={"w": 12, "h": 8},
        configuration={
            "rows": ["vendedor", "estado"],
            "columns": [],
            "values": ["presupuestos"],
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
        slug="mayoristapp-presupuestos-vendedor", empresa__isnull=True
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0031_catalog_legacy_metadata_and_placeholders"),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
