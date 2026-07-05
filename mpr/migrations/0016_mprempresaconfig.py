# Configuración operativa MPR por empresa (bloqueo parte vs Fabricando).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mpr", "0015_mprpartelinea_id_articulo_componente"),
    ]

    operations = [
        migrations.CreateModel(
            name="MprEmpresaConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("base_empresa", models.CharField(db_index=True, help_text="Base MySQL AdministraNET (ej. administranet92).", max_length=64, unique=True)),
                (
                    "bloquear_parte_supera_fabricando",
                    models.BooleanField(
                        default=False,
                        help_text="Si está activo, rechaza el parte cuando la suma por componente supera Fabricando (enviado − stock Producción).",
                    ),
                ),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Configuración MPR por empresa",
                "verbose_name_plural": "Configuraciones MPR por empresa",
                "db_table": "mpr_empresa_config",
            },
        ),
    ]
