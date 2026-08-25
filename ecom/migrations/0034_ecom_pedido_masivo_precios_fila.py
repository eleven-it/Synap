# Generated manually — precios de línea en pedido masivo

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ecom", "0033_ecompedidomasivodraft_estado_aprobacion_lote"),
    ]

    operations = [
        migrations.AddField(
            model_name="ecompedidomasivodraft",
            name="precios_fila",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="precios unitarios netos por artículo (id_articulo → decimal)",
                verbose_name="precios unitarios netos por artículo (id_articulo → decimal)",
            ),
        ),
    ]
