# Bloqueo parte vs Fabricando activo por defecto.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mpr", "0016_mprempresaconfig"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mprempresaconfig",
            name="bloquear_parte_supera_fabricando",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "Si está activo, rechaza el parte cuando la suma por componente "
                    "supera Fabricando (enviado − stock Producción)."
                ),
            ),
        ),
    ]
