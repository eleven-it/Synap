# Solo crea PuntoVentaCanalEjecutivo en PostgreSQL Synap (panel ejecutivo ventas).
# Evita mezclar CreateModel de otros modelos ya existentes por migraciones RunPython previas.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0030_add_total_consolidado_operativo"),
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
                        choices=[
                            ("mayorista", "Mayorista"),
                            ("minorista", "Minorista (Salón)"),
                        ],
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
    ]
