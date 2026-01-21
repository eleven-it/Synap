from django.db import migrations
from django.utils import timezone


def create_uninvoiced_remitos_report(apps, schema_editor):
    """Crea el reporte de Remitos no facturados."""
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
            print("⚠️  Tabla reports_reportdefinition no existe, saltando creación de reporte uninvoiced_remitos")
            return
    except Exception as e:
        print(f"⚠️  Error verificando tabla: {e}, saltando creación de reporte uninvoiced_remitos")
        return
    finally:
        cursor.close()
    
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")

    now = timezone.now()

    report_def, _ = ReportDefinition.objects.update_or_create(
        slug="uninvoiced_remitos",
        empresa=None,
        defaults={
            "name": "Remitos no facturados",
            "description": "Listado de remitos pendientes de facturación. Muestra todos los remitos (TipoComprobante = REM) que están en estado Pendiente y no han sido anulados, con su valor total (SubtotalDesc).",
            "category": "operational",
            "config": {
                "metrics": ["subtotal_desc"],
                "dimensions": ["fecha", "nro_comprobante", "sucursal", "punto_venta"],
                "tags": ["remitos", "facturacion", "pendientes", "operational"],
                "notes": [
                    "Fuente: tabla comp_ped",
                    "Filtros: TipoComprobante = 'REM', Anulado = 'No', Estado = 'Pendiente'",
                    "Valor: SubtotalDesc",
                ],
                "filters": {
                    "fecha_inicio": {"type": "date", "required": True, "label": "Fecha Inicio"},
                    "fecha_fin": {"type": "date", "required": True, "label": "Fecha Fin"},
                    "sucursales": {"type": "multi_select", "required": False, "label": "Sucursales"},
                    "punto_venta": {"type": "multi_select", "required": False, "label": "Punto de Venta"},
                    "dia_actual": {"type": "boolean", "required": False, "label": "Día en curso", "default": False},
                    "mes_actual": {"type": "boolean", "required": False, "label": "Mes en curso", "default": False},
                    "año_actual": {"type": "boolean", "required": False, "label": "Año en curso", "default": False},
                    "periodo_tipo": {"type": "select", "required": False, "label": "Tipo de Período", "options": ["dia_actual", "mes_actual", "año_actual", "personalizado"]},
                },
            },
            "metadata": {
                "created_by": "system",
                "seeded_at": now.isoformat(),
                "tags": ["remitos", "facturacion", "pendientes", "operational"],
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
    
    # Widget principal: Tabla de remitos (sin gráfico)
    ReportWidget.objects.create(
        report=report_def,
        name="Tabla de Remitos no facturados",
        widget_type="pivot-table",
        order=1,
        layout={"w": 12, "h": 10},
        configuration={
            "rows": ["fecha", "nro_comprobante", "sucursal", "punto_venta"],
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


def delete_uninvoiced_remitos_report(apps, schema_editor):
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
            print("⚠️  Tabla reports_reportdefinition no existe, saltando eliminación de reporte uninvoiced_remitos")
            return
    except Exception as e:
        print(f"⚠️  Error verificando tabla: {e}, saltando eliminación de reporte uninvoiced_remitos")
        return
    finally:
        cursor.close()
    
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    try:
        ReportDefinition.objects.filter(slug="uninvoiced_remitos", empresa__isnull=True).delete()
    except Exception as e:
        print(f"⚠️  Error eliminando reporte uninvoiced_remitos: {e}")


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0013_add_cash_flow_by_account"),
    ]

    operations = [
        migrations.RunPython(create_uninvoiced_remitos_report, delete_uninvoiced_remitos_report),
    ]


