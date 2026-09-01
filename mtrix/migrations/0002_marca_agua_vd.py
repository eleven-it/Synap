from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mtrix", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="mtrixconfig",
            name="last_vd_enviado_hasta",
            field=models.DateField(
                blank=True,
                help_text="Marca de agua: avanza solo si el SFTP de la corrida fue OK.",
                null=True,
                verbose_name="Último VD enviado hasta",
            ),
        ),
        migrations.AlterField(
            model_name="mtrixconfig",
            name="cnpj_fornecedor",
            field=models.CharField(
                blank=True,
                help_text="Obsoleto: se deriva del CUIT de datosempresa.",
                max_length=20,
                verbose_name="CNPJ fornecedor",
            ),
        ),
        migrations.AlterField(
            model_name="mtrixconfig",
            name="dias_a_procesar",
            field=models.PositiveIntegerField(
                default=5,
                help_text="Solo la primera corrida automática, mientras no haya marca de agua de VD.",
                verbose_name="Días a procesar",
            ),
        ),
    ]
