# Data migration — Fase P3 (devolución DEV) del change catalogo-carrito-checkout-mayorista

from django.db import migrations


def crear_checkpoint_devolucion(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.update_or_create(
        module_slug="mayoristapp_devolucion",
        defaults={
            "notes": (
                "Fase P3 (item 1): alta de devolución (DEV) reutilizando el servicio "
                "transaccional de checkout (mayorista_checkout_service.confirmar con tipo='DEV'). "
                "Mismo comp_ped/stockp/numeración FOR UPDATE que PED; diferencias: TipoComp='Devolucion', "
                "stock_deposito.saldo_pedido_cliente incrementa SIN validación de disponible "
                "(paridad legacy alta_devolucion_confirmado.php). Corrige el bug del PHP que numeraba "
                "el talonario 'PED' al dar de alta un 'DEV'. Endpoint compartido "
                "/ecom/api/mayoristapp/checkout/confirmar/ (body tipo='DEV'). Ver docs/ecom/CHECKOUT_MAYORISTA_P2.md."
            ),
        },
    )


def revertir_checkpoint_devolucion(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.filter(module_slug="mayoristapp_devolucion").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("ecom", "0019_alter_ecomcart_tipo_comprobante"),
    ]

    operations = [
        migrations.RunPython(crear_checkpoint_devolucion, revertir_checkpoint_devolucion),
    ]
