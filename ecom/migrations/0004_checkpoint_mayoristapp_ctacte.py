# Data migration — Fase C vertical cuenta corriente (relay-ctacte v1)

from django.db import migrations


def crear_checkpoint(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.get_or_create(
        module_slug="mayoristapp_ctacte",
        defaults={
            "notes": (
                "Cuenta corriente v1 (solo lectura): POST …/ctacte/movimientos/, GET …/ctacte/sugerencias-nro/. "
                "Paridad relay-ctacte.php (JSON; requiere idcliente en sesión). "
                "Ver docs/ecom/SPEC_MAYORISTAPP_CTACTE_RECIBOS.md."
            ),
        },
    )


def revertir(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.filter(module_slug="mayoristapp_ctacte").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("ecom", "0003_checkpoint_mayoristapp_comprobantes"),
    ]

    operations = [
        migrations.RunPython(crear_checkpoint, revertir),
    ]
