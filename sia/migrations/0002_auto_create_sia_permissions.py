# Generated migration for automatic SIA permissions creation
# Esta migración crea automáticamente los permisos SIA en PostgreSQL al ejecutar migrate

from django.db import migrations
import logging

logger = logging.getLogger(__name__)


def create_sia_permissions(apps, schema_editor):
    """
    Crea automáticamente los permisos SIA en PostgreSQL durante la migración.
    
    Esta función es idempotente y segura de ejecutar múltiples veces.
    """
    try:
        # Importar aquí para evitar problemas de dependencias circulares
        from core.permissions_utils import ensure_sia_permissions_in_postgres
        
        # Crear/actualizar permisos SIA
        creados, actualizados = ensure_sia_permissions_in_postgres(verbose=False)
        
        logger.info(
            f'SIA permissions migration: {creados} created, {actualizados} updated'
        )
    except Exception as e:
        # En caso de error, loguear pero no fallar la migración
        # Esto permite que el sistema arranque incluso si hay problemas con permisos
        logger.error(
            f'Error al crear permisos SIA en migración: {e}. '
            f'Los permisos pueden ser creados manualmente ejecutando: '
            f'python manage.py create_sia_permissions',
            exc_info=True
        )
        # No re-lanzar la excepción para que la migración continúe


def reverse_create_sia_permissions(apps, schema_editor):
    """
    Función de reversión (opcional).
    
    Por defecto no elimina los permisos al revertir la migración,
    ya que pueden estar siendo usados por otros módulos o usuarios.
    
    Si necesitas eliminar los permisos manualmente:
    python manage.py shell
    >>> from core.models import Permiso
    >>> Permiso.objects.filter(modulo='sia').delete()
    """
    logger.info('Reversión de migración SIA permissions: no se eliminan permisos por seguridad')
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('sia', '0001_initial'),
        # Dependencia de core para asegurar que el modelo Permiso existe
        # Usar la misma dependencia que usa 0001_initial de sia
        ('core', '0007_increase_permiso_codigo_length'),
    ]

    operations = [
        migrations.RunPython(
            create_sia_permissions,
            reverse_create_sia_permissions,
            atomic=True,  # Ejecutar en una transacción
        ),
    ]

