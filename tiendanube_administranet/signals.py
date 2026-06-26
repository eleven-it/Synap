"""
Señales de Django para la integración Tiendanube-AdministraNET.
"""

import logging

from django.db.models.signals import post_delete, post_save
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


def _log_mapping_event(mapping: CustomerMapping, event: str) -> None:
    """Registra evento de mapeo usando el schema válido de SyncLog."""
    tn_cfg = TiendanubeConfig.objects.filter(is_active=True).first()
    an_cfg = AdministraNETConfig.objects.filter(is_active=True).first()
    SyncLog.objects.create(
        sync_type=SyncLog.SyncType.CUSTOMER,
        direction=SyncLog.SyncDirection.TO_ADMINET,
        status=SyncLog.Status.COMPLETED,
        total_items=1,
        processed_items=1,
        successful_items=1,
        failed_items=0,
        tiendanube_config=tn_cfg,
        adminet_config=an_cfg,
        details={
            'event': event,
            'mapping_id': mapping.id,
            'tiendanube_email': mapping.tiendanube_email,
        },
    )


@receiver(post_save, sender=CustomerMapping)
def customer_mapping_post_save(sender, instance, created, **kwargs):
    """Señal post_save de CustomerMapping."""
    try:
        if created:
            logger.info("Nuevo mapeo de cliente creado: %s", instance)
            _log_mapping_event(instance, 'mapping_create')
            if instance.sync_enabled and instance.sync_status == 'pending':
                _schedule_sync_pending_async()
                logger.info("Sincronización programada para mapeo %s", instance.id)
        else:
            logger.info("Mapeo de cliente actualizado: %s", instance)
            _log_mapping_event(instance, 'mapping_update')
            if instance.sync_enabled and instance.sync_status == 'pending':
                _schedule_sync_pending_async()
                logger.info("Sincronización programada para mapeo actualizado %s", instance.id)
    except Exception as e:
        logger.error("Error en señal post_save de CustomerMapping: %s", e)


@receiver(post_delete, sender=CustomerMapping)
def customer_mapping_post_delete(sender, instance, **kwargs):
    """Señal post_delete de CustomerMapping."""
    try:
        logger.info("Mapeo de cliente eliminado: %s", instance.tiendanube_email)
        tn_cfg = TiendanubeConfig.objects.filter(is_active=True).first()
        an_cfg = AdministraNETConfig.objects.filter(is_active=True).first()
        SyncLog.objects.create(
            sync_type=SyncLog.SyncType.CUSTOMER,
            direction=SyncLog.SyncDirection.TO_ADMINET,
            status=SyncLog.Status.COMPLETED,
            total_items=1,
            processed_items=1,
            successful_items=1,
            failed_items=0,
            tiendanube_config=tn_cfg,
            adminet_config=an_cfg,
            details={
                'event': 'mapping_delete',
                'tiendanube_email': instance.tiendanube_email,
            },
        )
    except Exception as e:
        logger.error("Error en señal post_delete de CustomerMapping: %s", e)


@receiver(post_save, sender=TiendanubeConfig)
def tiendanube_config_post_save(sender, instance, created, **kwargs):
    """Una sola configuración Tienda Nube activa."""
    try:
        if created:
            logger.info("Nueva configuración de Tiendanube creada: %s", instance.name)
        else:
            logger.info("Configuración de Tiendanube actualizada: %s", instance.name)
        if instance.is_active:
            TiendanubeConfig.objects.exclude(id=instance.id).update(is_active=False)
            logger.info("Configuración %s activada, otras desactivadas", instance.name)
    except Exception as e:
        logger.error("Error en señal post_save de TiendanubeConfig: %s", e)


@receiver(post_save, sender=AdministraNETConfig)
def adminet_config_post_save(sender, instance, created, **kwargs):
    """Una sola configuración AdministraNET activa."""
    try:
        if created:
            logger.info("Nueva configuración de AdministraNET creada: %s", instance.name)
        else:
            logger.info("Configuración de AdministraNET actualizada: %s", instance.name)
        if instance.is_active:
            AdministraNETConfig.objects.exclude(id=instance.id).update(is_active=False)
            logger.info("Configuración %s activada, otras desactivadas", instance.name)
    except Exception as e:
        logger.error("Error en señal post_save de AdministraNETConfig: %s", e)


@receiver(post_save, sender=SyncLog)
def sync_log_post_save(sender, instance, created, **kwargs):
    """Log de nivel según estado del SyncLog."""
    try:
        if created:
            if instance.status == SyncLog.Status.FAILED:
                logger.warning("Log de sincronización fallido: %s", instance.error_message)
            else:
                logger.info(
                    "Log de sincronización: %s - %s",
                    instance.sync_type,
                    instance.status,
                )
    except Exception as e:
        logger.error("Error en señal post_save de SyncLog: %s", e)


@receiver(post_save, sender='tiendanube_administranet.ProductMapping')
def product_mapping_post_save(sender, instance, created, **kwargs):
    try:
        if created:
            logger.info("Nuevo mapeo de producto creado: %s", instance)
        else:
            logger.info("Mapeo de producto actualizado: %s", instance)
    except Exception as e:
        logger.error("Error en señal post_save de ProductMapping: %s", e)


@receiver(post_save, sender='tiendanube_administranet.OrderMapping')
def order_mapping_post_save(sender, instance, created, **kwargs):
    try:
        if created:
            logger.info("Nuevo mapeo de orden creado: %s", instance)
        else:
            logger.info("Mapeo de orden actualizado: %s", instance)
    except Exception as e:
        logger.error("Error en señal post_save de OrderMapping: %s", e)
