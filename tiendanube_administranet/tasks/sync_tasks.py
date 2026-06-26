"""
Tareas de Celery para sincronización automática entre Tiendanube y AdministraNET.
"""

import logging

try:
    from celery import shared_task
except ImportError:  # Celery opcional en instalaciones mínimas
    def shared_task(*args, **kwargs):
        def _decorator(f):
            return f
        return _decorator
from django.utils import timezone
from typing import Dict, Any, Optional

from ..utils.feature_flags import (
    tiendanube_auto_sync_disabled_reason,
    tiendanube_sync_disabled_reason,
)
from ..services.sync_service import TiendanubeAdministraNETSyncService
from ..services.initial_sync_service import InitialSyncService
from ..models import CustomerMapping, SyncLog, TiendanubeConfig, AdministraNETConfig

logger = logging.getLogger(__name__)


def _sync_disabled_response(
    tiendanube_config: Optional[TiendanubeConfig] = None,
) -> Dict[str, Any]:
    reason = tiendanube_sync_disabled_reason(tiendanube_config)
    return {
        'success': False,
        'error': reason or 'Sincronización deshabilitada',
        'timestamp': timezone.now().isoformat(),
    }


@shared_task(bind=True, name='tiendanube_adminet.sync_customers_from_tiendanube')
def sync_customers_from_tiendanube_task(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """
    Tarea para sincronizar clientes desde Tiendanube hacia AdministraNET.
    
    Args:
        limit: Número máximo de clientes a sincronizar
        offset: Número de clientes a saltar
        
    Returns:
        Dict con el resultado de la sincronización
    """
    try:
        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        if tiendanube_sync_disabled_reason(tiendanube_config):
            return _sync_disabled_response(tiendanube_config)
        logger.info(f"Iniciando sincronización desde Tiendanube (limit={limit}, offset={offset})")
        
        # Crear servicio de sincronización
        sync_service = TiendanubeAdministraNETSyncService()
        
        # Ejecutar sincronización
        result = sync_service.sync_customers_from_tiendanube()
        
        if not result.get('success'):
            return {
                'success': False,
                'error': result.get('message', 'Error en sincronización'),
                'timestamp': timezone.now().isoformat()
            }

        result_out = {
            'success': True,
            'success_count': result.get('successful', 0),
            'failed_count': result.get('failed', 0),
            'total_processed': result.get('total_processed', 0),
            'timestamp': timezone.now().isoformat()
        }
        
        logger.info(f"Sincronización desde Tiendanube completada: {result_out['success_count']} exitosos, {result_out['failed_count']} fallidos")
        
        return result_out
        
    except Exception as e:
        error_msg = f"Error en tarea de sincronización desde Tiendanube: {str(e)}"
        logger.error(error_msg)
        
        # Registrar error en log
        try:
            SyncLog.objects.create(
                sync_type=SyncLog.SyncType.CUSTOMER,
                direction=SyncLog.SyncDirection.TO_ADMINET,
                status=SyncLog.Status.FAILED,
                error_message=error_msg,
            )
        except Exception as log_error:
            logger.error(f"Error registrando log: {str(log_error)}")
        
        return {
            'success': False,
            'error': error_msg,
            'timestamp': timezone.now().isoformat()
        }


@shared_task(bind=True, name='tiendanube_adminet.sync_customers_from_adminet')
def sync_customers_from_adminet_task(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """
    Tarea para sincronizar clientes desde AdministraNET hacia Tiendanube.
    
    Args:
        limit: Número máximo de clientes a sincronizar
        offset: Número de clientes a saltar
        
    Returns:
        Dict con el resultado de la sincronización
    """
    try:
        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        if tiendanube_sync_disabled_reason(tiendanube_config):
            return _sync_disabled_response(tiendanube_config)
        logger.info(f"Iniciando sincronización desde AdministraNET (limit={limit}, offset={offset})")
        
        # Crear servicio de sincronización
        sync_service = TiendanubeAdministraNETSyncService()
        
        # Ejecutar sincronización
        result = sync_service.sync_customers_from_adminet(limit=limit, offset=offset)
        
        if not result.get('success'):
            return {
                'success': False,
                'error': result.get('message', 'Error en sincronización'),
                'timestamp': timezone.now().isoformat()
            }

        result_out = {
            'success': True,
            'success_count': result.get('successful', 0),
            'failed_count': result.get('failed', 0),
            'total_processed': result.get('total_processed', 0),
            'timestamp': timezone.now().isoformat()
        }
        
        logger.info(f"Sincronización desde AdministraNET completada: {result_out['success_count']} exitosos, {result_out['failed_count']} fallidos")
        
        return result_out
        
    except Exception as e:
        error_msg = f"Error en tarea de sincronización desde AdministraNET: {str(e)}"
        logger.error(error_msg)
        
        # Registrar error en log
        try:
            SyncLog.objects.create(
                sync_type=SyncLog.SyncType.CUSTOMER,
                direction=SyncLog.SyncDirection.FROM_ADMINET,
                status=SyncLog.Status.FAILED,
                error_message=error_msg,
            )
        except Exception as log_error:
            logger.error(f"Error registrando log: {str(log_error)}")
        
        return {
            'success': False,
            'error': error_msg,
            'timestamp': timezone.now().isoformat()
        }


@shared_task(bind=True, name='tiendanube_adminet.initial_sync_batch')
def initial_sync_batch_task(
    self,
    sync_type: str = 'customer',
    limit: int = 30,
) -> Dict[str, Any]:
    """
    Procesa un lote de la sync masiva inicial Adminet → Tienda Nube.

    Args:
        sync_type: ``customer`` o ``product``
        limit: Tamaño del lote

    Returns:
        Dict con resultado del lote y estado del checkpoint
    """
    try:
        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        if tiendanube_sync_disabled_reason(tiendanube_config):
            return _sync_disabled_response(tiendanube_config)

        adminet_config = AdministraNETConfig.objects.filter(is_active=True).first()
        if not adminet_config:
            return {
                'success': False,
                'error': 'No hay configuración de AdministraNET activa',
                'timestamp': timezone.now().isoformat(),
            }

        logger.info(
            'Sync inicial por lotes (%s, limit=%s, offset desde checkpoint)',
            sync_type,
            limit,
        )
        service = InitialSyncService(tiendanube_config, adminet_config)
        result = service.run_next_pending_batch(sync_type=sync_type, limit=limit)
        result['timestamp'] = timezone.now().isoformat()
        return result

    except Exception as e:
        error_msg = f'Error en sync inicial por lotes ({sync_type}): {str(e)}'
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg,
            'sync_type': sync_type,
            'timestamp': timezone.now().isoformat(),
        }


@shared_task(bind=True, name='tiendanube_adminet.sync_pending_mappings')
def sync_pending_mappings_task(self) -> Dict[str, Any]:
    """
    Tarea para sincronizar mapeos pendientes.
    
    Returns:
        Dict con el resultado de la sincronización
    """
    try:
        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        if tiendanube_sync_disabled_reason(tiendanube_config):
            return _sync_disabled_response(tiendanube_config)
        logger.info("Iniciando sincronización de mapeos pendientes")
        
        # Crear servicio de sincronización
        sync_service = TiendanubeAdministraNETSyncService()
        
        # Obtener mapeos pendientes
        pending_mappings = CustomerMapping.objects.filter(
            sync_status='pending',
            sync_enabled=True
        ).order_by('created_at')[:50]  # Procesar máximo 50 por vez
        
        success_count = 0
        failed_count = 0
        errors = []
        
        for mapping in pending_mappings:
            try:
                if mapping.sync_direction == 'tiendanube_to_adminet':
                    success, message = sync_service.sync_customer_to_adminet(mapping)
                elif mapping.sync_direction == 'adminet_to_tiendanube':
                    success, message = sync_service.sync_customer_to_tiendanube(mapping)
                else:  # bidirectional
                    # Intentar sincronizar en ambas direcciones
                    success1, message1 = sync_service.sync_customer_to_adminet(mapping)
                    success2, message2 = sync_service.sync_customer_to_tiendanube(mapping)
                    success = success1 and success2
                    message = f"Adminet: {message1}, Tiendanube: {message2}"
                
                if success:
                    success_count += 1
                else:
                    failed_count += 1
                    errors.append(f"Mapping {mapping.id}: {message}")
                    
            except Exception as e:
                failed_count += 1
                error_msg = f"Error procesando mapping {mapping.id}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        # Registrar resultado
        result = {
            'success': True,
            'success_count': success_count,
            'failed_count': failed_count,
            'total_processed': success_count + failed_count,
            'errors': errors[:10],  # Solo los primeros 10 errores
            'timestamp': timezone.now().isoformat()
        }
        
        logger.info(f"Sincronización de mapeos pendientes completada: {success_count} exitosos, {failed_count} fallidos")
        
        return result
        
    except Exception as e:
        error_msg = f"Error en tarea de sincronización de mapeos pendientes: {str(e)}"
        logger.error(error_msg)
        
        return {
            'success': False,
            'error': error_msg,
            'timestamp': timezone.now().isoformat()
        }


@shared_task(bind=True, name='tiendanube_adminet.test_connections')
def test_connections_task(self) -> Dict[str, Any]:
    """
    Tarea para probar las conexiones con ambas plataformas.
    
    Returns:
        Dict con el resultado de las pruebas
    """
    try:
        logger.info("Iniciando prueba de conexiones")
        
        # Crear servicio de sincronización
        sync_service = TiendanubeAdministraNETSyncService()
        
        # Probar conexiones
        result = sync_service.test_connections()
        
        # Registrar resultado
        result['timestamp'] = timezone.now().isoformat()
        
        logger.info(f"Prueba de conexiones completada: {result['success']}")
        
        return result
        
    except Exception as e:
        error_msg = f"Error en tarea de prueba de conexiones: {str(e)}"
        logger.error(error_msg)
        
        return {
            'success': False,
            'error': error_msg,
            'timestamp': timezone.now().isoformat()
        }


@shared_task(bind=True, name='tiendanube_adminet.cleanup_old_logs')
def cleanup_old_logs_task(self, days: int = 30) -> Dict[str, Any]:
    """
    Tarea para limpiar logs antiguos.
    
    Args:
        days: Número de días a mantener
        
    Returns:
        Dict con el resultado de la limpieza
    """
    try:
        logger.info(f"Iniciando limpieza de logs antiguos (mantener {days} días)")
        
        # Calcular fecha límite
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        
        # Contar logs a eliminar
        logs_to_delete = SyncLog.objects.filter(started_at__lt=cutoff_date).count()
        
        # Eliminar logs antiguos
        deleted_count, _ = SyncLog.objects.filter(started_at__lt=cutoff_date).delete()
        
        result = {
            'success': True,
            'deleted_count': deleted_count,
            'logs_to_delete': logs_to_delete,
            'cutoff_date': cutoff_date.isoformat(),
            'timestamp': timezone.now().isoformat()
        }
        
        logger.info(f"Limpieza de logs completada: {deleted_count} logs eliminados")
        
        return result
        
    except Exception as e:
        error_msg = f"Error en tarea de limpieza de logs: {str(e)}"
        logger.error(error_msg)
        
        return {
            'success': False,
            'error': error_msg,
            'timestamp': timezone.now().isoformat()
        }


@shared_task(bind=True, name='tiendanube_adminet.full_sync')
def full_sync_task(self) -> Dict[str, Any]:
    """
    Tarea para sincronización completa (desde ambas plataformas).
    
    Returns:
        Dict con el resultado de la sincronización completa
    """
    try:
        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        if tiendanube_sync_disabled_reason(tiendanube_config):
            return _sync_disabled_response(tiendanube_config)
        logger.info("Iniciando sincronización completa")
        
        # Crear servicio de sincronización
        sync_service = TiendanubeAdministraNETSyncService()
        
        # Sincronizar desde Tiendanube
        tiendanube_result = sync_service.sync_customers_from_tiendanube()
        tiendanube_success = tiendanube_result.get('successful', 0)
        tiendanube_failed = tiendanube_result.get('failed', 0)
        
        adminet_result = sync_service.sync_customers_from_adminet()
        adminet_success = adminet_result.get('successful', 0)
        adminet_failed = adminet_result.get('failed', 0)
        
        # Sincronizar mapeos pendientes
        pending_result = sync_pending_mappings_task.delay()
        pending_data = pending_result.get(timeout=300)  # 5 minutos timeout
        
        # Calcular totales
        total_success = tiendanube_success + adminet_success + pending_data.get('success_count', 0)
        total_failed = tiendanube_failed + adminet_failed + pending_data.get('failed_count', 0)
        
        result = {
            'success': True,
            'tiendanube': {
                'success_count': tiendanube_success,
                'failed_count': tiendanube_failed
            },
            'adminet': {
                'success_count': adminet_success,
                'failed_count': adminet_failed
            },
            'pending': pending_data,
            'total_success': total_success,
            'total_failed': total_failed,
            'total_processed': total_success + total_failed,
            'timestamp': timezone.now().isoformat()
        }
        
        logger.info(f"Sincronización completa finalizada: {total_success} exitosos, {total_failed} fallidos")
        
        return result
        
    except Exception as e:
        error_msg = f"Error en tarea de sincronización completa: {str(e)}"
        logger.error(error_msg)
        
        return {
            'success': False,
            'error': error_msg,
            'timestamp': timezone.now().isoformat()
        } 

@shared_task(bind=True, name='tiendanube_administranet.tasks.sync_tasks.auto_sync_task')
def auto_sync_task(self) -> Dict[str, Any]:
    """
    Tarea de sincronización automática basada en configuración.
    Lee TiendanubeConfig.auto_sync y sync_interval para determinar
    qué y cuándo sincronizar.
    
    Returns:
        Dict con el resultado de la sincronización automática
    """
    try:
        logger.info("🤖 Iniciando sincronización automática programada")
        
        # Obtener configuración activa
        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        adminet_config = AdministraNETConfig.objects.filter(is_active=True).first()

        auto_disabled = tiendanube_auto_sync_disabled_reason(tiendanube_config)
        if auto_disabled:
            logger.info("%s", auto_disabled)
            return {
                'success': False,
                'message': auto_disabled,
                'skipped': True,
            }

        if not adminet_config:
            logger.warning("No hay configuración de AdministraNET activa. Saltando sincronización.")
            return {
                'success': False,
                'message': 'No active AdministraNET configuration',
                'skipped': True
            }
        
        # Crear servicio de sincronización
        sync_service = TiendanubeAdministraNETSyncService(tiendanube_config, adminet_config)
        
        results = {}
        total_success = 0
        total_failed = 0
        total_processed = 0
        
        # Sincronizar según configuración
        if tiendanube_config.sync_customers:
            logger.info("📊 Sincronizando clientes...")
            customer_result = sync_service.sync_customers_from_tiendanube()
            results['customers'] = customer_result
            total_success += customer_result.get('successful', 0)
            total_failed += customer_result.get('failed', 0)
            total_processed += customer_result.get('total_processed', 0)
        
        if tiendanube_config.sync_products:
            logger.info("📦 Sincronizando productos...")
            product_result = sync_service.sync_products_from_tiendanube()
            results['products'] = product_result
            total_success += product_result.get('successful', 0)
            total_failed += product_result.get('failed', 0)
            total_processed += product_result.get('total_processed', 0)
        
        if tiendanube_config.sync_orders:
            logger.info("🛒 Sincronizando pedidos...")
            order_result = sync_service.sync_orders_from_tiendanube()
            results['orders'] = order_result
            total_success += order_result.get('successful', 0)
            total_failed += order_result.get('failed', 0)
            total_processed += order_result.get('total_processed', 0)
        
        # Actualizar last_sync en configuración
        tiendanube_config.last_sync = timezone.now()
        tiendanube_config.save(update_fields=['last_sync'])
        
        result = {
            'success': True,
            'message': f'Auto sync completed: {total_success} successful, {total_failed} failed',
            'total_processed': total_processed,
            'total_success': total_success,
            'total_failed': total_failed,
            'results': results,
            'timestamp': timezone.now().isoformat()
        }
        
        logger.info(f"✅ Sincronización automática completada: {total_success} exitosos, {total_failed} fallidos")
        
        return result
        
    except Exception as e:
        error_msg = f"Error en tarea de sincronización automática: {str(e)}"
        logger.error(error_msg)
        logger.exception(e)
        
        return {
            'success': False,
            'error': error_msg,
            'timestamp': timezone.now().isoformat()
        }
