# Informe Objetivos de ventas vs BO (jerárquico vendedor → cliente).
from django.db import migrations
from django.utils import timezone


def create_ventas_objetivos_vs_bo_report(apps, schema_editor):
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
            print("⚠️  Tabla reports_reportdefinition no existe, saltando ventas-objetivos-vs-bo")
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
        slug="ventas-objetivos-vs-bo",
        empresa=None,
        defaults={
            "name": "Objetivos de ventas por vendedor",
            "description": (
                "Seguimiento de objetivos por cliente agrupados por vendedor, con facturación, remitos, "
                "total, falta, unidades vendidas y columnas de backorder. Misma temporalidad dual que el informe BO."
            ),
            "category": "operational",
            "config": {
                "metrics": [
                    "objetivo",
                    "facturacion",
                    "remitos",
                    "total",
                    "falta",
                    "cantidades_vendidas",
                    "backorder_total",
                    "bo_con_stock",
                    "bo_con_ingreso",
                    "bo_sin_stock",
                ],
                "dimensions": ["vendedor", "cliente"],
                "tags": ["ventas", "objetivos", "backorder", "operational"],
                "filters": {
                    "fecha_inicio": {"type": "date", "required": True, "label": "Fecha inicio (BO)"},
                    "fecha_fin": {"type": "date", "required": True, "label": "Fecha fin (BO)"},
                    "fecha_inicio_facturacion": {"type": "date", "required": False, "label": "Fecha inicio facturación"},
                    "fecha_fin_facturacion": {"type": "date", "required": False, "label": "Fecha fin facturación"},
                    "sucursales": {"type": "multi_select", "required": False, "label": "Sucursales"},
                    "depositos_incluidos": {"type": "multi_select", "required": False, "label": "Depósitos"},
                    "clientes_excluidos": {"type": "multi_select", "required": False, "label": "Clientes a excluir"},
                    "lista_precio": {"type": "integer", "required": False, "label": "Lista precio BO"},
                },
            },
            "metadata": {
                "created_by": "system",
                "seeded_at": now.isoformat(),
                "related_reports": ["bo-stock-facturacion"],
            },
            "refresh_interval": "realtime",
            "is_active": True,
        },
    )

    ReportWidget.objects.filter(report=report_def).delete()
    ReportWidget.objects.create(
        report=report_def,
        name="Tabla objetivos",
        widget_type="table",
        order=1,
        layout={"w": 12, "h": 10},
        configuration={"source": "objetivos_jerarquia"},
    )


def delete_ventas_objetivos_vs_bo_report(apps, schema_editor):
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
    finally:
        cursor.close()

    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportDefinition.objects.filter(slug="ventas-objetivos-vs-bo", empresa__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0030_add_total_consolidado_operativo"),
    ]
    operations = [
        migrations.RunPython(create_ventas_objetivos_vs_bo_report, delete_ventas_objetivos_vs_bo_report),
    ]
