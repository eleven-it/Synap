# Actualiza checkpoint comprobantes con relays no-cancelados v1

from django.db import migrations


NOTAS = (
    "Comprobantes v1 (solo lectura): POST …/comprobantes/pedidos/, presupuestos/, remitos/, "
    "POST …/comprobantes/no-cancelados/, POST …/comprobantes/no-cancelados-resumen/, "
    "GET …/comprobantes/sugerencias-nro/, GET …/comprobantes/comprobante-a-mail/ "
    "(payload/token fin-comprobante, sin SMTP). Ver docs/ecom/SPEC_MAYORISTAPP_COMPROBANTES.md."
)

NOTAS_ANTERIOR = (
    "Comprobantes v1 (solo lectura): POST …/comprobantes/pedidos/, presupuestos/, remitos/; "
    "GET …/comprobantes/sugerencias-nro/; "
    "GET …/comprobantes/comprobante-a-mail/ (payload/token fin-comprobante, sin SMTP). "
    "Ver docs/ecom/SPEC_MAYORISTAPP_COMPROBANTES.md."
)


def adelante(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.filter(module_slug="mayoristapp_comprobantes").update(notes=NOTAS)


def atras(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.filter(module_slug="mayoristapp_comprobantes").update(
        notes=NOTAS_ANTERIOR
    )


class Migration(migrations.Migration):

    dependencies = [
        ("ecom", "0011_update_checkpoint_fe_facturas_imputar"),
    ]

    operations = [
        migrations.RunPython(adelante, atras),
    ]
