# Generated manually: credenciales y host MySQL unificados en Synap (DATABASES['mysql']).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("tiendanube_administranet", "0020_administranetconfig_punto_venta_tiendanube_id"),
    ]

    operations = [
        migrations.RemoveField(model_name="administranetconfig", name="host"),
        migrations.RemoveField(model_name="administranetconfig", name="port"),
        migrations.RemoveField(model_name="administranetconfig", name="user"),
        migrations.RemoveField(model_name="administranetconfig", name="password"),
    ]
