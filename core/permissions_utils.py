"""
Utilidades para gestión de permisos del sistema.
Funciones reutilizables para crear y sincronizar permisos entre PostgreSQL y MySQL.
"""
import logging
from typing import Dict, List, Tuple
from django.db import transaction
from core.models import Permiso

logger = logging.getLogger(__name__)


# Definición de permisos SIA (centralizada)
SIA_PERMISSIONS_DATA = [
    {
        'codigo': 'sia.manage_cycles',
        'nombre': 'Gestionar Ciclos de Evaluación',
        'descripcion': 'Permite crear, editar y eliminar ciclos de evaluación estratégica',
        'modulo': 'sia',
    },
    {
        'codigo': 'sia.view_company_dashboard',
        'nombre': 'Ver Dashboard Consolidado',
        'descripcion': 'Permite ver el dashboard ejecutivo con datos consolidados de la empresa',
        'modulo': 'sia',
    },
    {
        'codigo': 'sia.view_own_responses',
        'nombre': 'Ver Propias Respuestas',
        'descripcion': 'Permite ver las propias respuestas de encuesta estratégica',
        'modulo': 'sia',
    },
    {
        'codigo': 'sia.create_response',
        'nombre': 'Crear Respuestas',
        'descripcion': 'Permite crear nuevas respuestas de encuesta estratégica',
        'modulo': 'sia',
    },
    {
        'codigo': 'sia.view_all_responses',
        'nombre': 'Ver Todas las Respuestas',
        'descripcion': 'Permite ver todas las respuestas de la empresa (rol administrativo)',
        'modulo': 'sia',
    },
]


@transaction.atomic
def ensure_sia_permissions_in_postgres(verbose: bool = False) -> Tuple[int, int]:
    """
    Asegura que los permisos SIA existan en PostgreSQL (core.models.Permiso).
    
    Esta función es idempotente: si los permisos ya existen, los actualiza si es necesario.
    Puede ser llamada múltiples veces sin causar errores.
    
    Args:
        verbose: Si True, loguea información detallada (útil para comandos de gestión)
    
    Returns:
        Tuple[int, int]: (cantidad_creados, cantidad_actualizados)
    
    Raises:
        Exception: Si hay un error crítico al crear/actualizar permisos
    """
    creados = 0
    actualizados = 0
    
    try:
        for permiso_data in SIA_PERMISSIONS_DATA:
            codigo = permiso_data['codigo']
            
            # Intentar obtener o crear el permiso
            permiso, created = Permiso.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'nombre': permiso_data['nombre'],
                    'descripcion': permiso_data.get('descripcion', ''),
                    'modulo': permiso_data.get('modulo', 'sia'),
                    'activo': True,
                }
            )
            
            if created:
                creados += 1
                if verbose:
                    logger.info(f'✓ Permiso creado: {codigo}')
            else:
                # Actualizar si hay cambios
                updated = False
                for key, value in permiso_data.items():
                    if key != 'codigo' and getattr(permiso, key, None) != value:
                        setattr(permiso, key, value)
                        updated = True
                
                # Asegurar que esté activo
                if not permiso.activo:
                    permiso.activo = True
                    updated = True
                
                if updated:
                    permiso.save()
                    actualizados += 1
                    if verbose:
                        logger.info(f'↻ Permiso actualizado: {codigo}')
        
        if verbose:
            logger.info(
                f'SIA permissions ensured in PostgreSQL: {creados} created, {actualizados} updated'
            )
        
        return creados, actualizados
        
    except Exception as e:
        logger.error(f'Error al asegurar permisos SIA en PostgreSQL: {e}', exc_info=True)
        raise


def get_sia_permissions_data() -> List[Dict]:
    """
    Retorna la lista de definiciones de permisos SIA.
    
    Returns:
        Lista de diccionarios con la definición de cada permiso SIA
    """
    return SIA_PERMISSIONS_DATA.copy()













