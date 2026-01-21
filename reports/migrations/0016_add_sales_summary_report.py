from django.db import migrations
from django.utils import timezone


def create_sales_summary_report(apps, schema_editor):
    """Crea el reporte consolidado de Resumen de Ventas (Ventas netas + Remitos no facturados + Pedidos pendientes)."""
    # Verificar si la tabla existe antes de intentar acceder
    from django.db import connection
    cursor = connection.cursor()
    
    try:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'reports_reportdefinition'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("⚠️  Tabla reports_reportdefinition no existe, saltando creación de reporte sales_summary")
            return
    except Exception as e:
        print(f"⚠️  Error verificando tabla: {e}, saltando creación de reporte sales_summary")
        return
    finally:
        cursor.close()
    
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")

    now = timezone.now()

    report_def, _ = ReportDefinition.objects.update_or_create(
        slug="sales_summary",
        empresa=None,
        defaults={
            "name": "Resumen de Ventas",
            "description": "Resumen consolidado que muestra los totales de Ventas Netas, Remitos no facturados y Pedidos pendientes para un período determinado.",
            "category": "operational",
            "config": {
                "metrics": ["ventas_netas", "remitos_no_facturados", "pedidos_pendientes", "total_consolidado"],
                "dimensions": [],
                "tags": ["ventas", "resumen", "consolidado", "operational"],
                "notes": [
                    "Fuente: tablas cuentacliente y comp_ped",
                    "Ventas Netas: Facturas - Notas de Crédito (cuentacliente)",
                    "Remitos no facturados: Remitos pendientes (comp_ped, TipoComprobante = REM)",
                    "Pedidos pendientes: Pedidos en preparación (comp_ped, TipoComprobante = PED)",
                ],
                "filters": {
                    "fecha_inicio": {"type": "date", "required": True, "label": "Fecha Inicio"},
                    "fecha_fin": {"type": "date", "required": True, "label": "Fecha Fin"},
                    "dia_actual": {"type": "boolean", "required": False, "label": "Día en curso", "default": False},
                    "mes_actual": {"type": "boolean", "required": False, "label": "Mes en curso", "default": False},
                    "año_actual": {"type": "boolean", "required": False, "label": "Año en curso", "default": False},
                    "periodo_tipo": {"type": "select", "required": False, "label": "Tipo de Período", "options": ["dia_actual", "mes_actual", "año_actual", "personalizado"]},
                },
            },
            "metadata": {
                "created_by": "system",
                "seeded_at": now.isoformat(),
                "tags": ["ventas", "resumen", "consolidado", "operational"],
                "related_reports": ["ventas_netas", "uninvoiced_remitos", "pending_orders"],
            },
            "refresh_interval": "daily",
            "is_active": True,
            # is_visible se agregará automáticamente con el valor por defecto True
            # cuando se ejecute la migración 0011
        },
    )

    # Eliminar widgets existentes y crear nuevos
    ReportWidget.objects.filter(report=report_def).delete()
    
    # Widget principal: Cards de totales (sin tabla ni gráfico)
    ReportWidget.objects.create(
        report=report_def,
        name="Resumen de Total",
        widget_type="d3-cards",
        order=1,
        layout={"w": 12, "h": 8},
        configuration={
            "fields": ["ventas_netas", "remitos_no_facturados", "pedidos_pendientes", "total_consolidado"],
        },
    )


def delete_sales_summary_report(apps, schema_editor):
    # Verificar si la tabla existe antes de intentar acceder
    from django.db import connection
    cursor = connection.cursor()
    
    try:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'reports_reportdefinition'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("⚠️  Tabla reports_reportdefinition no existe, saltando eliminación de reporte sales_summary")
            return
    except Exception as e:
        print(f"⚠️  Error verificando tabla: {e}, saltando eliminación de reporte sales_summary")
        return
    finally:
        cursor.close()
    
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    try:
        ReportDefinition.objects.filter(slug="sales_summary", empresa__isnull=True).delete()
    except Exception as e:
        print(f"⚠️  Error eliminando reporte sales_summary: {e}")


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0015_add_pending_orders_report"),
    ]

    operations = [
        migrations.RunPython(create_sales_summary_report, delete_sales_summary_report),
    ]

