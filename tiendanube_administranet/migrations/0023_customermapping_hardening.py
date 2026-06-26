# Endurecimiento CustomerMapping — unicidad adminet_codigo y defaults seguros

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tiendanube_administranet', '0022_legacy_managed_and_api_url'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customermapping',
            name='sync_direction',
            field=models.CharField(
                choices=[
                    ('bidirectional', 'Bidirectional'),
                    ('tiendanube_to_adminet', 'Tiendanube → AdministraNET'),
                    ('adminet_to_tiendanube', 'AdministraNET → Tiendanube'),
                ],
                default='tiendanube_to_adminet',
                max_length=30,
                verbose_name='Sync Direction',
            ),
        ),
        migrations.AlterField(
            model_name='customermapping',
            name='sync_enabled',
            field=models.BooleanField(default=False, verbose_name='Sync Enabled'),
        ),
        migrations.AddConstraint(
            model_name='customermapping',
            constraint=models.UniqueConstraint(
                condition=models.Q(('adminet_codigo__isnull', False)),
                fields=('adminet_codigo',),
                name='unique_customermapping_adminet_codigo',
            ),
        ),
    ]
