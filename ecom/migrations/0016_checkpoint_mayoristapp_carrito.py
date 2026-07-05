# Data migration — Fase P1 carrito mayorista (change catalogo-carrito-checkout-mayorista)

from django.db import migrations


def crear_checkpoint_carrito(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.update_or_create(
        module_slug="mayoristapp_carrito",
        defaults={
            "notes": (
                "Fase P1: carrito borrador en Postgres synap (EcomCart/EcomCartItem). "
                "Precio vía motor único (resolver_precio_articulo), stock con StockService, "
                "totales con desglose 21/10,5/exento + impuesto interno + descuento al pie "
                "(paridad Jcart.update_subtotal). Sin escritura MySQL legacy (llega en P2). "
                "Ver docs/ecom/CARRITO_MAYORISTA_P1.md."
            ),
        },
    )


def revertir_checkpoint_carrito(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.filter(module_slug="mayoristapp_carrito").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("ecom", "0015_ecomcart_ecomcartitem_and_more"),
    ]

    operations = [
        migrations.RunPython(crear_checkpoint_carrito, revertir_checkpoint_carrito),
    ]
