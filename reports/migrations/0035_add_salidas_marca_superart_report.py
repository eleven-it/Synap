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
    from reports.services.salidas_marca_superart_seed import seed_salidas_marca_superart_report

    seed_salidas_marca_superart_report(ReportDefinition, ReportWidget)


def backward(apps, schema_editor):
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")
    ReportWidget.objects.filter(report__slug="salidas-marca-superart").delete()
    ReportDefinition.objects.filter(slug="salidas-marca-superart", empresa=None).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0034_add_compras_marca_superart_report"),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
