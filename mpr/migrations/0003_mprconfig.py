# Generated migration for MprConfig (depósito de producción por base_empresa).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mpr", "0002_add_opt_codigo_movimiento"),
    ]

    operations = [
        migrations.CreateModel(
            name="MprConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("base_empresa", models.CharField(db_index=True, max_length=64, unique=True)),
                (
                    "id_deposito_produccion",
                    models.IntegerField(
                        blank=True,
                        help_text="Depósito de producción: donde se registra el stock al liberar la OPT (automático).",
                        null=True,
                    ),
                ),
            ],
            options={
                "db_table": "mpr_config",
                "verbose_name": "Configuración MPR",
                "verbose_name_plural": "Configuraciones MPR",
            },
        ),
    ]
