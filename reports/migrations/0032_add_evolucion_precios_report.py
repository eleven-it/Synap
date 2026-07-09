from django.db import migrations
from django.utils import timezone


def create_evolucion_precios_report(apps, schema_editor):
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
            print("⚠️  Tabla reports_reportdefinition no existe, saltando evolucion-precios")
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
        slug="evolucion-precios",
        empresa=None,
        defaults={
            "name": "Evolución de precios",
            "description": (
                "Ranking de artículos por variación porcentual de precio neto "
                "entre el primer y último snapshot en precios_historial."
            ),
            "category": "operational",
            "config": {
                "metrics": ["variacion_pct", "neto_inicial", "neto_final"],
                "dimensions": ["id_articulo", "nombre_rubro", "nombre_marca"],
                "tags": ["ventas", "precios", "historial"],
                "filters": {
                    "fecha_desde": {"type": "date", "required": False, "label": "Fecha desde"},
                    "fecha_hasta": {"type": "date", "required": False, "label": "Fecha hasta"},
                    "lista": {"type": "number", "required": False, "label": "Lista de precios", "default": 1},
                    "solo_synap": {"type": "boolean", "required": False, "label": "Solo cambios Synap"},
                    "marcas_incluidos": {"type": "multiselect", "required": False, "label": "Marcas"},
                    "rubros_incluidos": {"type": "multiselect", "required": False, "label": "Rubros"},
                    "limit": {"type": "number", "required": False, "label": "Límite ranking", "default": 50},
                },
            },
            "metadata": {
                "created_by": "system",
                "seeded_at": now.isoformat(),
                "tags": ["ventas", "precios", "historial"],
                "related_ui": "/ventas/evolucion-precios/",
            },
            "refresh_interval": "daily",
            "is_active": True,
        },
    )

    ReportWidget.objects.filter(report=report_def).delete()
    ReportWidget.objects.create(
        report=report_def,
        name="Ranking variación precios",
        widget_type="table",
        order=1,
        layout={"w": 12, "h": 10},
        configuration={
            "fields": [
                "id_manual",
                "nombre_articulo",
                "nombre_rubro",
                "nombre_marca",
                "neto_inicial",
                "neto_final",
                "variacion_pct",
                "cantidad_registros",
            ],
        },
    )


def delete_evolucion_precios_report(apps, schema_editor):
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
    except Exception:
        return
    finally:
        cursor.close()

    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    try:
        ReportDefinition.objects.filter(slug="evolucion-precios", empresa__isnull=True).delete()
    except Exception as e:
        print(f"⚠️  Error eliminando evolucion-precios: {e}")


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0031_add_puntoventacanalejecutivo"),
    ]

    operations = [
        migrations.RunPython(create_evolucion_precios_report, delete_evolucion_precios_report),
    ]
