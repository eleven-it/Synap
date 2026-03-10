# Migración merge: resuelve conflicto entre 0002_add_opt_codigo_movimiento y 0003_mprconfig.
# Ejecutar si aparece: "multiple leaf nodes in the migration graph: (0001_opt_optlinea 2, 0003_mprconfig in mpr)".

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("mpr", "0002_add_opt_codigo_movimiento"),
        ("mpr", "0003_mprconfig"),
    ]

    operations = []
