from django.db import migrations
from django.utils import timezone


def create_cash_flow_detailed_movements_report(apps, schema_editor):
    """Crea el reporte de Movimientos Detallados de Flujo de Caja."""
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
            print("⚠️  Tabla reports_reportdefinition no existe, saltando creación de reporte cash_flow_detailed_movements")
            return
    except Exception as e:
        print(f"⚠️  Error verificando tabla: {e}, saltando creación de reporte cash_flow_detailed_movements")
        return
    finally:
        cursor.close()
    
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")

    now = timezone.now()

    report_def, _ = ReportDefinition.objects.update_or_create(
        slug="cash_flow_detailed_movements",
        empresa=None,
        defaults={
            "name": "Movimientos Detallados de Flujo de Caja",
            "description": "Vista detallada de cada movimiento individual de caja con información completa: fecha, tipo, categoría, cliente/proveedor, medio de pago, importe, cuenta y flujo. Permite análisis detallado, auditoría y trazabilidad de movimientos.",
            "category": "managerial",
            "config": {
                "metrics": ["importe_neto", "ingreso", "egreso"],
                "dimensions": ["fecha", "flujo_tipo", "flujo_subcategoria", "contraparte", "cuenta"],
                "tags": ["cashflow", "detailed", "movements", "audit", "managerial"],
                "notes": [
                    "Fuente: tabla caja",
                    "Incluye JOINs con: cliente, proveedor, caja_abm, gastos, gastos_grupo, sucursales",
                    "Clasificación automática en flujos (operativo, inversión, financiamiento) y subcategorías",
                ],
                "filters": {
                    "fecha_inicio": {"type": "date", "required": True, "label": "Fecha Inicio"},
                    "fecha_fin": {"type": "date", "required": True, "label": "Fecha Fin"},
                    "id_caja": {"type": "multi_select", "required": False, "label": "Caja"},
                    "dia_actual": {"type": "boolean", "required": False, "label": "Día en curso", "default": False},
                    "mes_actual": {"type": "boolean", "required": False, "label": "Mes en curso", "default": False},
                    "año_actual": {"type": "boolean", "required": False, "label": "Año en curso", "default": False},
                    "periodo_tipo": {"type": "select", "required": False, "label": "Tipo de Período", "options": ["dia_actual", "mes_actual", "año_actual", "personalizado"]},
                },
            },
            "metadata": {
                "created_by": "system",
                "seeded_at": now.isoformat(),
                "tags": ["cashflow", "detailed", "movements", "audit", "managerial"],
                "related_reports": ["cash_flow_waterfall"],
            },
            "refresh_interval": "realtime",
            "is_active": True,
        },
    )

    # Eliminar widgets existentes y crear nuevos
    ReportWidget.objects.filter(report=report_def).delete()
    
    # Widget principal: Tabla detallada de movimientos
    ReportWidget.objects.create(
        report=report_def,
        name="Tabla de Movimientos Detallados",
        widget_type="pivot-table",
        order=1,
        layout={"w": 12, "h": 10},
        configuration={
            "rows": ["fecha", "flujo_tipo", "flujo_subcategoria"],
            "columns": ["contraparte", "cuenta"],
            "values": ["importe_neto", "ingreso", "egreso"],
            "aggregation": "sum",
            "pagination": True,
            "page_size": 100,
            "sortable": True,
            "filterable": True,
            "exportable": True,
        },
    )


def delete_cash_flow_detailed_movements_report(apps, schema_editor):
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
            print("⚠️  Tabla reports_reportdefinition no existe, saltando eliminación de reporte cash_flow_detailed_movements")
            return
    except Exception as e:
        print(f"⚠️  Error verificando tabla: {e}, saltando eliminación de reporte cash_flow_detailed_movements")
        return
    finally:
        cursor.close()
    
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    try:
        ReportDefinition.objects.filter(slug="cash_flow_detailed_movements", empresa__isnull=True).delete()
    except Exception as e:
        print(f"⚠️  Error eliminando reporte cash_flow_detailed_movements: {e}")


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0008_add_ventas_netas_report"),
    ]

    operations = [
        migrations.RunPython(create_cash_flow_detailed_movements_report, delete_cash_flow_detailed_movements_report),
    ]



