from django.db import migrations


def forward(apps, schema_editor):
    from django.db import connection

    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'reports_reportdefinition'
            );
            """
        )
        if not cursor.fetchone()[0]:
            return
    finally:
        cursor.close()

    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")
    from reports.services.pedidos_pendientes_produccion_seed import (
        seed_pedidos_pendientes_produccion_report,
    )

    seed_pedidos_pendientes_produccion_report(ReportDefinition, ReportWidget)


def backward(apps, schema_editor):
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")
    ReportWidget.objects.filter(report__slug="pedidos-pendientes-produccion").delete()
    ReportDefinition.objects.filter(slug="pedidos-pendientes-produccion", empresa=None).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0031_add_puntoventacanalejecutivo"),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
