# Migración merge: une ramas 0002_add_opt_codigo_movimiento y 0003_mprconfig.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("mpr", "0002_add_opt_codigo_movimiento"),
        ("mpr", "0003_mprconfig"),
    ]

    operations = []
