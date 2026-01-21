from django.db import migrations


def delete_ventas_netas_v2_report(apps, schema_editor):
    """Elimina el reporte Ventas Netas v2 de la base de datos."""
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
        print("✅ Reporte ventas_netas_v2 eliminado exitosamente")
    except Exception as e:
        print(f"⚠️  Error eliminando reporte ventas_netas_v2: {e}")


def reverse_delete_ventas_netas_v2_report(apps, schema_editor):
    """No hacer nada en reversa - el reporte fue eliminado intencionalmente."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0018_reportdefinitionversion_reportworkspace_and_more'),
    ]

    operations = [
        migrations.RunPython(delete_ventas_netas_v2_report, reverse_delete_ventas_netas_v2_report),
    ]





