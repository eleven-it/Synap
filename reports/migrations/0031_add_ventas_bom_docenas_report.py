# Generated migration: Ventas BOM en docenas
from django.db import migrations


def create_ventas_bom_docenas_report(apps, schema_editor):
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
            print("⚠️  Tabla reports_reportdefinition no existe, saltando ventas-bom-docenas")
            return
    except Exception as e:
        print(f"⚠️  Error verificando tabla: {e}")
        return
    finally:
        cursor.close()

    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")
    from reports.services.ventas_bom_docenas_seed import seed_ventas_bom_docenas_report

    seed_ventas_bom_docenas_report(ReportDefinition, ReportWidget)


def delete_ventas_bom_docenas_report(apps, schema_editor):
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
            return
    except Exception:
        return
    finally:
        cursor.close()

    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportDefinition.objects.filter(slug="ventas-bom-docenas", empresa__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0030_add_total_consolidado_operativo"),
    ]
    operations = [
        migrations.RunPython(
            create_ventas_bom_docenas_report,
            delete_ventas_bom_docenas_report,
        ),
    ]
