# Generated migration: Inventario por depósito (catálogo Reportes)
from django.db import migrations


def create_inventario_deposito_report(apps, schema_editor):
    from django.db import connection

    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'reports_reportdefinition'
            );
            """
        )
        if not cursor.fetchone()[0]:
            print(
                "⚠️  Tabla reports_reportdefinition no existe, "
                "saltando inventario-deposito-articulo"
            )
            return
    except Exception as e:
        print(f"⚠️  Error verificando tabla: {e}")
        return
    finally:
        cursor.close()

    from reports.services.inventario_deposito_seed import seed_inventario_deposito_report

    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")
    seed_inventario_deposito_report(ReportDefinition, ReportWidget)


def delete_inventario_deposito_report(apps, schema_editor):
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")
    qs = ReportDefinition.objects.filter(
        slug="inventario-deposito-articulo",
        empresa__isnull=True,
    )
    for report in qs:
        ReportWidget.objects.filter(report=report).delete()
    qs.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0037_add_ventas_bom_docenas_report"),
    ]
    operations = [
        migrations.RunPython(
            create_inventario_deposito_report,
            delete_inventario_deposito_report,
        ),
    ]
