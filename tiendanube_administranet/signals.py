"""
Señales de Django para la integración Tiendanube-AdministraNET.
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone

from .models import AdministraNETConfig, CustomerMapping, SyncLog, TiendanubeConfig

logger = logging.getLogger(__name__)


def _schedule_sync_pending_async():
    """Encola tarea Celery si está disponible; si no, solo registra."""
    try:
        from .tasks.sync_tasks import sync_pending_mappings_task

        if hasattr(sync_pending_mappings_task, "apply_async"):
            sync_pending_mappings_task.apply_async(countdown=30)
        else:
            logger.debug("Celery no configurado: omitiendo cola de sync_pending_mappings")
    except Exception as exc:
        logger.warning("No se pudo programar sincronización en segundo plano: %s", exc)


@receiver(post_save, sender=CustomerMapping)
def customer_mapping_post_save(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta después de guardar un CustomerMapping.
    
    Args:
        sender: Modelo que envió la señal
        instance: Instancia del CustomerMapping
        created: True si es una nueva instancia
    """
    try:
        if created:
            # Nuevo mapeo creado
            logger.info(f"Nuevo mapeo de cliente creado: {instance}")
            
            # Registrar log de creación
            SyncLog.objects.create(
                sync_type='mapping_create',
                status='success',
                platform='both',
                mapping=instance,
                message=f"Mapeo creado para {instance.tiendanube_email}",
                started_at=timezone.now()
            )
            
            # Si el mapeo está habilitado y es pendiente, programar sincronización
            if instance.sync_enabled and instance.sync_status == 'pending':
                # Programar tarea de sincronización (con delay para evitar bloqueos)
                _schedule_sync_pending_async()
                logger.info(f"Sincronización programada para mapeo {instance.id}")
        
        else:
            # Mapeo actualizado
            logger.info(f"Mapeo de cliente actualizado: {instance}")
            
            # Registrar log de actualización
            SyncLog.objects.create(
                sync_type='mapping_update',
                status='success',
                platform='both',
                mapping=instance,
                message=f"Mapeo actualizado para {instance.tiendanube_email}",
                started_at=timezone.now()
            )
            
            # Si el estado cambió a pendiente y está habilitado, programar sincronización
            if instance.sync_enabled and instance.sync_status == 'pending':
                _schedule_sync_pending_async()
                logger.info(f"Sincronización programada para mapeo actualizado {instance.id}")
                
    except Exception as e:
        logger.error(f"Error en señal post_save de CustomerMapping: {str(e)}")


@receiver(post_delete, sender=CustomerMapping)
def customer_mapping_post_delete(sender, instance, **kwargs):
    """
    Señal que se ejecuta después de eliminar un CustomerMapping.
    
    Args:
        sender: Modelo que envió la señal
        instance: Instancia del CustomerMapping eliminado
    """
    try:
        logger.info(f"Mapeo de cliente eliminado: {instance}")
        
        # Registrar log de eliminación
        SyncLog.objects.create(
            sync_type='mapping_delete',
            status='success',
            platform='both',
            mapping=None,  # Ya no existe la instancia
            message=f"Mapeo eliminado para {instance.tiendanube_email}",
            started_at=timezone.now()
        )
        
    except Exception as e:
        logger.error(f"Error en señal post_delete de CustomerMapping: {str(e)}")


@receiver(post_save, sender=TiendanubeConfig)
def tiendanube_config_post_save(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta después de guardar una configuración de Tiendanube.
    
    Args:
        sender: Modelo que envió la señal
        instance: Instancia de TiendanubeConfig
        created: True si es una nueva instancia
    """
    try:
        if created:
            logger.info(f"Nueva configuración de Tiendanube creada: {instance.name}")
        else:
            logger.info(f"Configuración de Tiendanube actualizada: {instance.name}")
            
        # Si esta configuración se activó, desactivar las demás
        if instance.is_active:
            TiendanubeConfig.objects.exclude(id=instance.id).update(is_active=False)
            logger.info(f"Configuración {instance.name} activada, otras desactivadas")
            
    except Exception as e:
        logger.error(f"Error en señal post_save de TiendanubeConfig: {str(e)}")


@receiver(post_save, sender=AdministraNETConfig)
def adminet_config_post_save(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta después de guardar una configuración de AdministraNET.
    
    Args:
        sender: Modelo que envió la señal
        instance: Instancia de AdministraNETConfig
        created: True si es una nueva instancia
    """
    try:
        if created:
            logger.info(f"Nueva configuración de AdministraNET creada: {instance.name}")
        else:
            logger.info(f"Configuración de AdministraNET actualizada: {instance.name}")
            
        # Si esta configuración se activó, desactivar las demás
        if instance.is_active:
            AdministraNETConfig.objects.exclude(id=instance.id).update(is_active=False)
            logger.info(f"Configuración {instance.name} activada, otras desactivadas")
            
    except Exception as e:
        logger.error(f"Error en señal post_save de AdministraNETConfig: {str(e)}")


@receiver(post_save, sender=SyncLog)
def sync_log_post_save(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta después de guardar un SyncLog.
    
    Args:
        sender: Modelo que envió la señal
        instance: Instancia de SyncLog
        created: True si es una nueva instancia
    """
    try:
        if created:
            # Log de nivel apropiado según el estado
            if instance.status == 'error':
                logger.error(f"Log de sincronización: {instance.error_message}")
            elif instance.status == 'failed':
                logger.warning(f"Log de sincronización: {instance.error_message}")
            else:
                logger.info(f"Log de sincronización: {instance.sync_type} - {instance.status}")
                
    except Exception as e:
        logger.error(f"Error en señal post_save de SyncLog: {str(e)}")


# Señales para productos (futuras implementaciones)
@receiver(post_save, sender='tiendanube_administranet.ProductMapping')
def product_mapping_post_save(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta después de guardar un ProductMapping.
    
    Args:
        sender: Modelo que envió la señal
        instance: Instancia del ProductMapping
        created: True si es una nueva instancia
    """
    try:
        if created:
            logger.info(f"Nuevo mapeo de producto creado: {instance}")
        else:
            logger.info(f"Mapeo de producto actualizado: {instance}")
            
    except Exception as e:
        logger.error(f"Error en señal post_save de ProductMapping: {str(e)}")


# Señales para órdenes (futuras implementaciones)
@receiver(post_save, sender='tiendanube_administranet.OrderMapping')
def order_mapping_post_save(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta después de guardar un OrderMapping.
    
    Args:
        sender: Modelo que envió la señal
        instance: Instancia del OrderMapping
        created: True si es una nueva instancia
    """
    try:
        if created:
            logger.info(f"Nuevo mapeo de orden creado: {instance}")
        else:
            logger.info(f"Mapeo de orden actualizado: {instance}")
            
    except Exception as e:
        logger.error(f"Error en señal post_save de OrderMapping: {str(e)}") 