from django.db import migrations
from django.utils import timezone


def create_pending_orders_report(apps, schema_editor):
    """Crea el reporte de Pedidos pendientes."""
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
            print("⚠️  Tabla reports_reportdefinition no existe, saltando creación de reporte pedidos-pendientes")
            return
    except Exception as e:
        print(f"⚠️  Error verificando tabla: {e}, saltando creación de reporte pedidos-pendientes")
        return
    finally:
        cursor.close()
    
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")

    now = timezone.now()

    report_def, _ = ReportDefinition.objects.update_or_create(
        slug="pedidos-pendientes",
        empresa=None,
        defaults={
            "name": "Pedidos pendientes",
            "description": "Listado de pedidos pendientes de preparación. Muestra todos los pedidos (TipoComprobante = PED) que están en estado 'En preparación' o 'Preparado' y no han sido anulados, con su valor total (SubtotalDesc).",
            "category": "operational",
            "config": {
                "metrics": ["subtotal_desc"],
                "dimensions": ["fecha", "nro_comprobante"],
                "tags": ["pedidos", "preparacion", "pendientes", "operational"],
                "notes": [
                    "Fuente: tabla comp_ped",
                    "Filtros: TipoComprobante = 'PED', Anulado = 'No', Estado IN ('En preparación', 'Preparado')",
                    "Valor: SubtotalDesc",
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
                "tags": ["pedidos", "preparacion", "pendientes", "operational"],
                "related_reports": [],
            },
            "refresh_interval": "daily",
            "is_active": True,
            # is_visible se agregará automáticamente con el valor por defecto True
            # cuando se ejecute la migración 0011
        },
    )

    # Eliminar widgets existentes y crear nuevos
    ReportWidget.objects.filter(report=report_def).delete()
    
    # Widget principal: Tabla de pedidos (sin gráfico)
    ReportWidget.objects.create(
        report=report_def,
        name="Tabla de Pedidos pendientes",
        widget_type="pivot-table",
        order=1,
        layout={"w": 12, "h": 10},
        configuration={
            "rows": ["fecha", "nro_comprobante"],
            "columns": [],
            "values": ["subtotal_desc"],
            "aggregation": "sum",
            "pagination": True,
            "page_size": 50,
            "sortable": True,
            "filterable": True,
            "exportable": True,
        },
    )


def delete_pending_orders_report(apps, schema_editor):
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
            print("⚠️  Tabla reports_reportdefinition no existe, saltando eliminación de reporte pedidos-pendientes")
            return
    except Exception as e:
        print(f"⚠️  Error verificando tabla: {e}, saltando eliminación de reporte pedidos-pendientes")
        return
    finally:
        cursor.close()
    
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    try:
        ReportDefinition.objects.filter(slug="pedidos-pendientes", empresa__isnull=True).delete()
    except Exception as e:
        print(f"⚠️  Error eliminando reporte pedidos-pendientes: {e}")


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0014_add_uninvoiced_remitos_report"),
    ]

    operations = [
        migrations.RunPython(create_pending_orders_report, delete_pending_orders_report),
    ]

