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
    from reports.services.compras_marca_superart_seed import seed_compras_marca_superart_report

    seed_compras_marca_superart_report(ReportDefinition, ReportWidget)


def backward(apps, schema_editor):
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")
    ReportWidget.objects.filter(report__slug="compras-marca-superart").delete()
    ReportDefinition.objects.filter(slug="compras-marca-superart", empresa=None).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0033_add_fabricados_superart_report"),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
