# Generated migration: Informe Ventas marcas mensual
from django.db import migrations


def create_ventas_marcas_mensual_report(apps, schema_editor):
    """Crea ReportDefinition slug ventas-marcas-mensual."""
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
                "⚠️  Tabla reports_reportdefinition no existe, saltando ventas-marcas-mensual"
            )
            return
    except Exception as e:
        print(f"⚠️  Error verificando tabla: {e}")
        return
    finally:
        cursor.close()

    from reports.services.ventas_marcas_mensual_seed import (
        seed_ventas_marcas_mensual_report,
    )

    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")
    seed_ventas_marcas_mensual_report(ReportDefinition, ReportWidget)


def delete_ventas_marcas_mensual_report(apps, schema_editor):
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
    ReportDefinition.objects.filter(
        slug="ventas-marcas-mensual", empresa__isnull=True
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0032_add_dabra_consolidado_remitos_report"),
    ]

    operations = [
        migrations.RunPython(
            create_ventas_marcas_mensual_report,
            delete_ventas_marcas_mensual_report,
        ),
    ]
