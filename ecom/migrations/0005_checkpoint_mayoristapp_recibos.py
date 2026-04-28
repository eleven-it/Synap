# Data migration — Fase C vertical recibos cobranzas (relay-recibos v1)

from django.db import migrations


def crear_checkpoint(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.get_or_create(
        module_slug="mayoristapp_recibos",
        defaults={
            "notes": (
                "Recibos v1 (solo lectura): POST …/recibos/listado/?ajax=1&consulta=1. "
                "Paridad relay-recibos.php lista_recibos (JSON). "
                "Ver docs/ecom/SPEC_MAYORISTAPP_CTACTE_RECIBOS.md."
            ),
        },
    )


def revertir(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.filter(module_slug="mayoristapp_recibos").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("ecom", "0004_checkpoint_mayoristapp_ctacte"),
    ]

    operations = [
        migrations.RunPython(crear_checkpoint, revertir),
    ]
