from django.db import migrations


def add_labels(apps, schema_editor):
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")

    report = ReportDefinition.objects.filter(slug="clientes_churn_ltv").first()
    if not report:
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
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")

    report = ReportDefinition.objects.filter(slug="clientes_churn_ltv").first()
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
