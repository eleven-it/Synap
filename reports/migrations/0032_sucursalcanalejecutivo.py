from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0031_add_puntoventacanalejecutivo"),
    ]

    operations = [
        migrations.CreateModel(
            name="SucursalCanalEjecutivo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "id_sucursal",
                    models.PositiveIntegerField(verbose_name="ID sucursal (AdministraNET)"),
                ),
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
                        related_name="sucursal_canales_ejecutivo",
                        to="core.empresa",
                        verbose_name="Empresa",
                    ),
                ),
            ],
            options={
                "verbose_name": "Clasificación sucursal — panel ejecutivo",
                "verbose_name_plural": "Clasificaciones sucursal — panel ejecutivo",
            },
        ),
        migrations.AddConstraint(
            model_name="sucursalcanalejecutivo",
            constraint=models.UniqueConstraint(
                fields=("empresa", "id_sucursal"),
                name="reports_suc_canal_unico_por_empresa",
            ),
        ),
        migrations.AddIndex(
            model_name="sucursalcanalejecutivo",
            index=models.Index(
                fields=["empresa", "id_sucursal"],
                name="reports_suc_canal_emp_suc_idx",
            ),
        ),
    ]
