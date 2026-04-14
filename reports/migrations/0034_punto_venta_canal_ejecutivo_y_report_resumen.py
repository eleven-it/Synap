# Panel ejecutivo ventas + modelo clasificación PV.
import django.db.models.deletion
from django.db import migrations, models
from django.utils import timezone


def seed_resumen_ejecutivo_report(apps, schema_editor):
    from django.db import connection

    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'reports_reportdefinition'
            );
            """
        )
        if not cursor.fetchone()[0]:
            return
    except Exception:
        return
    finally:
        cursor.close()

    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")
    now = timezone.now()

    report_def, _ = ReportDefinition.objects.update_or_create(
        slug="resumen-ejecutivo-ventas",
        empresa=None,
        defaults={
            "name": "Resumen ejecutivo (ventas)",
            "description": (
                "Panel gerencial: ventas del día, comparativos, tickets, ticket medio, unidades, "
                "mayorista vs salón, ventas por hora y últimos 7 días (solo facturación)."
            ),
            "category": "managerial",
            "config": {
                "metrics": [
                    "ventas_netas",
                    "tickets",
                    "ticket_promedio",
                    "unidades",
                    "mayorista_minorista",
                ],
                "dimensions": ["dia", "hora"],
                "tags": ["ventas", "gerencial", "dashboard"],
            },
            "metadata": {
                "created_by": "system",
                "seeded_at": now.isoformat(),
                "catalog_legacy_section": "listados",
            },
            "refresh_interval": "realtime",
            "is_active": True,
        },
    )

    ReportWidget.objects.filter(report=report_def).delete()
    ReportWidget.objects.create(
        report=report_def,
        name="Panel ejecutivo",
        widget_type="executive-summary",
        order=1,
        layout={"w": 12, "h": 12},
        configuration={"source": "executive_sales_summary"},
    )


def unseed_resumen(apps, schema_editor):
    from django.db import connection

    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'reports_reportdefinition'
            );
            """
        )
        if not cursor.fetchone()[0]:
            return
    finally:
        cursor.close()

    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportDefinition.objects.filter(slug="resumen-ejecutivo-ventas", empresa__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0033_rename_ventas_objetivos_report_title"),
    ]

    operations = [
        migrations.CreateModel(
            name="PuntoVentaCanalEjecutivo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("id_pv", models.PositiveIntegerField(verbose_name="ID punto de venta (AdministraNET)")),
                (
                    "canal",
                    models.CharField(
                        choices=[("mayorista", "Mayorista"), ("minorista", "Minorista (Salón)")],
                        max_length=16,
                        verbose_name="Canal",
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Updated at")),
                (
                    "empresa",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="punto_venta_canales_ejecutivo",
                        to="core.empresa",
                        verbose_name="Empresa",
                    ),
                ),
            ],
            options={
                "verbose_name": "Clasificación PV — panel ejecutivo",
                "verbose_name_plural": "Clasificaciones PV — panel ejecutivo",
            },
        ),
        migrations.AddConstraint(
            model_name="puntoventacanalejecutivo",
            constraint=models.UniqueConstraint(
                fields=("empresa", "id_pv"),
                name="reports_pv_canal_unico_por_empresa",
            ),
        ),
        migrations.AddIndex(
            model_name="puntoventacanalejecutivo",
            index=models.Index(fields=["empresa", "id_pv"], name="reports_pv_canal_emp_pv_idx"),
        ),
        migrations.RunPython(seed_resumen_ejecutivo_report, unseed_resumen),
    ]
