from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tiendanube_administranet', '0024_initialsynccheckpoint'),
    ]

    operations = [
        migrations.AddField(
            model_name='productmapping',
            name='adminet_precio_venta_final',
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                max_digits=15,
                null=True,
                verbose_name='Precio Venta Final AdministraNET',
            ),
        ),
        migrations.AddField(
            model_name='productmapping',
            name='adminet_costo_final',
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                max_digits=15,
                null=True,
                verbose_name='Costo Final AdministraNET',
            ),
        ),
    ]
