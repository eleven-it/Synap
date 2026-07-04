# Data migration — Fase P3 (restricciones de catálogo por PV) del change catalogo-carrito-checkout-mayorista

from django.db import migrations


def crear_checkpoint(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.update_or_create(
        module_slug="mayoristapp_restricciones_pv",
        defaults={
            "notes": (
                "Fase P3 (item 3): restricciones de catálogo por punto de venta. Reemplaza el baneo "
                "legacy hardcodeado (lista_baneo_productos_fiscal/no_fiscal en sesión, aplicado según "
                "punto_venta.cont) por config genérica en BD (modelo EcomCatalogoRestriccionPV, Postgres). "
                "Por PV se excluye por artículo/rubro/subrubro; el servicio catalogo_restricciones inyecta "
                "excluir_articulos/rubros/subrubros a los filtros y _construir_where_catalogo los traduce a "
                "NOT IN. Aplicado en listado (POST /catalogo/articulos/listado/) y export PDF. Gestionable "
                "por Django admin. Ver docs/ecom/RESTRICCIONES_CATALOGO_PV_P3.md."
            ),
        },
    )


def revertir_checkpoint(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.filter(module_slug="mayoristapp_restricciones_pv").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("ecom", "0022_ecomcatalogorestriccionpv_and_more"),
    ]

    operations = [
        migrations.RunPython(crear_checkpoint, revertir_checkpoint),
    ]
