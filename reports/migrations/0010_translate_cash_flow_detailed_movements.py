from django.db import migrations


def translate_cash_flow_detailed_movements(apps, schema_editor):
    """Traduce el reporte de Movimientos Detallados de Flujo de Caja al español."""
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
            print("⚠️  Tabla reports_reportdefinition no existe, saltando traducción de cash_flow_detailed_movements")
            return
    except Exception as e:
        print(f"⚠️  Error verificando tabla: {e}, saltando traducción de cash_flow_detailed_movements")
        return
    finally:
        cursor.close()
    
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")

    try:
        report = ReportDefinition.objects.get(slug="cash_flow_detailed_movements", empresa__isnull=True)
    except ReportDefinition.DoesNotExist:
        print("⚠️  Reporte 'cash_flow_detailed_movements' no encontrado, saltando traducción")
        return
    except Exception as e:
        print(f"⚠️  Error accediendo a ReportDefinition: {e}, saltando traducción")
        return

    report.name = "Movimientos Detallados de Flujo de Caja"
    report.description = "Vista detallada de cada movimiento individual de caja con información completa: fecha, tipo, categoría, cliente/proveedor, medio de pago, importe, cuenta y flujo. Permite análisis detallado, auditoría y trazabilidad de movimientos."
    report.save(update_fields=["name", "description", "updated_at"])

    # Traducir widgets
    ReportWidget.objects.filter(report=report, name="Tabla de Movimientos Detallados").update(
        name="Tabla de Movimientos Detallados"
    )


def reverse_translation(apps, schema_editor):
    # No se implementa reversión explícita
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0009_add_cash_flow_detailed_movements"),
    ]

    operations = [
        migrations.RunPython(translate_cash_flow_detailed_movements, reverse_translation),
    ]



