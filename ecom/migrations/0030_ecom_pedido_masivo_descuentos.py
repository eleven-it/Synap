# Generated manually — Oleada D pedido masivo descuentos

from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ecom", "0029_ecom_pedido_masivo_draft"),
    ]

    operations = [
        migrations.AddField(
            model_name="ecompedidomasivodraft",
            name="descuento_pie_pct",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0"),
                max_digits=6,
                verbose_name="descuento pie lote %",
            ),
        ),
        migrations.AddField(
            model_name="ecompedidomasivodraft",
            name="descuentos_fila",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="descuentos % por artículo (id_articulo → pct)",
                verbose_name="descuentos % por artículo (id_articulo → pct)",
            ),
        ),
    ]
