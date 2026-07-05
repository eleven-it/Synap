# Checkpoint F0 — Module shell + API REST v1 piloto (change ecom-migracion-completa)

from django.db import migrations


def crear_checkpoint(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.update_or_create(
        module_slug="mayoristapp_modulo_shell",
        defaults={
            "notes": (
                "F0 ecom-migracion-completa: módulo ecom en MODULE_CONFIGS + ModuleConfig (0026), "
                "menu_config.py, permisos ecom.*, hub GET /ecom/mayoristapp/ (7 cards PHP), "
                "API REST v1 piloto POST /ecom/api/v1/mayoristapp/comprobantes/pedidos/ y "
                "GET .../pedidos/sugerencias-numero/; legacy pedidos con header Deprecation. "
                "Docs: INVENTARIO_HUB_MAYORISTAPP.md, API_REST_V1_MAPPING.md."
            ),
        },
    )


def revertir_checkpoint(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.filter(module_slug="mayoristapp_modulo_shell").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("ecom", "0026_moduleconfig_ecom"),
    ]

    operations = [
        migrations.RunPython(crear_checkpoint, revertir_checkpoint),
    ]
