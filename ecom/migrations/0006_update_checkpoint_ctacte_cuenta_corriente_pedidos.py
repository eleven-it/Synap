# Actualiza notas del checkpoint ctacte (relay-cuenta-corriente.php v1)

from django.db import migrations


NOTAS = (
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
    EcomMigrationCheckpoint.objects.filter(module_slug="mayoristapp_ctacte").update(
        notes=(
            "Cuenta corriente v1 (solo lectura): POST …/ctacte/movimientos/, GET …/ctacte/sugerencias-nro/. "
            "Paridad relay-ctacte.php (JSON; requiere idcliente en sesión). "
            "Ver docs/ecom/SPEC_MAYORISTAPP_CTACTE_RECIBOS.md."
        )
    )


class Migration(migrations.Migration):

    dependencies = [
        ("ecom", "0005_checkpoint_mayoristapp_recibos"),
    ]

    operations = [
        migrations.RunPython(adelante, atras),
    ]
