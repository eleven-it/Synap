from celery import shared_task
from .models import TiendaNubeConfig
from .services import TiendaNubeService
from django.utils import timezone
import logging
from tiendanube.models import TiendaNubeProductMapping
from inventory.models import Product

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
    service = TiendaNubeService(config)
    # Sincronizar productos pendientes de actualización
    pendientes = TiendaNubeProductMapping.objects.filter(sync_status='pending', sync_enabled=True)
    prod_update_ok = 0
    prod_update_fail = 0
    for mapping in pendientes:
        # Si el mapping existe pero el producto no tiene tiendanube_id, saltar
        if not mapping.product.tiendanube_id:
            continue
        ok, msg = service.sync_product_update(mapping.product)
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