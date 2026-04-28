# Data migration — Fase C vertical FE/NC (relay_nota_credito v1)

from django.db import migrations


def crear_checkpoint(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.get_or_create(
        module_slug="mayoristapp_fe",
        defaults={
            "notes": (
                "FE/NC v1 parcial: POST …/fe/nota-credito/listado/, "
                "GET …/fe/nota-credito/sugerencias-nro/. "
                "Paridad relay_nota_credito.php (JSON). "
                "Ver docs/ecom/SPEC_MAYORISTAPP_FE_NC.md."
            ),
        },
    )


def revertir(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.filter(module_slug="mayoristapp_fe").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("ecom", "0008_update_checkpoint_comprobantes_mail_payload"),
    ]

    operations = [
        migrations.RunPython(crear_checkpoint, revertir),
    ]
