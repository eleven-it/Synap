# Incluye relay-consumos-resumen en notas del checkpoint mayoristapp_ctacte

from django.db import migrations


NOTAS = (
    "Cuenta corriente v1: POST …/ctacte/movimientos/, GET …/ctacte/sugerencias-nro/ (cuentacliente). "
    "Pedidos cliente: POST …/ctacte/pedidos/, GET …/ctacte/pedidos/sugerencias-nro/. "
    "Consumos resumen: POST …/ctacte/consumos-resumen/ (stock agregado + precios v1; ver advertencia JSON). "
    "Paridad JSON; requiere idcliente en sesión. Ver docs/ecom/SPEC_MAYORISTAPP_CTACTE_RECIBOS.md."
)

NOTAS_ANTERIOR = (
    "Cuenta corriente v1: POST …/ctacte/movimientos/, GET …/ctacte/sugerencias-nro/ (cuentacliente). "
    "Pedidos del cliente (relay-cuenta-corriente.php): POST …/ctacte/pedidos/, "
    "GET …/ctacte/pedidos/sugerencias-nro/. Paridad JSON; requiere idcliente en sesión. "
    "Ver docs/ecom/SPEC_MAYORISTAPP_CTACTE_RECIBOS.md."
)


def adelante(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.filter(module_slug="mayoristapp_ctacte").update(notes=NOTAS)


def atras(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.filter(module_slug="mayoristapp_ctacte").update(notes=NOTAS_ANTERIOR)


class Migration(migrations.Migration):

    dependencies = [
        ("ecom", "0006_update_checkpoint_ctacte_cuenta_corriente_pedidos"),
    ]

    operations = [
        migrations.RunPython(adelante, atras),
    ]
