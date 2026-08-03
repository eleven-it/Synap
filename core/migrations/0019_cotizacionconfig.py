# CotizacionConfig — configuración BCRA por empresa

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0018_backupsettings_notify_email"),
    ]

    operations = [
        migrations.CreateModel(
            name="CotizacionConfig",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("base_empresa", models.CharField(max_length=64, unique=True)),
                ("id_cotizacion", models.PositiveIntegerField(default=1)),
                (
                    "tipo_cotizacion",
                    models.CharField(
                        choices=[
                            ("bcra_referencia", "BCRA referencia"),
                            ("bcra_compra", "BCRA compra"),
                            ("bcra_venta", "BCRA venta"),
                            ("mid", "Promedio compra/venta"),
                            ("manual_only", "Solo manual (sin sugerencia BCRA)"),
                        ],
                        default="bcra_referencia",
                        max_length=32,
                    ),
                ),
                ("auto_aceptar_job", models.BooleanField(default=False)),
                ("timeout_seg", models.PositiveSmallIntegerField(default=5)),
                ("actualizado_por", models.CharField(default="sistema", max_length=64)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Configuración cotización dólar",
                "verbose_name_plural": "Configuraciones cotización dólar",
            },
        ),
    ]
