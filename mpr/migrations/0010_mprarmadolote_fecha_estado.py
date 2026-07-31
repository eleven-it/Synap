# Generated manually for armado lote fecha/estado/borrador

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mpr", "0009_armado_unificado_lote_imputacion"),
    ]

    operations = [
        migrations.AddField(
            model_name="mprarmadolote",
            name="fecha_realizado",
            field=models.DateField(
                blank=True,
                help_text="Fecha de realizado del armado (puede ser pasada). UI: dd/MM/yyyy.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="mprarmadolote",
            name="estado",
            field=models.CharField(
                default="aprobado",
                help_text="borrador | aprobado | anulado",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="mprarmadolote",
            name="movimiento_fisico_ok",
            field=models.BooleanField(
                default=True,
                help_text="True si ya hay MSTOCK del lote",
            ),
        ),
        migrations.AddField(
            model_name="mprarmadolote",
            name="detalle",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Detalle cabecera del lote",
                max_length=500,
            ),
        ),
    ]
