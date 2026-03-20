# Añade id_operario_opt a OptLinea (operario por línea de OPT).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mpr", "0004_merge_20260310_mpr_leafs"),
    ]

    operations = [
        migrations.AddField(
            model_name="optlinea",
            name="id_operario_opt",
            field=models.IntegerField(
                blank=True,
                help_text="id_sue_abm_empleado del operario que fabrica esta línea.",
                null=True,
            ),
        ),
    ]
