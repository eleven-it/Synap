from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tiendanube_administranet', '0025_productmapping_precios_finales_adminet'),
    ]

    operations = [
        migrations.AddField(
            model_name='tiendanubeconfig',
            name='location_id',
            field=models.PositiveBigIntegerField(
                blank=True,
                help_text='ID de ubicación Tienda Nube para inventory_levels; vacío omite location_id del payload de stock.',
                null=True,
                verbose_name='Location ID',
            ),
        ),
    ]
