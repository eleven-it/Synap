from django.db import migrations


def upgrade_clientes_churn(apps, schema_editor):
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
            print("⚠️  Tabla reports_reportdefinition no existe, saltando actualización de widget")
            return
    except Exception as e:
        print(f"⚠️  Error verificando tabla: {e}, saltando actualización de widget")
        return
    finally:
        cursor.close()
    
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")

    try:
        report = ReportDefinition.objects.filter(slug="clientes_churn_ltv").first()
        if not report:
            print("⚠️  Reporte 'clientes_churn_ltv' no encontrado, saltando actualización")
            return
    except Exception as e:
        print(f"⚠️  Error accediendo a ReportDefinition: {e}, saltando actualización")
        return

    report.config = {
        "metrics": ["churn_rate", "retention_rate", "ltv"],
        "dimensions": ["month"],
        "tags": ["customers", "retention"],
        "notes": ["Relación churn vs retención con tamaño proporcional al LTV promedio."],
    }
    report.save(update_fields=["config"])

    widget = ReportWidget.objects.filter(report=report).first()
    if not widget:
        return

    widget.name = "Churn vs Retention Connected"
    widget.widget_type = "d3-connected-scatter"
    widget.configuration = {
        "x_field": "retention_rate",
        "y_field": "churn_rate",
        "label_field": "month",
        "radius_field": "ltv",
    }
    widget.layout = {"w": 6, "h": 4}
    widget.save(update_fields=["name", "widget_type", "configuration", "layout"])


def downgrade_clientes_churn(apps, schema_editor):
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
            print("⚠️  Tabla reports_reportdefinition no existe, saltando reversión de widget")
            return
    except Exception as e:
        print(f"⚠️  Error verificando tabla: {e}, saltando reversión de widget")
        return
    finally:
        cursor.close()
    
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")

    try:
        report = ReportDefinition.objects.filter(slug="clientes_churn_ltv").first()
        if not report:
            print("⚠️  Reporte 'clientes_churn_ltv' no encontrado, saltando reversión")
            return
    except Exception as e:
        print(f"⚠️  Error accediendo a ReportDefinition: {e}, saltando reversión")
        return

    report.config = {
        "metrics": ["churn_rate", "retention_rate", "ltv"],
        "dimensions": ["month", "segment"],
        "tags": ["customers", "retention"],
    }
    report.save(update_fields=["config"])

    widget = ReportWidget.objects.filter(report=report).first()
    if not widget:
        return

    widget.name = "Churn vs Retention"
    widget.widget_type = "d3-line"
    widget.configuration = {
        "x_field": "month",
        "y_field": "churn_rate",
    }
    widget.layout = {"w": 6, "h": 3}
    widget.save(update_fields=["name", "widget_type", "configuration", "layout"])


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0003_translate_reports_es"),
    ]

    operations = [
        migrations.RunPython(upgrade_clientes_churn, downgrade_clientes_churn),
    ]
