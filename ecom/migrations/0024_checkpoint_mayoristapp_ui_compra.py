# Data migration — Fase P3 (UI web compra mayorista) del change catalogo-carrito-checkout-mayorista

from django.db import migrations


def crear_checkpoint(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.update_or_create(
        module_slug="mayoristapp_ui_compra",
        defaults={
            "notes": (
                "Fase P3 (item 4): UI web del vertical mayorista (catálogo → carrito → checkout) "
                "en una sola pantalla estilo POS. Vista CompraMayoristaView + plantilla "
                "ecom/templates/ecom/compra_mayorista.html (extiende base_app.html, Alpine 3, "
                "patrones canónicos slate/sky, contenedor full-width). Consume las APIs P0/P1/P2/P3: "
                "listado, carrito (GET/POST/PATCH/DELETE/vaciar/descuento-pie), checkout confirmar "
                "(PED/PRE/DEV) y link a lista-precios.pdf. Ruta /ecom/mayoristapp/compra/. "
                "Ver docs/ecom/UI_COMPRA_MAYORISTA_P3.md y docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md."
            ),
        },
    )


def revertir_checkpoint(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.filter(module_slug="mayoristapp_ui_compra").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("ecom", "0023_checkpoint_mayoristapp_restricciones_pv"),
    ]

    operations = [
        migrations.RunPython(crear_checkpoint, revertir_checkpoint),
    ]
