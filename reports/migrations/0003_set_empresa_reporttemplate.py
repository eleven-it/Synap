from django.db import migrations


def set_empresa_activa(apps, schema_editor):
    Empresa = apps.get_model('core', 'Empresa')
    ReportTemplate = apps.get_model('reports', 'ReportTemplate')
    empresa_activa = Empresa.objects.filter(activa=True).first()
    if empresa_activa:
        ReportTemplate.objects.filter(empresa__isnull=True).update(empresa=empresa_activa)

class Migration(migrations.Migration):
    dependencies = [
        ('reports', '0002_reporttemplate_empresa'),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(set_empresa_activa, reverse_code=migrations.RunPython.noop),
    ] 