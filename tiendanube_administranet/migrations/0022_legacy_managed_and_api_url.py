# Generated manually — managed=False modelos legacy + default api_url 2025-03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tiendanube_administranet', '0021_remove_administranetconfig_mysql_credentials'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='AdministraNETDepartamento',
            options={
                'managed': False,
                'verbose_name': 'AdministraNET Departamento',
                'verbose_name_plural': 'AdministraNET Departamentos',
            },
        ),
        migrations.AlterModelOptions(
            name='AdministraNETDistrito',
            options={
                'managed': False,
                'verbose_name': 'AdministraNET Distrito',
                'verbose_name_plural': 'AdministraNET Distritos',
            },
        ),
        migrations.AlterModelOptions(
            name='AdministraNETPais',
            options={
                'managed': False,
                'verbose_name': 'AdministraNET País',
                'verbose_name_plural': 'AdministraNET Países',
            },
        ),
        migrations.AlterModelOptions(
            name='AdministraNETProvincia',
            options={
                'managed': False,
                'verbose_name': 'AdministraNET Provincia',
                'verbose_name_plural': 'AdministraNET Provincias',
            },
        ),
        migrations.AlterModelOptions(
            name='AdministraNETTipoCliente',
            options={
                'managed': False,
                'verbose_name': 'AdministraNET Tipo Cliente',
                'verbose_name_plural': 'AdministraNET Tipos Cliente',
            },
        ),
        migrations.AlterModelOptions(
            name='AdministraNETViajante',
            options={
                'managed': False,
                'verbose_name': 'AdministraNET Viajante',
                'verbose_name_plural': 'AdministraNET Viajantes',
            },
        ),
        migrations.AlterField(
            model_name='tiendanubeconfig',
            name='api_url',
            field=models.URLField(
                default='https://api.tiendanube.com/2025-03',
                help_text='Referencia; los servicios usan NUVEMSHOP_API_VERSION (2025-03).',
                verbose_name='API URL',
            ),
        ),
    ]
