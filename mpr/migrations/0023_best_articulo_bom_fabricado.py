# Choices BOM_FABRICADO en BestArticuloMap (sin DDL MySQL legacy).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mpr", "0022_best_operario_map"),
    ]

    operations = [
        migrations.AlterField(
            model_name="bestarticulomap",
            name="origen_requerimiento",
            field=models.CharField(
                choices=[
                    ("PEDIDO_ABIERTO", "Pedido abierto"),
                    ("STOCK_DEPOSITO", "Saldo en depósito"),
                    ("BOM_FABRICADO", "BOM fabricado"),
                    ("HISTORICO", "Histórico / fuera de alcance"),
                ],
                default="PEDIDO_ABIERTO",
                max_length=24,
            ),
        ),
    ]
