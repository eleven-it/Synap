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
    from reports.services.bestsox_marca_reports_seed import seed_all_bestsox_marca_reports

    seed_all_bestsox_marca_reports(ReportDefinition, ReportWidget)


def backward(apps, schema_editor):
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")
    slugs = (
        "produccion-marca-superart",
        "compras-marca-superart",
        "consignacion-stock",
    )
    ReportWidget.objects.filter(report__slug__in=slugs).delete()
    ReportDefinition.objects.filter(slug__in=slugs, empresa=None).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0033_add_fabricados_superart_report"),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
