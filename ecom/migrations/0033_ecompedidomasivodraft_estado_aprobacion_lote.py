# Estado comercial agregado del lote masivo confirmado

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ecom", "0032_ecom_pedido_masivo_draft_modo_simple"),
    ]

    operations = [
        migrations.AddField(
            model_name="ecompedidomasivodraft",
            name="estado_aprobacion_lote",
            field=models.CharField(
                choices=[
                    ("-", "Sin aprobación comercial"),
                    ("pendiente", "Pendiente"),
                    ("aprobado", "Aprobado"),
                    ("rechazado", "Rechazado"),
                    ("error", "Error"),
                ],
                db_index=True,
                default="-",
                max_length=16,
                verbose_name="estado aprobación comercial del lote",
            ),
        ),
    ]
