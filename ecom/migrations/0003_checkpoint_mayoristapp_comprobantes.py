# Data migration — Fase C vertical comprobantes (listados v1)

from django.db import migrations


def crear_checkpoint(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.get_or_create(
        module_slug="mayoristapp_comprobantes",
        defaults={
            "notes": (
                "Comprobantes v1 (solo lectura): POST …/comprobantes/pedidos/, presupuestos/, remitos/; "
                "GET …/comprobantes/sugerencias-nro/. Paridad relay-pedidos/presupuestos/remitos (JSON). "
                "Ver docs/ecom/SPEC_MAYORISTAPP_COMPROBANTES.md."
            ),
        },
    )


def revertir(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.filter(module_slug="mayoristapp_comprobantes").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("ecom", "0002_checkpoint_mayoristapp_clientes"),
    ]

    operations = [
        migrations.RunPython(crear_checkpoint, revertir),
    ]
