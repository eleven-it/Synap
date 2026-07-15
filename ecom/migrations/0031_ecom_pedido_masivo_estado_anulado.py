# Estado anulado en borrador pedido masivo (soft-delete recuperable)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ecom", "0030_ecom_pedido_masivo_descuentos"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ecompedidomasivodraft",
            name="estado",
            field=models.CharField(
                choices=[
                    ("borrador", "Borrador"),
                    ("confirmando", "Confirmando"),
                    ("confirmado", "Confirmado"),
                    ("archivado", "Archivado"),
                    ("anulado", "Anulado"),
                ],
                db_index=True,
                default="borrador",
                max_length=16,
                verbose_name="estado",
            ),
        ),
    ]
