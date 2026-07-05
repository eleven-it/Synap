# Data migration — Fase P2 checkout mayorista (change catalogo-carrito-checkout-mayorista)

from django.db import migrations


def crear_checkpoint_checkout(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.update_or_create(
        module_slug="mayoristapp_checkout",
        defaults={
            "notes": (
                "Fase P2: confirmación del carrito con alta de comprobante legacy PED/PRE. "
                "Transacción MySQL AdministraNET (comp_ped + stockp + cliente_datos_adicionales; "
                "stock_deposito solo PED) con autocommit off y COMMIT/ROLLBACK. Numeración codmov "
                "y talonarios con SELECT ... FOR UPDATE (corrige el bug de concurrencia del PHP), "
                "validación de stock disponible en el commit, idempotencia por estado del carrito "
                "y precio recalculado con el motor único. Autorización por límite de crédito "
                "(cuentacliente + credito_limite_dias). Fuera de alcance: CAE/FE, medios de pago/caja, "
                "percepciones IIBB (total_percep=0) y devolución (P3). "
                "Ver docs/ecom/CHECKOUT_MAYORISTA_P2.md."
            ),
        },
    )


def revertir_checkpoint_checkout(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.filter(module_slug="mayoristapp_checkout").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("ecom", "0017_ecomcart_autorizacion_ecomcart_codigo_movimiento_and_more"),
    ]

    operations = [
        migrations.RunPython(crear_checkpoint_checkout, revertir_checkpoint_checkout),
    ]
