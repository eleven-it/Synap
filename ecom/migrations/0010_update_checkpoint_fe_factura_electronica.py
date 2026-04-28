# Actualiza checkpoint FE con relay_factura_electronica v1

from django.db import migrations


NOTAS = (
    "FE/NC v1 parcial: POST …/fe/nota-credito/listado/, "
    "GET …/fe/nota-credito/sugerencias-nro/, "
    "POST …/fe/factura-electronica/listado/, "
    "GET …/fe/factura-electronica/sugerencias-nro/. "
    "Paridad relay_nota_credito + relay_factura_electronica (JSON). "
    "Ver docs/ecom/SPEC_MAYORISTAPP_FE_NC.md."
)

NOTAS_ANTERIOR = (
    "FE/NC v1 parcial: POST …/fe/nota-credito/listado/, "
    "GET …/fe/nota-credito/sugerencias-nro/. "
    "Paridad relay_nota_credito.php (JSON). "
    "Ver docs/ecom/SPEC_MAYORISTAPP_FE_NC.md."
)


def adelante(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.filter(module_slug="mayoristapp_fe").update(notes=NOTAS)


def atras(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.filter(module_slug="mayoristapp_fe").update(notes=NOTAS_ANTERIOR)


class Migration(migrations.Migration):

    dependencies = [
        ("ecom", "0009_checkpoint_mayoristapp_fe_nota_credito"),
    ]

    operations = [
        migrations.RunPython(adelante, atras),
    ]
