# El depósito de producción se define solo con tipo_mpr=Producción en MySQL (deposito).
# Se elimina el modelo MprConfig (Synap/PostgreSQL) que guardaba id_deposito_produccion.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("mpr", "0006_alter_opt_options_alter_optlinea_options"),
    ]

    operations = [
        migrations.DeleteModel(name="MprConfig"),
    ]
