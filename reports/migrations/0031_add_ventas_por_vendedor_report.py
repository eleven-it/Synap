# Informe legacy «Ventas por vendedor» (slug ventas-por-vendedor).
from django.db import migrations
from django.utils import timezone


def create_ventas_por_vendedor_report(apps, schema_editor):
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
            print("⚠️  Tabla reports_reportdefinition no existe, saltando ventas-por-vendedor")
            return
    except Exception as e:
        print(f"⚠️  Error verificando tabla: {e}")
        return
    finally:
        cursor.close()

    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")
    now = timezone.now()

    report_def, _ = ReportDefinition.objects.update_or_create(
        slug="ventas-por-vendedor",
        empresa=None,
        defaults={
            "name": "Ventas por vendedor",
            "description": "Facturación por vendedor con jerarquía Con compra / Sin compra, cliente y rubro. Mismos filtros operativos que Objetivos vs BO; sin período de backorder en pantalla. Ver docs/reports/SPEC_INFORME_VENTAS_POR_VENDEDOR.md.",
            "category": "operational",
            "config": {},
            "metadata": {
                "created_by": "system",
                "seeded_at": now.isoformat(),
                "catalog_legacy_section": "listados",
                "catalog_legacy_order": 96,
            },
            "refresh_interval": "daily",
            "is_active": True,
        },
    )
    ReportWidget.objects.filter(report=report_def).delete()


def delete_ventas_por_vendedor_report(apps, schema_editor):
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
    ReportDefinition.objects.filter(slug="ventas-por-vendedor", empresa__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0030_add_total_consolidado_operativo"),
    ]

    operations = [
        migrations.RunPython(create_ventas_por_vendedor_report, delete_ventas_por_vendedor_report),
    ]
