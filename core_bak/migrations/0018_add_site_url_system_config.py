from django.db import migrations

def add_site_url_config(apps, schema_editor):
    SystemConfiguration = apps.get_model('core', 'SystemConfiguration')
    if not SystemConfiguration.objects.filter(key='main.site.url').exists():
        SystemConfiguration.objects.create(
            key='main.site.url',
            value='https://tudominio.com',
            description='URL base pública del sitio para imágenes y enlaces externos.',
            is_active=True
        )

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0017_alter_systemconfiguration_key'),
    ]
    operations = [
        migrations.RunPython(add_site_url_config),
    ] 