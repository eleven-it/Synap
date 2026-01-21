from django.db import migrations
from django.utils import timezone


def create_ventas_netas_report(apps, schema_editor):
    """Crea el reporte de Ventas Netas."""
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
            print("⚠️  Tabla reports_reportdefinition no existe, saltando creación de reporte ventas_netas")
            return
    except Exception as e:
        print(f"⚠️  Error verificando tabla: {e}, saltando creación de reporte ventas_netas")
        return
    finally:
        cursor.close()
    
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")

    now = timezone.now()

    report_def, _ = ReportDefinition.objects.update_or_create(
        slug="ventas_netas",
        empresa=None,
        defaults={
            "name": "Ventas Netas",
            "description": "Cálculo de ventas netas (Ventas - Notas de Crédito) con importes sin impuestos. Agrupado por mes y sucursal.",
            "category": "operational",
            "config": {
                "metrics": ["ventas_netas", "ventas_brutas", "notas_credito"],
                "dimensions": ["mes", "sucursal", "punto_venta"],
                "tags": ["sales", "net_sales", "operational"],
                "notes": ["Fuente: cuentacliente", "Cálculo: Ventas (FA,FB,FC,FE,FM) - NC (NCA,NCB,NCC,NCE,NCM) sin impuestos"],
                "filters": {
                    "fecha_inicio": {"type": "date", "required": True, "label": "Fecha Inicio"},
                    "fecha_fin": {"type": "date", "required": True, "label": "Fecha Fin"},
                    "punto_venta": {"type": "multi_select", "required": False, "label": "Punto de Venta"},
                    "sucursales": {"type": "multi_select", "required": False, "label": "Sucursales"},
                    "mes_actual": {"type": "boolean", "required": False, "label": "Mes en curso", "default": False},
                },
            },
            "metadata": {
                "created_by": "system",
                "seeded_at": now.isoformat(),
                "tags": ["sales", "net_sales", "operational"],
            },
            "refresh_interval": "daily",
            "is_active": True,
        },
    )

    # Eliminar widgets existentes y crear nuevos
    ReportWidget.objects.filter(report=report_def).delete()
    
    # Widget principal: Gráfico de barras agrupadas por mes y sucursal
    ReportWidget.objects.create(
        report=report_def,
        name="Ventas Netas por Mes y Sucursal",
        widget_type="d3-bar-grouped",
        order=1,
        layout={"w": 12, "h": 6},
        configuration={
            "x_field": "mes",
            "y_field": "ventas_netas",
            "group_field": "sucursal",
            "unit": "ARS",
            "show_totals": True,
        },
    )
    
    # Widget secundario: Tabla pivot con detalles
    ReportWidget.objects.create(
        report=report_def,
        name="Tabla Detallada",
        widget_type="pivot-table",
        order=2,
        layout={"w": 12, "h": 8},
        configuration={
            "rows": ["mes", "sucursal"],
            "columns": ["punto_venta"],
            "values": ["ventas_netas", "ventas_brutas", "notas_credito"],
            "aggregation": "sum",
        },
    )


def delete_ventas_netas_report(apps, schema_editor):
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
            print("⚠️  Tabla reports_reportdefinition no existe, saltando eliminación de reporte ventas_netas")
            return
    except Exception as e:
        print(f"⚠️  Error verificando tabla: {e}, saltando eliminación de reporte ventas_netas")
        return
    finally:
        cursor.close()
    
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    try:
        ReportDefinition.objects.filter(slug="ventas_netas", empresa__isnull=True).delete()
    except Exception as e:
        print(f"⚠️  Error eliminando reporte ventas_netas: {e}")


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0007_alter_reportdefinition_refresh_interval"),
    ]

    operations = [
        migrations.RunPython(create_ventas_netas_report, delete_ventas_netas_report),
    ]
