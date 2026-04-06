# Data migration — Fase C cierre vertical clientes mayoristapp

from django.db import migrations


def crear_checkpoint_clientes(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.get_or_create(
        module_slug="mayoristapp_clientes",
        defaults={
            "notes": (
                "Vertical clientes v1: relay-clientes (búsqueda, selección, comprobante), "
                "domicilio, contacto JSON, cliente rápido (lecturas + alta/edición), "
                "selección en sesión y lista rápida. Ver docs/ecom/SPEC_MAYORISTAPP_CLIENTES.md."
            ),
        },
    )


def revertir_checkpoint_clientes(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.filter(module_slug="mayoristapp_clientes").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("ecom", "0001_initial_ecom_checkpoint"),
    ]

    operations = [
        migrations.RunPython(crear_checkpoint_clientes, revertir_checkpoint_clientes),
    ]
