# Generated manually for TiendaNube permissions

from django.db import migrations

def create_tiendanube_permissions(apps, schema_editor):
    """Create TiendaNube permissions."""
    Permiso = apps.get_model('core', 'Permiso')
    
    # Create tiendanube.access permission
    Permiso.objects.get_or_create(
        codigo='tiendanube.access',
        defaults={
            'nombre': 'Access TiendaNube integration',
            'descripcion': 'Allows access to TiendaNube integration dashboard and features',
            'activo': True
        }
    )

def remove_tiendanube_permissions(apps, schema_editor):
    """Remove TiendaNube permissions."""
    Permiso = apps.get_model('core', 'Permiso')
    Permiso.objects.filter(codigo='tiendanube.access').delete()

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_alter_systemconfiguration_key'),
    ]

    operations = [
        migrations.RunPython(create_tiendanube_permissions, remove_tiendanube_permissions),
    ] 