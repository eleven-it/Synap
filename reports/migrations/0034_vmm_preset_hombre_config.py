# Actualiza config preset_hombre en ventas-marcas-mensual
from django.db import migrations


def apply_preset_hombre_config(apps, schema_editor):
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

    from reports.services.ventas_marcas_mensual_seed import (
        seed_ventas_marcas_mensual_report,
    )

    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")
    seed_ventas_marcas_mensual_report(ReportDefinition, ReportWidget)


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0033_add_ventas_marcas_mensual_report"),
    ]

    operations = [
        migrations.RunPython(apply_preset_hombre_config, migrations.RunPython.noop),
    ]
