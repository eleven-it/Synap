# Generated migration to fix remitos_no_facturados slug

from django.db import migrations


def fix_remitos_slug(apps, schema_editor):
    """
    Actualiza el slug de remitos_no_facturados a remitos-no-facturados
    para cumplir con la validación de slug (solo guiones, no guiones bajos).
    """
    ReportDefinition = apps.get_model('reports', 'ReportDefinition')
    
    try:
        # Buscar reporte con slug antiguo
        report = ReportDefinition.objects.filter(slug='remitos_no_facturados').first()
        if report:
            # Verificar que no exista ya uno con el slug nuevo
            existing = ReportDefinition.objects.filter(slug='remitos-no-facturados').first()
            if existing:
                # Si existe uno con el slug nuevo, eliminar el antiguo
                print(f"⚠️  Reporte con slug 'remitos-no-facturados' ya existe. Eliminando el antiguo.")
                report.delete()
            else:
                # Actualizar el slug
                report.slug = 'remitos-no-facturados'
                report.save(update_fields=['slug'])
                print(f"✅ Slug actualizado: 'remitos_no_facturados' -> 'remitos-no-facturados'")
        else:
            print(f"ℹ️  No se encontró reporte con slug 'remitos_no_facturados'")
    except Exception as e:
        print(f"⚠️  Error actualizando slug: {e}")


def reverse_fix_remitos_slug(apps, schema_editor):
    """
    Revertir el cambio (no recomendado, pero necesario para rollback).
    """
    ReportDefinition = apps.get_model('reports', 'ReportDefinition')
    
    try:
        report = ReportDefinition.objects.filter(slug='remitos-no-facturados').first()
        if report:
            # Verificar que no exista ya uno con el slug antiguo
            existing = ReportDefinition.objects.filter(slug='remitos_no_facturados').first()
            if existing:
                print(f"⚠️  Reporte con slug 'remitos_no_facturados' ya existe. No se puede revertir.")
            else:
                report.slug = 'remitos_no_facturados'
                report.save(update_fields=['slug'])
                print(f"⚠️  Slug revertido: 'remitos-no-facturados' -> 'remitos_no_facturados'")
    except Exception as e:
        print(f"⚠️  Error revirtiendo slug: {e}")


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0025_add_remitos_no_facturados_declarative'),
    ]

    operations = [
        migrations.RunPython(fix_remitos_slug, reverse_fix_remitos_slug),
    ]

