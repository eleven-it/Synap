from django.db import migrations
from django.utils import timezone


def create_remitos_no_facturados_declarative_report(apps, schema_editor):
    """Crea el reporte declarativo de Remitos no facturados."""
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
            print("⚠️  Tabla reports_reportdefinition no existe, saltando creación de reporte remitos_no_facturados")
            return
    except Exception as e:
        print(f"⚠️  Error verificando tabla: {e}, saltando creación de reporte remitos_no_facturados")
        return
    finally:
        cursor.close()
    
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")

    now = timezone.now()

    # Configuración declarativa del informe
    config = {
        "version": "declarative-v1",
        "datasource": "comp_ped",
        "metrics": {
            "subtotal_desc": {
                "expression": "COALESCE(c.SubtotalDesc, 0)",
                "label": "Subtotal",
                "operator": "SUM",
                "format_type": "currency",
                "decimals": 2
            }
        },
        "dimensions": {
            "fecha": {
                "expression": "DATE_FORMAT(c.Fecha, '%d/%m/%Y')",
                "label": "Fecha",
                "data_type": "date"
            },
            "nro_comprobante": {
                "expression": "c.NroComprobante",
                "label": "Nro. Comprobante",
                "data_type": "string"
            },
            "id_sucursal": {
                "expression": "c.CodSucursal",
                "label": "ID Sucursal",
                "data_type": "number",
                "format_type": "number",
                "decimals": 0
            },
            "sucursal": {
                "expression": "COALESCE(s.nombre_sucursal, 'Sin Sucursal')",
                "label": "Sucursal",
                "data_type": "string"
            },
            "id_punto_venta": {
                "expression": "c.id_pv",
                "label": "ID Punto de Venta",
                "data_type": "number",
                "format_type": "number",
                "decimals": 0
            },
            "punto_venta": {
                "expression": "COALESCE(CAST(pv.nro_punto_venta AS CHAR), CAST(c.id_pv AS CHAR), 'Sin PV')",
                "label": "Punto de Venta",
                "data_type": "string"
            }
        },
        "filters": [
            {
                "name": "Fecha Inicio",
                "field": "c.Fecha",
                "operator": ">=",
                "param": "fecha_inicio",
                "is_variable": True,
                "constant_value": None
            },
            {
                "name": "Fecha Fin",
                "field": "c.Fecha",
                "operator": "<=",
                "param": "fecha_fin",
                "is_variable": True,
                "constant_value": None
            },
            {
                "name": "Tipo Comprobante REM",
                "field": "c.TipoComprobante",
                "operator": "=",
                "param": None,
                "is_variable": False,
                "constant_value": "REM"
            },
            {
                "name": "No Anulado",
                "field": "c.Anulado",
                "operator": "=",
                "param": None,
                "is_variable": False,
                "constant_value": "No"
            },
            {
                "name": "Estado Pendiente",
                "field": "c.Estado",
                "operator": "=",
                "param": None,
                "is_variable": False,
                "constant_value": "Pendiente"
            },
            {
                "name": "Sucursales",
                "field": "c.CodSucursal",
                "operator": "IN",
                "param": "sucursales",
                "is_variable": True,
                "constant_value": None
            },
            {
                "name": "Punto de Venta",
                "field": "c.id_pv",
                "operator": "IN",
                "param": "punto_venta",
                "is_variable": True,
                "constant_value": None
            }
        ],
        "joins": [
            {
                "type": "LEFT",
                "table": "sucursales",
                "alias": "s",
                "on": [
                    {
                        "left": "s.id_sucursal",
                        "op": "=",
                        "right": "c.CodSucursal"
                    }
                ]
            },
            {
                "type": "LEFT",
                "table": "punto_venta",
                "alias": "pv",
                "on": [
                    {
                        "left": "pv.id_punto_venta",
                        "op": "=",
                        "right": "c.id_pv"
                    }
                ]
            }
        ],
        "group_by": [],
        "order_by": [
            {
                "field": "fecha",
                "direction": "DESC"
            },
            {
                "field": "nro_comprobante",
                "direction": "ASC"
            }
        ],
        "options": {
            "default_filters": {},
            "fixed_filters": [],
            "custom_metrics_format": {},
            "custom_dimensions_format": {
                "id_sucursal": {
                    "format_type": "number",
                    "decimals": 0
                },
                "id_punto_venta": {
                    "format_type": "number",
                    "decimals": 0
                }
            }
        }
    }

    # Crear o actualizar el reporte con is_visible explícitamente
    report_def, _ = ReportDefinition.objects.update_or_create(
        slug="remitos-no-facturados",
        empresa=None,
        defaults={
            "name": "Remitos no facturados",
            "description": "Listado de remitos pendientes de facturación. Muestra todos los remitos (TipoComprobante = REM) que están en estado Pendiente y no han sido anulados, con su valor total (SubtotalDesc).",
            "category": "operational",
            "version": "declarative-v1",
            "config": config,
            "metadata": {
                "created_by": "system",
                "seeded_at": now.isoformat(),
                "tags": ["remitos", "facturacion", "pendientes", "operational", "declarative"],
                "related_reports": ["uninvoiced_remitos"],
            },
            "refresh_interval": "daily",
            "is_active": True,
        },
    )
    
    # Actualizar is_visible usando SQL directo si la columna existe
    from django.db import connection
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'reports_reportdefinition'
                AND column_name = 'is_visible'
            );
        """)
        is_visible_column_exists = cursor.fetchone()[0]
        
        if is_visible_column_exists:
            cursor.execute("""
                UPDATE reports_reportdefinition 
                SET is_visible = true 
                WHERE id = %s
            """, [report_def.id])
            print("✅ Campo is_visible actualizado a true")
    except Exception as e:
        print(f"⚠️  Error actualizando is_visible: {e}")
    finally:
        cursor.close()

    # Eliminar widgets existentes y crear nuevos
    ReportWidget.objects.filter(report=report_def).delete()
    
    # Widget principal: Tabla de remitos
    ReportWidget.objects.create(
        report=report_def,
        name="Tabla de Remitos no facturados",
        widget_type="table",
        order=1,
        layout={"w": 12, "h": 10},
        configuration={
            "config": {
                "metrics": ["subtotal_desc"],
                "dimensions": ["fecha", "nro_comprobante", "sucursal", "punto_venta"],
                "filters": {},
                "group_by": [],
                "order_by": [
                    {"field": "fecha", "direction": "DESC"},
                    {"field": "nro_comprobante", "direction": "ASC"}
                ]
            },
            "title_options": {
                "show_count": True,
                "count_position": "after",
                "count_format": "number",
                "count_separator": " ",
                "column_metrics": [
                    {
                        "column": "subtotal_desc",
                        "aggregation": "sum",
                        "label": "Total",
                        "format": "currency",
                        "position": "after",
                        "separator": " | "
                    }
                ]
            },
            "grouping": {
                "enabled": False,
                "fields": [],
                "collapsed_by_default": True,
                "show_totals": True,
                "total_columns": []
            }
        },
    )

    print(f"✅ Reporte declarativo 'Remitos no facturados' creado exitosamente (slug: remitos-no-facturados)")


def delete_remitos_no_facturados_declarative_report(apps, schema_editor):
    """Elimina el reporte declarativo de Remitos no facturados."""
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
            print("⚠️  Tabla reports_reportdefinition no existe, saltando eliminación de reporte remitos_no_facturados")
            return
    except Exception as e:
        print(f"⚠️  Error verificando tabla: {e}, saltando eliminación de reporte remitos_no_facturados")
        return
    finally:
        cursor.close()
    
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    try:
        ReportDefinition.objects.filter(slug="remitos-no-facturados", empresa__isnull=True).delete()
        print(f"✅ Reporte declarativo 'Remitos no facturados' eliminado exitosamente")
    except Exception as e:
        print(f"⚠️  Error eliminando reporte remitos_no_facturados: {e}")


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0024_add_learned_relationship'),
    ]

    operations = [
        migrations.RunPython(create_remitos_no_facturados_declarative_report, delete_remitos_no_facturados_declarative_report),
    ]
