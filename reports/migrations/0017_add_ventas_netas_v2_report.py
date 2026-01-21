from django.db import migrations
from django.utils import timezone


def create_ventas_netas_v2_report(apps, schema_editor):
    """Crea el reporte de Ventas Netas v2 siguiendo la estructura de Flujo de Caja."""
    # Verificar si la tabla existe antes de intentar acceder
    from django.db import connection
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'reports_reportdefinition'
                );
            """)
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                print("⚠️  Tabla reports_reportdefinition no existe, saltando creación de reporte ventas_netas_v2")
                return
    except Exception as e:
        print(f"⚠️  Error verificando tabla: {e}, saltando creación de reporte ventas_netas_v2")
        return
    
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")

    now = timezone.now()

    # Crear el reporte usando SQL directo para incluir is_visible
    import json
    from django.db import connection
    
    config_data = {
        "metrics": ["ventas_netas", "ventas_brutas", "notas_credito"],
        "dimensions": ["mes", "sucursal", "punto_venta"],
        "tags": ["sales", "net_sales", "operational", "v2"],
        "notes": [
            "Fuente: cuentacliente",
            "Cálculo: Ventas (FA,FB,FC,FE,FM) - NC (NCA,NCB,NCC,NCE,NCM) sin impuestos",
            "Versión v2: Estructura similar a Flujo de Caja",
        ],
        "filters": {
            "fecha_inicio": {"type": "date", "required": True, "label": "Fecha Inicio"},
            "fecha_fin": {"type": "date", "required": True, "label": "Fecha Fin"},
            "punto_venta": {"type": "multi_select", "required": False, "label": "Punto de Venta"},
            "sucursales": {"type": "multi_select", "required": False, "label": "Sucursales"},
            "mes_actual": {"type": "boolean", "required": False, "label": "Mes en curso", "default": False},
        },
    }
    
    metadata_data = {
        "created_by": "system",
        "seeded_at": now.isoformat(),
        "tags": ["sales", "net_sales", "operational", "v2"],
        "related_reports": ["ventas_netas"],
    }
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO reports_reportdefinition (
                    slug, name, description, category, version, config, metadata, 
                    refresh_interval, is_active, is_visible, created_at, updated_at, empresa_id
                ) VALUES (
                    %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (slug, empresa_id) WHERE empresa_id IS NULL
                DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    category = EXCLUDED.category,
                    version = EXCLUDED.version,
                    config = EXCLUDED.config,
                    metadata = EXCLUDED.metadata,
                    refresh_interval = EXCLUDED.refresh_interval,
                    is_active = EXCLUDED.is_active,
                    is_visible = EXCLUDED.is_visible,
                    updated_at = EXCLUDED.updated_at
                RETURNING id;
            """, [
                "ventas_netas_v2",
                "Ventas Netas v2",
                "Cálculo de ventas netas (Ventas - Notas de Crédito) con importes sin impuestos. Agrupado por mes y sucursal. Versión v2 siguiendo la estructura de Flujo de Caja.",
                "operational",
                "1.0.0",
                json.dumps(config_data),
                json.dumps(metadata_data),
                "daily",
                True,
                True,
                now,
                now,
                None,
            ])
            result = cursor.fetchone()
            if result:
                report_id = result[0]
            else:
                # Si no retornó ID, obtenerlo
                cursor.execute("""
                    SELECT id FROM reports_reportdefinition 
                    WHERE slug = %s AND empresa_id IS NULL
                """, ["ventas_netas_v2"])
                report_id = cursor.fetchone()[0]
        
        # Obtener el reporte usando el modelo para crear los widgets
        report_def = ReportDefinition.objects.get(id=report_id)
    except Exception as e:
        print(f"⚠️  Error creando reporte ventas_netas_v2: {e}")
        import traceback
        traceback.print_exc()
        return

    # Eliminar widgets existentes y crear nuevos
    ReportWidget.objects.filter(report=report_def).delete()
    
    # Widget principal: Gráfico de barras apiladas (similar a cash_flow_waterfall)
    # Usando formato declarativo: kind="bar" con x_dimension, y_metrics, series_dimension
    ReportWidget.objects.create(
        report=report_def,
        name="Ventas Netas por Mes",
        widget_type="bar",  # Formato declarativo
        order=1,
        layout={"w": 12, "h": 6},
        configuration={
            "x_dimension": "mes",
            "y_metrics": ["ventas_netas"],
            "series_dimension": None,  # Sin agrupación por sucursal en el gráfico principal (similar a cash_flow)
            "stacked": False,
        },
    )
    
    # Widget secundario: Gráfico de barras apiladas por sucursal (opcional)
    ReportWidget.objects.create(
        report=report_def,
        name="Ventas Netas por Mes y Sucursal",
        widget_type="bar",  # Formato declarativo
        order=2,
        layout={"w": 12, "h": 6},
        configuration={
            "x_dimension": "mes",
            "y_metrics": ["ventas_netas"],
            "series_dimension": "nombre_sucursal",  # Agrupar por sucursal
            "stacked": True,
        },
    )


def delete_ventas_netas_v2_report(apps, schema_editor):
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
            print("⚠️  Tabla reports_reportdefinition no existe, saltando eliminación de reporte ventas_netas_v2")
            return
    except Exception as e:
        print(f"⚠️  Error verificando tabla: {e}, saltando eliminación de reporte ventas_netas_v2")
        return
    finally:
        cursor.close()
    
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    try:
        ReportDefinition.objects.filter(slug="ventas_netas_v2", empresa__isnull=True).delete()
    except Exception as e:
        print(f"⚠️  Error eliminando reporte ventas_netas_v2: {e}")


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0016_add_sales_summary_report"),
    ]

    operations = [
        migrations.RunPython(create_ventas_netas_v2_report, delete_ventas_netas_v2_report),
    ]
