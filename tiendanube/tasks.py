from celery import shared_task
from .models import TiendaNubeConfig, TiendaNubeSyncLog
# from .services import TiendaNubeService  # REMOVIDO: Este import causaba error en Celery
from django.utils import timezone
import logging
from tiendanube.models import TiendaNubeProductMapping
from inventory.models import Product
# from tiendanube.models_adminet import TiendaNubeCondVentaMap, TiendaNubeAdminetConfig  # REMOVIDO: módulo no existe
from tiendanube.services.connection_service import MySQLConnectionService

logger = logging.getLogger(__name__)

def get_tiendanube_service(config=None):
    """
    Obtiene una instancia de TiendaNubeService
    Import dinámico para evitar errores de importación circular
    """
    if config is None:
        config = TiendaNubeConfig.objects.first()
    from .services_main import TiendaNubeService
    return TiendaNubeService(config)

@shared_task
def sync_tiendanube_periodic():
    config = TiendaNubeConfig.objects.first()
    if not config or not config.auto_sync:
        logging.info('[Celery] Sincronización TiendaNube: No hay configuración activa o auto_sync deshabilitado.')
        return 'No config or auto_sync disabled'
    now = timezone.now()
    if config.last_sync:
        elapsed = (now - config.last_sync).total_seconds() / 60.0
        if elapsed < config.sync_interval:
            logging.info(f'[Celery] Sincronización TiendaNube: Esperando intervalo. Última sync hace {elapsed:.1f} min, intervalo requerido: {config.sync_interval} min.')
            return f'Waiting interval ({elapsed:.1f}/{config.sync_interval} min)'
    service = get_tiendanube_service(config)
    # Sincronizar productos pendientes de actualización
    pendientes = TiendaNubeProductMapping.objects.filter(sync_status='pending', sync_enabled=True)
    prod_update_ok = 0
    prod_update_fail = 0
    for mapping in pendientes:
        # Si el mapping existe pero el producto no tiene tiendanube_id, saltar
        if not mapping.product.tiendanube_id:
            continue
        ok = service.sync_product_update(mapping.product)
        if ok:
            prod_update_ok += 1
        else:
            prod_update_fail += 1
    # Crear mappings faltantes para productos con tiendanube_id pero sin mapping
    productos_sin_mapping = Product.objects.filter(tiendanube_id__isnull=False).exclude(id__in=pendientes.values_list('product_id', flat=True))
    for producto in productos_sin_mapping:
        TiendaNubeProductMapping.objects.get_or_create(
            product=producto,
            defaults={
                'tiendanube_id': producto.tiendanube_id,
                'tiendanube_handle': producto.handle,
                'sync_status': 'pending',
                'sync_enabled': True
            }
        )
    # Sincronizar productos nuevos (no mapeados)
    prod_ok, prod_fail = service.sync_products_from_tiendanube()
    stock_ok, stock_fail = service.sync_stock_to_tiendanube()
    config.last_sync = now
    config.save(update_fields=["last_sync"])
    msg = f'[Celery] Sincronización TiendaNube: Productos nuevos OK={prod_ok}, FAIL={prod_fail} | Actualizados OK={prod_update_ok}, FAIL={prod_update_fail} | Stock OK={stock_ok}, FAIL={stock_fail}'
    logging.info(msg)
    return msg

@shared_task
def sync_products_task():
    """Tarea para sincronizar productos con Tiendanube."""
    try:
        config = TiendaNubeConfig.objects.filter(auto_sync=True, sync_products=True).first()
        if not config:
            logger.info("No hay configuración activa para sincronización automática de productos")
            return
        
        service = get_tiendanube_service(config)
        success_count, failed_count = service.sync_products_from_tiendanube()
        
        logger.info(f"Sincronización automática de productos completada. Exitosos: {success_count}, Fallidos: {failed_count}")
        
        return {
            'success_count': success_count,
            'failed_count': failed_count,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error en sincronización automática de productos: {str(e)}")
        raise

@shared_task
def sync_customers_task():
    """Tarea para sincronizar clientes con Tiendanube."""
    try:
        config = TiendaNubeConfig.objects.filter(auto_sync=True, sync_customers=True).first()
        if not config:
            logger.info("No hay configuración activa para sincronización automática de clientes")
            return
        
        service = get_tiendanube_service(config)
        success_count, failed_count = service.sync_customers_from_tiendanube()
        
        logger.info(f"Sincronización automática de clientes completada. Exitosos: {success_count}, Fallidos: {failed_count}")
        
        return {
            'success_count': success_count,
            'failed_count': failed_count,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error en sincronización automática de clientes: {str(e)}")
        raise

@shared_task
def sync_orders_task():
    """Tarea para sincronizar pedidos con Tiendanube."""
    try:
        config = TiendaNubeConfig.objects.filter(auto_sync=True, sync_orders=True).first()
        if not config:
            logger.info("No hay configuración activa para sincronización automática de pedidos")
            return
        
        service = get_tiendanube_service(config)
        success_count, failed_count = service.sync_orders_from_tiendanube()
        
        logger.info(f"Sincronización automática de pedidos completada. Exitosos: {success_count}, Fallidos: {failed_count}")
        
        return {
            'success_count': success_count,
            'failed_count': failed_count,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error en sincronización automática de pedidos: {str(e)}")
        raise

@shared_task
def sync_stock_task():
    """Tarea para sincronizar stock con Tiendanube."""
    try:
        config = TiendaNubeConfig.objects.filter(auto_sync=True, sync_stock=True).first()
        if not config:
            logger.info("No hay configuración activa para sincronización automática de stock")
            return
        
        service = get_tiendanube_service(config)
        success_count, failed_count = service.sync_stock_to_tiendanube()
        
        logger.info(f"Sincronización automática de stock completada. Exitosos: {success_count}, Fallidos: {failed_count}")
        
        return {
            'success_count': success_count,
            'failed_count': failed_count,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error en sincronización automática de stock: {str(e)}")
        raise

@shared_task
def check_restock_task():
    """Tarea para verificar y ejecutar reabastecimiento automático."""
    try:
        config = TiendaNubeConfig.objects.filter(auto_sync=True, auto_restock=True).first()
        if not config:
            logger.info("No hay configuración activa para reabastecimiento automático")
            return
        
        service = get_tiendanube_service(config)
        success_count, failed_count = service.check_and_restock_products()
        
        logger.info(f"Verificación de reabastecimiento completada. Exitosos: {success_count}, Fallidos: {failed_count}")
        
        return {
            'success_count': success_count,
            'failed_count': failed_count,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error en verificación de reabastecimiento: {str(e)}")
        raise

@shared_task
def full_sync_task():
    """Tarea para sincronización completa con Tiendanube."""
    try:
        config = TiendaNubeConfig.objects.filter(auto_sync=True).first()
        if not config:
            logger.info("No hay configuración activa para sincronización automática")
            return
        
        service = get_tiendanube_service(config)
        results = {}
        
        # Sincronizar productos
        if config.sync_products:
            success_count, failed_count = service.sync_products_from_tiendanube()
            results['products'] = {'success': success_count, 'failed': failed_count}
        
        # Sincronizar clientes
        if config.sync_customers:
            success_count, failed_count = service.sync_customers_from_tiendanube()
            results['customers'] = {'success': success_count, 'failed': failed_count}
        
        # Sincronizar pedidos
        if config.sync_orders:
            success_count, failed_count = service.sync_orders_from_tiendanube()
            results['orders'] = {'success': success_count, 'failed': failed_count}
        
        # Sincronizar stock
        if config.sync_stock:
            success_count, failed_count = service.sync_stock_to_tiendanube()
            results['stock'] = {'success': success_count, 'failed': failed_count}
        
        # Verificar reabastecimiento
        if config.auto_restock:
            success_count, failed_count = service.check_and_restock_products()
            results['restock'] = {'success': success_count, 'failed': failed_count}
        
        logger.info(f"Sincronización completa completada: {results}")
        
        return {
            'results': results,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error en sincronización completa: {str(e)}")
        raise

@shared_task
def cleanup_old_logs_task():
    """Tarea para limpiar logs antiguos."""
    try:
        # Eliminar logs de más de 90 días
        cutoff_date = timezone.now() - timezone.timedelta(days=90)
        deleted_count = TiendaNubeSyncLog.objects.filter(started_at__lt=cutoff_date).delete()[0]
        
        logger.info(f"Limpieza de logs completada. Eliminados: {deleted_count}")
        
        return {
            'deleted_count': deleted_count,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error en limpieza de logs: {str(e)}")
        raise

@shared_task
def test_connection_task():
    """Tarea para probar conexión con Tiendanube."""
    try:
        config = TiendaNubeConfig.objects.first()
        if not config:
            logger.warning("No hay configuración de Tiendanube para probar conexión")
            return
        
        service = get_tiendanube_service(config)
        success, message = service.test_connection()
        
        if success:
            logger.info(f"Prueba de conexión exitosa: {message}")
        else:
            logger.error(f"Prueba de conexión fallida: {message}")
        
        return {
            'success': success,
            'message': message,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error en prueba de conexión: {str(e)}")
        raise 

# La sincronización del mapeo de condiciones de venta a MySQL ha sido eliminada.
# El mapeo solo se mantiene en la base de datos de la app tiendanube (PostgreSQL).

# Puedes consultar el mapeo así:
# from tiendanube.models_adminet import TiendaNubeCondVentaMap
# mapeo = TiendaNubeCondVentaMap.objects.filter(payment_method=metodo_pago, activo=True).first()
# if mapeo:
#     adminet_codigo = mapeo.adminet_codigo
#     # Usar adminet_codigo en la integración con MySQL 