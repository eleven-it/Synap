from django.db import migrations


def add_labels(apps, schema_editor):
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
            print("⚠️  Tabla reports_reportdefinition no existe, saltando actualización de labels")
            return
    except Exception as e:
        print(f"⚠️  Error verificando tabla: {e}, saltando actualización de labels")
        return
    finally:
        cursor.close()
    
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")

    try:
        report = ReportDefinition.objects.filter(slug="clientes_churn_ltv").first()
        if not report:
            print("⚠️  Reporte 'clientes_churn_ltv' no encontrado, saltando actualización de labels")
            return
    except Exception as e:
        print(f"⚠️  Error accediendo a ReportDefinition: {e}, saltando actualización de labels")
        return

    config = report.config or {}
    config.setdefault("x_label", "Tasa de retención")
    config.setdefault("y_label", "Tasa de churn")
    config.setdefault("grid", True)
    report.config = config
    report.save(update_fields=["config"])

    widget = ReportWidget.objects.filter(report=report).first()
    if not widget:
        return

    widget.configuration = {
        **widget.configuration,
        "x_label": "Tasa de retención",
        "y_label": "Tasa de churn",
        "grid": True,
    }
    widget.save(update_fields=["configuration"])


def remove_labels(apps, schema_editor):
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
            print("⚠️  Tabla reports_reportdefinition no existe, saltando reversión de labels")
            return
    except Exception as e:
        print(f"⚠️  Error verificando tabla: {e}, saltando reversión de labels")
        return
    finally:
        cursor.close()
    
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")

    try:
        report = ReportDefinition.objects.filter(slug="clientes_churn_ltv").first()
        if not report:
            print("⚠️  Reporte 'clientes_churn_ltv' no encontrado, saltando reversión de labels")
            return
    except Exception as e:
        print(f"⚠️  Error accediendo a ReportDefinition: {e}, saltando reversión de labels")
        return
    
    if report:
        config = report.config or {}
        config.pop("x_label", None)
        config.pop("y_label", None)
        config.pop("grid", None)
        report.config = config
        report.save(update_fields=["config"])

    widget = ReportWidget.objects.filter(report__slug="clientes_churn_ltv").first()
    if widget:
        config = widget.configuration or {}
        config.pop("x_label", None)
        config.pop("y_label", None)
        config.pop("grid", None)
        widget.configuration = config
        widget.save(update_fields=["configuration"])


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0004_update_clientes_churn_widget"),
    ]

    operations = [
        migrations.RunPython(add_labels, remove_labels),
    ]
