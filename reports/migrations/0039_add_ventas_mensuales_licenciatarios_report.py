# Generated migration: Informe Ventas Mensuales Licenciatarios
from django.db import migrations


def create_ventas_mensuales_licenciatarios_report(apps, schema_editor):
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
                "saltando ventas-mensuales-licenciatarios"
            )
            return
    except Exception as e:
        print(f"⚠️  Error verificando tabla: {e}")
        return
    finally:
        cursor.close()

    from reports.services.ventas_mensuales_licenciatarios_seed import (
        seed_ventas_mensuales_licenciatarios_report,
    )

    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")
    seed_ventas_mensuales_licenciatarios_report(ReportDefinition, ReportWidget)


def delete_ventas_mensuales_licenciatarios_report(apps, schema_editor):
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
        slug="ventas-mensuales-licenciatarios",
        empresa__isnull=True,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0038_add_inventario_deposito_articulo_report"),
    ]

    operations = [
        migrations.RunPython(
            create_ventas_mensuales_licenciatarios_report,
            delete_ventas_mensuales_licenciatarios_report,
        ),
    ]
