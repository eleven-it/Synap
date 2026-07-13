# Alcance cutover BEST→MPR: requerido_migracion solo pedidos abiertos (+ futuro stock depósito).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mpr", "0019_bestcliente_inferencia"),
    ]

    operations = [
        migrations.AddField(
            model_name="bestarticulomap",
            name="requerido_migracion",
            field=models.BooleanField(db_index=True, default=True),
        ),
        migrations.AddField(
            model_name="bestarticulomap",
            name="en_snapshot_abierto",
            field=models.BooleanField(db_index=True, default=True),
        ),
        migrations.AddField(
            model_name="bestarticulomap",
            name="origen_requerimiento",
            field=models.CharField(
                choices=[
                    ("PEDIDO_ABIERTO", "Pedido abierto"),
                    ("STOCK_DEPOSITO", "Saldo en depósito"),
                    ("HISTORICO", "Histórico / fuera de alcance"),
                ],
                default="PEDIDO_ABIERTO",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="bestclientemap",
            name="requerido_migracion",
            field=models.BooleanField(db_index=True, default=True),
        ),
        migrations.AddField(
            model_name="bestclientemap",
            name="en_snapshot_abierto",
            field=models.BooleanField(db_index=True, default=True),
        ),
        migrations.AddField(
            model_name="bestclientemap",
            name="origen_requerimiento",
            field=models.CharField(
                choices=[
                    ("PEDIDO_ABIERTO", "Pedido abierto"),
                    ("STOCK_DEPOSITO", "Saldo en depósito"),
                    ("HISTORICO", "Histórico / fuera de alcance"),
                ],
                default="PEDIDO_ABIERTO",
                max_length=24,
            ),
        ),
    ]
