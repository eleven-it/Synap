# Data migration — Fase P4 (percepciones IIBB) del change catalogo-carrito-checkout-mayorista

from django.db import migrations


def crear_checkpoint(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.update_or_create(
        module_slug="mayoristapp_percepciones_iibb",
        defaults={
            "notes": (
                "Fase P4: percepciones de Ingresos Brutos (IIBB) en el checkout mayorista, "
                "configurable por implementación vía sucursales.agente_percep. Servicio "
                "ecom/services/mayorista_percepciones.py (paridad jcart.php 1093-1171): "
                "base = neto con descuento (subtotal_neto), lee percep_cli_param + "
                "percep_cli_tipo, importe = base*alicuota/100 (sin importe_minimo). "
                "Integrado transaccionalmente en mayorista_checkout_service.confirmar para "
                "PED/PRE: INSERT percep_cli por tipo + comp_ped.total_percep; bloqueo con "
                "ROLLBACK si agente_percep='Si' y cliente sin percep_cli_param. Flag resuelto "
                "desde la sucursal del usuario (usuarios->sucursales) u override de sesión. "
                "DEV fuera de alcance. Tests 22/22 en test_mayorista_checkout_service. "
                "Ver docs/ecom/PERCEPCIONES_IIBB_P4.md y REQ-CHK-009."
            ),
        },
    )


def revertir_checkpoint(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.filter(module_slug="mayoristapp_percepciones_iibb").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("ecom", "0024_checkpoint_mayoristapp_ui_compra"),
    ]

    operations = [
        migrations.RunPython(crear_checkpoint, revertir_checkpoint),
    ]
