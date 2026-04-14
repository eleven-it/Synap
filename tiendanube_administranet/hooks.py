"""
Hooks para el módulo tiendanube_administranet
Implementa los hooks definidos en el registro de módulos para integración con el sistema
"""

import logging
from typing import Dict, Any, Optional
from django.utils import timezone
from .models import SyncLog, CustomerMapping, ProductMapping, OrderMapping

logger = logging.getLogger(__name__)


def pre_customer_sync(customer_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """
    Hook que se ejecuta antes de sincronizar un cliente
    
    Args:
        customer_data: Datos del cliente a sincronizar
        **kwargs: Argumentos adicionales
        
    Returns:
        Dict con datos procesados del cliente
    """
    try:
        logger.info(f"Pre-sync hook ejecutado para cliente: {customer_data.get('email', 'N/A')}")
        
        # Aquí se pueden agregar validaciones, transformaciones o lógica de negocio
        # antes de la sincronización
        
        # Ejemplo: Validar que el email esté presente
        if not customer_data.get('email'):
            logger.warning("Cliente sin email, agregando email por defecto")
            customer_data['email'] = f"cliente_{timezone.now().strftime('%Y%m%d_%H%M%S')}@example.com"
        
        # Ejemplo: Normalizar nombre
        if customer_data.get('first_name'):
            customer_data['first_name'] = customer_data['first_name'].strip().title()
        
        if customer_data.get('last_name'):
            customer_data['last_name'] = customer_data['last_name'].strip().title()
        
        return customer_data
        
    except Exception as e:
        logger.error(f"Error en pre_customer_sync hook: {str(e)}")
        return customer_data


def post_customer_sync(customer_mapping: CustomerMapping, sync_result: Dict[str, Any], **kwargs) -> None:
    """
    Hook que se ejecuta después de sincronizar un cliente
    
    Args:
        customer_mapping: Instancia del mapeo de cliente
        sync_result: Resultado de la sincronización
        **kwargs: Argumentos adicionales
    """
    try:
        logger.info(f"Post-sync hook ejecutado para cliente: {customer_mapping.tiendanube_email}")
        
        # Ejemplo: Actualizar estadísticas
        if sync_result.get('success'):
            customer_mapping.last_synced = timezone.now()
            customer_mapping.sync_status = 'synced'
            customer_mapping.save(update_fields=['last_synced', 'sync_status'])
            
            # Crear log de sincronización exitosa
            SyncLog.objects.create(
                sync_type='customer_sync',
                status='success',
                platform='both',
                mapping=customer_mapping,
                message=f"Cliente sincronizado exitosamente: {customer_mapping.tiendanube_email}",
                started_at=timezone.now()
            )
        
    except Exception as e:
        logger.error(f"Error en post_customer_sync hook: {str(e)}")


def pre_product_sync(product_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """
    Hook que se ejecuta antes de sincronizar un producto
    
    Args:
        product_data: Datos del producto a sincronizar
        **kwargs: Argumentos adicionales
        
    Returns:
        Dict con datos procesados del producto
    """
    try:
        logger.info(f"Pre-sync hook ejecutado para producto: {product_data.get('name', 'N/A')}")
        
        # Ejemplo: Validar precio
        if product_data.get('price') and float(product_data['price']) < 0:
            logger.warning(f"Precio negativo detectado para producto {product_data.get('name')}, estableciendo a 0")
            product_data['price'] = 0
        
        # Ejemplo: Normalizar nombre
        if product_data.get('name'):
            product_data['name'] = product_data['name'].strip()
        
        # Ejemplo: Validar stock
        if product_data.get('stock') and int(product_data['stock']) < 0:
            logger.warning(f"Stock negativo detectado para producto {product_data.get('name')}, estableciendo a 0")
            product_data['stock'] = 0
        
        return product_data
        
    except Exception as e:
        logger.error(f"Error en pre_product_sync hook: {str(e)}")
        return product_data


def post_product_sync(product_mapping: ProductMapping, sync_result: Dict[str, Any], **kwargs) -> None:
    """
    Hook que se ejecuta después de sincronizar un producto
    
    Args:
        product_mapping: Instancia del mapeo de producto
        sync_result: Resultado de la sincronización
        **kwargs: Argumentos adicionales
    """
    try:
        logger.info(f"Post-sync hook ejecutado para producto: {product_mapping.tiendanube_name}")
        
        if sync_result.get('success'):
            product_mapping.last_synced = timezone.now()
            product_mapping.sync_status = 'synced'
            product_mapping.save(update_fields=['last_synced', 'sync_status'])
            
            # Crear log de sincronización exitosa
            SyncLog.objects.create(
                sync_type='product_sync',
                status='success',
                platform='both',
                mapping=product_mapping,
                message=f"Producto sincronizado exitosamente: {product_mapping.tiendanube_name}",
                started_at=timezone.now()
            )
        
    except Exception as e:
        logger.error(f"Error en post_product_sync hook: {str(e)}")


def pre_order_sync(order_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """
    Hook que se ejecuta antes de sincronizar una orden
    
    Args:
        order_data: Datos de la orden a sincronizar
        **kwargs: Argumentos adicionales
        
    Returns:
        Dict con datos procesados de la orden
    """
    try:
        logger.info(f"Pre-sync hook ejecutado para orden: {order_data.get('number', 'N/A')}")
        
        # Ejemplo: Validar total
        if order_data.get('total') and float(order_data['total']) < 0:
            logger.warning(f"Total negativo detectado para orden {order_data.get('number')}, estableciendo a 0")
            order_data['total'] = 0
        
        # Ejemplo: Normalizar número de orden
        if order_data.get('number'):
            order_data['number'] = order_data['number'].strip()
        
        # Ejemplo: Validar estado
        valid_statuses = ['pending', 'paid', 'shipped', 'delivered', 'cancelled']
        if order_data.get('status') and order_data['status'] not in valid_statuses:
            logger.warning(f"Estado inválido detectado para orden {order_data.get('number')}, estableciendo a 'pending'")
            order_data['status'] = 'pending'
        
        return order_data
        
    except Exception as e:
        logger.error(f"Error en pre_order_sync hook: {str(e)}")
        return order_data


def post_order_sync(order_mapping: OrderMapping, sync_result: Dict[str, Any], **kwargs) -> None:
    """
    Hook que se ejecuta después de sincronizar una orden
    
    Args:
        order_mapping: Instancia del mapeo de orden
        sync_result: Resultado de la sincronización
        **kwargs: Argumentos adicionales
    """
    try:
        logger.info(f"Post-sync hook ejecutado para orden: {order_mapping.tiendanube_order_number}")
        
        if sync_result.get('success'):
            order_mapping.last_synced = timezone.now()
            order_mapping.sync_status = 'synced'
            order_mapping.save(update_fields=['last_synced', 'sync_status'])
            
            # Crear log de sincronización exitosa
            SyncLog.objects.create(
                sync_type='order_sync',
                status='success',
                platform='both',
                mapping=order_mapping,
                message=f"Orden sincronizada exitosamente: {order_mapping.tiendanube_order_number}",
                started_at=timezone.now()
            )
        
    except Exception as e:
        logger.error(f"Error en post_order_sync hook: {str(e)}")


def sync_error(error_data: Dict[str, Any], **kwargs) -> None:
    """
    Hook que se ejecuta cuando ocurre un error en la sincronización
    
    Args:
        error_data: Datos del error
        **kwargs: Argumentos adicionales
    """
    try:
        logger.error(f"Sync error hook ejecutado: {error_data.get('message', 'Error desconocido')}")
        
        # Crear log de error
        SyncLog.objects.create(
            sync_type=error_data.get('sync_type', 'unknown'),
            status='error',
            platform=error_data.get('platform', 'unknown'),
            message=error_data.get('message', 'Error desconocido en sincronización'),
            error_details=error_data.get('error_details', ''),
            started_at=timezone.now()
        )
        
        # Aquí se pueden agregar notificaciones, alertas, etc.
        
    except Exception as e:
        logger.error(f"Error en sync_error hook: {str(e)}")


def sync_completed(sync_summary: Dict[str, Any], **kwargs) -> None:
    """
    Hook que se ejecuta cuando se completa una sincronización
    
    Args:
        sync_summary: Resumen de la sincronización
        **kwargs: Argumentos adicionales
    """
    try:
        logger.info(f"Sync completed hook ejecutado: {sync_summary.get('total_items', 0)} items procesados")
        
        # Crear log de resumen
        SyncLog.objects.create(
            sync_type='sync_summary',
            status='success',
            platform='both',
            message=f"Sincronización completada: {sync_summary.get('total_items', 0)} items, "
                    f"{sync_summary.get('success_count', 0)} exitosos, "
                    f"{sync_summary.get('error_count', 0)} errores",
            started_at=timezone.now()
        )
        
        # Aquí se pueden agregar notificaciones, reportes, etc.
        
    except Exception as e:
        logger.error(f"Error en sync_completed hook: {str(e)}")


# Configuración de hooks
HOOKS = {
    'tiendanube_administranet.pre_customer_sync': {
        'callback': pre_customer_sync,
        'description': 'Hook que se ejecuta antes de sincronizar un cliente',
        'priority': 10,
        'dependencies': [],
        'metadata': {
            'category': 'tiendanube_administranet',
            'type': 'pre_sync'
        }
    },
    'tiendanube_administranet.post_customer_sync': {
        'callback': post_customer_sync,
        'description': 'Hook que se ejecuta después de sincronizar un cliente',
        'priority': 10,
        'dependencies': [],
        'metadata': {
            'category': 'tiendanube_administranet',
            'type': 'post_sync'
        }
    },
    'tiendanube_administranet.pre_product_sync': {
        'callback': pre_product_sync,
        'description': 'Hook que se ejecuta antes de sincronizar un producto',
        'priority': 10,
        'dependencies': [],
        'metadata': {
            'category': 'tiendanube_administranet',
            'type': 'pre_sync'
        }
    },
    'tiendanube_administranet.post_product_sync': {
        'callback': post_product_sync,
        'description': 'Hook que se ejecuta después de sincronizar un producto',
        'priority': 10,
        'dependencies': [],
        'metadata': {
            'category': 'tiendanube_administranet',
            'type': 'post_sync'
        }
    },
    'tiendanube_administranet.pre_order_sync': {
        'callback': pre_order_sync,
        'description': 'Hook que se ejecuta antes de sincronizar una orden',
        'priority': 10,
        'dependencies': [],
        'metadata': {
            'category': 'tiendanube_administranet',
            'type': 'pre_sync'
        }
    },
    'tiendanube_administranet.post_order_sync': {
        'callback': post_order_sync,
        'description': 'Hook que se ejecuta después de sincronizar una orden',
        'priority': 10,
        'dependencies': [],
        'metadata': {
            'category': 'tiendanube_administranet',
            'type': 'post_sync'
        }
    },
    'tiendanube_administranet.sync_error': {
        'callback': sync_error,
        'description': 'Hook que se ejecuta cuando ocurre un error en la sincronización',
        'priority': 5,  # Prioridad alta para errores
        'dependencies': [],
        'metadata': {
            'category': 'tiendanube_administranet',
            'type': 'error'
        }
    },
    'tiendanube_administranet.sync_completed': {
        'callback': sync_completed,
        'description': 'Hook que se ejecuta cuando se completa una sincronización',
        'priority': 10,
        'dependencies': [],
        'metadata': {
            'category': 'tiendanube_administranet',
            'type': 'completion'
        }
    }
} 