# Campos modo simple en borrador pedido masivo (cod_mov_origen, modo, id_domicilio_fijo)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ecom", "0031_ecom_pedido_masivo_estado_anulado"),
    ]

    operations = [
        migrations.AddField(
            model_name="ecompedidomasivodraft",
            name="cod_mov_origen",
            field=models.IntegerField(
                blank=True,
                help_text="PED pendiente cargado para edición anula+crea (modo simple).",
                null=True,
                verbose_name="CodigoMovimiento PED origen",
            ),
        ),
        migrations.AddField(
            model_name="ecompedidomasivodraft",
            name="modo",
            field=models.CharField(
                choices=[("masivo", "Masivo"), ("simple", "Simple")],
                db_index=True,
                default="masivo",
                max_length=16,
                verbose_name="modo captura",
            ),
        ),
        migrations.AddField(
            model_name="ecompedidomasivodraft",
            name="id_domicilio_fijo",
            field=models.IntegerField(
                blank=True,
                help_text="Única columna en modo simple (id_cliente_domicilio).",
                null=True,
                verbose_name="cliente_domicilio fijo",
            ),
        ),
    ]
