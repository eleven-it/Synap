# Generated manually to fix ordering issue

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mercadopago', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='mercadopagoconfig',
            options={
                'verbose_name': 'MercadoPago Configuration',
                'verbose_name_plural': 'MercadoPago Configurations',
                'ordering': ['empresa'],
            },
        ),
    ] 