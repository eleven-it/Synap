# CAEA por período quincenal (obtención/renovación automática).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("fe_afip", "0001_initial_afip_config"),
    ]

    operations = [
        migrations.CreateModel(
            name="CAEACode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("base_empresa", models.CharField(db_index=True, help_text="Nombre de la base de datos administraNET.", max_length=64, verbose_name="Base empresa (DB)")),
                ("periodo", models.CharField(help_text="Año y mes, ej. 202601.", max_length=6, verbose_name="Período YYYYMM")),
                ("orden", models.SmallIntegerField(help_text="1 = días 1-15, 2 = días 16-fin de mes.", verbose_name="Orden quincena")),
                ("codigo", models.CharField(help_text="Valor devuelto por AFIP.", max_length=24, verbose_name="Código CAEA")),
                ("vencimiento", models.DateField(blank=True, help_text="Fin de vigencia del período (último día de la quincena).", null=True, verbose_name="Vencimiento")),
                ("requested_at", models.DateTimeField(auto_now_add=True, verbose_name="Solicitado el")),
                (
                    "source",
                    models.CharField(
                        choices=[("consultar", "Consultar"), ("solicitar", "Solicitar")],
                        default="solicitar",
                        max_length=16,
                        verbose_name="Origen",
                    ),
                ),
            ],
            options={
                "verbose_name": "CAEA por período",
                "verbose_name_plural": "CAEAs por período",
            },
        ),
        migrations.AddConstraint(
            model_name="caeacode",
            constraint=models.UniqueConstraint(
                fields=("base_empresa", "periodo", "orden"),
                name="fe_afip_caea_unique_periodo_orden",
            ),
        ),
        migrations.AddIndex(
            model_name="caeacode",
            index=models.Index(fields=["base_empresa", "periodo", "orden"], name="fe_afip_cae_base_em_2a1b0d_idx"),
        ),
    ]
