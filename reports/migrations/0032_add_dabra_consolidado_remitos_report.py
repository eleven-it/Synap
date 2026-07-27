# Generated migration: Informe DABRA consolidado remitos
from django.db import migrations
from django.utils import timezone


def create_dabra_consolidado_remitos_report(apps, schema_editor):
    """Crea ReportDefinition slug dabra-consolidado-remitos."""
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
                "⚠️  Tabla reports_reportdefinition no existe, saltando dabra-consolidado-remitos"
            )
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
        slug="dabra-consolidado-remitos",
        empresa=None,
        defaults={
            "name": "Informe DABRA consolidado remitos",
            "description": (
                "Export mensual consolidado de líneas de factura DABRA (Codigo=368) "
                "con remitos, preview en dashboard y validación de totales."
            ),
            "category": "operational",
            "config": {
                "metrics": [],
                "dimensions": [],
                "tags": ["dabra", "remitos", "facturas", "operational"],
                "filters": {
                    "mes": {"type": "integer", "required": True, "label": "Mes", "min": 1, "max": 12},
                    "anio": {"type": "integer", "required": True, "label": "Año"},
                },
            },
            "metadata": {
                "created_by": "system",
                "seeded_at": now.isoformat(),
                "permission": "reports.dabra_consolidado_remitos",
            },
            "refresh_interval": "daily",
            "is_active": True,
        },
    )

    ReportWidget.objects.filter(report=report_def).delete()
    ReportWidget.objects.create(
        report=report_def,
        name="DABRA consolidado",
        widget_type="table",
        order=1,
        layout={"w": 12, "h": 10},
        configuration={"tabs": ["REPORTE", "TOTAL FACTURAS"]},
    )


def delete_dabra_consolidado_remitos_report(apps, schema_editor):
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
    ReportDefinition.objects.filter(slug="dabra-consolidado-remitos", empresa__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0031_add_puntoventacanalejecutivo"),
    ]

    operations = [
        migrations.RunPython(
            create_dabra_consolidado_remitos_report,
            delete_dabra_consolidado_remitos_report,
        ),
    ]
