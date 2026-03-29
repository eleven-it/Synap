from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("factura_compra_captura", "0003_expediente_permisos_fase3"),
    ]

    operations = [
        migrations.AlterField(
            model_name="expedientefacturacompra",
            name="codigo_proveedor_legacy",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Código en tabla proveedor de AdministraNET",
                null=True,
                verbose_name="Código proveedor",
            ),
        ),
    ]
