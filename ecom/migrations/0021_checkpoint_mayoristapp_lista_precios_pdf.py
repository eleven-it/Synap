# Data migration — Fase P3 (export lista de precios PDF) del change catalogo-carrito-checkout-mayorista

from django.db import migrations


def crear_checkpoint(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.update_or_create(
        module_slug="mayoristapp_lista_precios_pdf",
        defaults={
            "notes": (
                "Fase P3 (item 2): export de lista de precios a PDF (reportlab, A3 landscape) "
                "migrando exporta_lista_pdf.php. Reutiliza el catálogo P0 (mismos filtros y motor "
                "de precios) sin paginar. Guardrails del runbook: corte por VOLUMEN previo "
                "(LP_PDF_MAX_ITEMS/_CON_IMAGEN) y por TIEMPO durante el armado "
                "(LP_PDF_MAX_SECONDS/_CON_IMAGEN, revisado cada 50 filas) con página HTML amigable "
                "en español. Umbrales en settings (config/env), defaults = paridad legacy. "
                "Servicio ecom/services/lista_precio_pdf.py; vista ecom/lista_precio_pdf_relay_views.py; "
                "ruta GET /ecom/api/mayoristapp/catalogo/lista-precios.pdf. "
                "Ver docs/ecom/LISTA_PRECIOS_PDF_P3.md y docs/general/RUNBOOK_EXPORTACION_PDF.md."
            ),
        },
    )


def revertir_checkpoint(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.filter(module_slug="mayoristapp_lista_precios_pdf").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("ecom", "0020_checkpoint_mayoristapp_devolucion"),
    ]

    operations = [
        migrations.RunPython(crear_checkpoint, revertir_checkpoint),
    ]
