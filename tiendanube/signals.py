"""
Señales para el módulo Tiendanube que usan TiendaNubeService centralizado.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
import logging

from .models_synap import (
    TiendaNubeConfig, TiendaNubeProductMapping, TiendaNubeCustomerMapping, 
    TiendaNubeOrderMapping, TiendaNubeSyncLog
)
from .models_adminet import TiendaNubeCondVentaMap, TiendaNubeAdminetConfig, TiendaNubeClienteMap

logger = logging.getLogger(__name__)

def get_tiendanube_service(config=None):
    """Función centralizada para obtener instancia de TiendaNubeService."""
    if config is None:
        config = TiendaNubeConfig.objects.first()
    if not config:
        return None
    from .services_main import TiendaNubeService
    return TiendaNubeService(config)

@receiver(post_save, sender=TiendaNubeProductMapping)
def product_mapping_saved(sender, instance, created, **kwargs):
    """
    Señal que se dispara cuando se guarda un mapping de producto.
    Puede usar TiendaNubeService para sincronización automática.
    """
    try:
        if created and instance.sync_enabled:
            # Nuevo mapping creado, posiblemente sincronizar automáticamente
            service = get_tiendanube_service()
            if service:
                logger.info(f"Product mapping created for {instance.product.sku}, sync enabled")
                # Aquí se podría agregar lógica de sincronización automática si es necesario
    except Exception as e:
        logger.error(f"Error in product_mapping_saved signal: {str(e)}")

@receiver(post_save, sender=TiendaNubeConfig)
def config_saved(sender, instance, created, **kwargs):
    """
    Señal que se dispara cuando se guarda una configuración de Tiendanube.
    Puede usar TiendaNubeService para validar la configuración.
    """
    try:
        if created or instance.is_configured:
            # Nueva configuración o configuración actualizada
            service = get_tiendanube_service(instance)
            if service:
                # Validar conexión
                ok, msg = service.test_connection()
                if ok:
                    logger.info(f"Tiendanube configuration validated successfully for store {instance.store_id}")
                else:
                    logger.warning(f"Tiendanube configuration validation failed for store {instance.store_id}: {msg}")
    except Exception as e:
        logger.error(f"Error in config_saved signal: {str(e)}")

@receiver(post_save, sender=TiendaNubeCondVentaMap)
def cond_venta_map_saved(sender, instance, created, **kwargs):
    """
    Señal que se dispara cuando se guarda un mapeo de condición de venta.
    Específico para integración administraNET.
    """
    try:
        if created:
            logger.info(f"Condition of sale mapping created: {instance.payment_method} -> {instance.adminet_codigo}")
        else:
            logger.info(f"Condition of sale mapping updated: {instance.payment_method} -> {instance.adminet_codigo}")
    except Exception as e:
        logger.error(f"Error in cond_venta_map_saved signal: {str(e)}")


@receiver(post_save, sender=TiendaNubeClienteMap)
def cliente_map_saved(sender, instance, created, **kwargs):
    """
    Señal que se dispara cuando se guarda un mapeo de cliente.
    Específico para integración administraNET.
    """
    try:
        if created:
            logger.info(f"Customer mapping created: {instance.tiendanube_email} -> {instance.adminet_codigo}")
        else:
            logger.info(f"Customer mapping updated: {instance.tiendanube_email} -> {instance.adminet_codigo}")
    except Exception as e:
        logger.error(f"Error in cliente_map_saved signal: {str(e)}")


@receiver(post_delete, sender=TiendaNubeClienteMap)
def cliente_map_deleted(sender, instance, **kwargs):
    """
    Señal que se dispara cuando se elimina un mapeo de cliente.
    """
    try:
        logger.info(f"Customer mapping deleted: {instance.tiendanube_email} -> {instance.adminet_codigo}")
    except Exception as e:
        logger.error(f"Error in cliente_map_deleted signal: {str(e)}")

@receiver(post_save, sender=TiendaNubeAdminetConfig)
def adminet_config_saved(sender, instance, created, **kwargs):
    """
    Señal que se dispara cuando se guarda una configuración de administraNET.
    Puede usar TiendaNubeService para validar la configuración.
    """
    try:
        if created and instance.is_active:
            logger.info(f"AdministraNET configuration activated: {instance.database} on {instance.host}")
            # Aquí se podría agregar lógica de validación de conexión MySQL si es necesario
    except Exception as e:
        logger.error(f"Error in adminet_config_saved signal: {str(e)}")

@receiver(post_delete, sender=TiendaNubeProductMapping)
def product_mapping_deleted(sender, instance, **kwargs):
    """
    Señal que se dispara cuando se elimina un mapping de producto.
    Puede usar TiendaNubeService para limpiar datos en Tiendanube.
    """
    try:
        logger.info(f"Product mapping deleted for {instance.product.sku}")
        # Aquí se podría agregar lógica para limpiar datos en Tiendanube si es necesario
    except Exception as e:
        logger.error(f"Error in product_mapping_deleted signal: {str(e)}")

@receiver(post_save, sender=TiendaNubeSyncLog)
def sync_log_saved(sender, instance, created, **kwargs):
    """
    Señal que se dispara cuando se guarda un log de sincronización.
    Puede usar TiendaNubeService para notificaciones o análisis.
    """
    try:
        if created:
            logger.info(f"Sync log created: {instance.sync_type} - {instance.status}")
            # Aquí se podría agregar lógica de notificaciones o análisis si es necesario
    except Exception as e:
        logger.error(f"Error in sync_log_saved signal: {str(e)}") 