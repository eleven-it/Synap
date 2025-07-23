# Generated manually for timestamp-based sync implementation

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0002_brand_empresa_category_empresa_subcategory_empresa'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='last_synced_with_adminet',
            field=models.DateTimeField(
                blank=True, 
                null=True, 
                help_text='Timestamp of last successful sync with administraNET',
                verbose_name='Last Synced with administraNET'
            ),
        ),
    ] 