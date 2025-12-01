from django.db import migrations


def translate_cash_flow_detailed_movements(apps, schema_editor):
    """Traduce el reporte de Movimientos Detallados de Flujo de Caja al español."""
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")

    try:
        report = ReportDefinition.objects.get(slug="cash_flow_detailed_movements", empresa__isnull=True)
    except ReportDefinition.DoesNotExist:
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



