# Generated migration: Total Consolidado Operativo (legacy)
from django.db import migrations
from django.utils import timezone


def create_total_consolidado_operativo_report(apps, schema_editor):
    """Crea el reporte legacy Total Consolidado Operativo: 4 KPIs verticales (Ventas Netas, Remitos no facturados, Pedidos pendientes, Total consolidado)."""
    from django.db import connection
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'reports_reportdefinition'
            );
        """)
        if not cursor.fetchone()[0]:
            print("⚠️  Tabla reports_reportdefinition no existe, saltando creación de total-consolidado-operativo")
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
        slug="total-consolidado-operativo",
        empresa=None,
        defaults={
            "name": "Total Consolidado Operativo",
            "description": "KPIs consolidados: Ventas Netas, Remitos no facturados, Pedidos pendientes de entrega y Total consolidado. Filtros por período, sucursales y punto de venta.",
            "category": "operational",
            "config": {
                "metrics": ["ventas_netas", "remitos_no_facturados", "pedidos_pendientes", "total_consolidado"],
                "dimensions": [],
                "tags": ["ventas", "consolidado", "operational", "kpi"],
                "filters": {
                    "fecha_inicio": {"type": "date", "required": True, "label": "Fecha Inicio"},
                    "fecha_fin": {"type": "date", "required": True, "label": "Fecha Fin"},
                    "sucursales": {"type": "multi_select", "required": False, "label": "Sucursales"},
                    "punto_venta": {"type": "multi_select", "required": False, "label": "Punto de venta"},
                    "dia_actual": {"type": "boolean", "required": False, "label": "Día en curso", "default": False},
                    "mes_actual": {"type": "boolean", "required": False, "label": "Mes en curso", "default": False},
                    "año_actual": {"type": "boolean", "required": False, "label": "Año en curso", "default": False},
                    "periodo_tipo": {"type": "select", "required": False, "label": "Tipo de Período", "options": ["dia_actual", "mes_actual", "año_actual", "personalizado"]},
                },
            },
            "metadata": {
                "created_by": "system",
                "seeded_at": now.isoformat(),
                "related_reports": ["ventas_netas", "remitos-no-facturados", "pedidos-pendientes", "sales_summary"],
            },
            "refresh_interval": "daily",
            "is_active": True,
        },
    )

    ReportWidget.objects.filter(report=report_def).delete()
    ReportWidget.objects.create(
        report=report_def,
        name="KPIs Consolidado",
        widget_type="d3-cards",
        order=1,
        layout={"w": 12, "h": 8},
        configuration={"fields": ["ventas_netas", "remitos_no_facturados", "pedidos_pendientes", "total_consolidado"]},
    )


def delete_total_consolidado_operativo_report(apps, schema_editor):
    from django.db import connection
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'reports_reportdefinition'
            );
        """)
        if not cursor.fetchone()[0]:
            return
    except Exception:
        return
    finally:
        cursor.close()
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportDefinition.objects.filter(slug="total-consolidado-operativo", empresa__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0029_add_table_cluster_assignment"),
    ]
    operations = [
        migrations.RunPython(create_total_consolidado_operativo_report, delete_total_consolidado_operativo_report),
    ]
