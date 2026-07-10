# Generated manually for embalaje en carrito mayorista

from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ecom", "0027_checkpoint_mayoristapp_modulo_shell"),
    ]

    operations = [
        migrations.AddField(
            model_name="ecomcartitem",
            name="tipo_unidad",
            field=models.CharField(
                blank=True,
                default="Unidad",
                max_length=16,
                verbose_name="tipo unidad",
            ),
        ),
        migrations.AddField(
            model_name="ecomcartitem",
            name="cantidad_dividir",
            field=models.DecimalField(
                decimal_places=3,
                default=Decimal("1"),
                max_digits=14,
                verbose_name="cantidad dividir",
            ),
        ),
    ]
