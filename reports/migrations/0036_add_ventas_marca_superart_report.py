# Generated migration: Informe Ventas por marca y SuperArt
from django.db import migrations


def create_ventas_marca_superart_report(apps, schema_editor):
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
                "saltando ventas-marca-superart"
            )
            return
    except Exception as e:
        print(f"⚠️  Error verificando tabla: {e}")
        return
    finally:
        cursor.close()

    from reports.services.ventas_marca_superart_seed import seed_ventas_marca_superart_report

    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")
    seed_ventas_marca_superart_report(ReportDefinition, ReportWidget)


def delete_ventas_marca_superart_report(apps, schema_editor):
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
        slug="ventas-marca-superart",
        empresa__isnull=True,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        # Independiente de VML (0035); tip remoto Desarrollo está en 0034.
        ("reports", "0034_vmm_preset_hombre_config"),
    ]

    operations = [
        migrations.RunPython(
            create_ventas_marca_superart_report,
            delete_ventas_marca_superart_report,
        ),
    ]
