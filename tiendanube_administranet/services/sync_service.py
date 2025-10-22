"""
Servicio principal de sincronización entre Tiendanube y AdministraNET.
"""

import logging
from typing import Dict, List, Tuple, Optional, Any
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from .tiendanube_service import TiendanubeService
from .adminet_service import AdministraNETService
from .product_service import TiendanubeProductService
from .automatic_mapping_service import AutomaticMappingService
from ..models import (
    TiendanubeConfig, AdministraNETConfig, CustomerMapping, 
    ProductMapping, ProductVariantMapping, OrderMapping, SyncLog
)

logger = logging.getLogger(__name__)


class TiendanubeAdministraNETSyncService:
    """
    Servicio principal para sincronización bidireccional entre Tiendanube y AdministraNET.
    """
    
    def __init__(self, tiendanube_config: TiendanubeConfig, adminet_config: AdministraNETConfig):
        self.tiendanube_config = tiendanube_config
        self.adminet_config = adminet_config
        self.tiendanube_service = TiendanubeService(tiendanube_config)
        self.adminet_service = AdministraNETService(adminet_config)
        self.product_service = TiendanubeProductService(tiendanube_config)
        self.mapping_service = AutomaticMappingService(tiendanube_config, adminet_config)
    
    def map_adminet_estado_to_tiendanube(self, estado: str, anulado: str) -> Dict[str, str]:
        """
        Mapear estado de AdministraNET a estados de TiendaNube.
        
        Args:
            estado: Estado del pedido en AdministraNET
            anulado: Campo anulado ("Si" o "No")
            
        Returns:
            Dict con order_status y fulfillment_status para TiendaNube
        """
        # Si está anulado, siempre es cancelled
        if anulado == "Si":
            return {
                'order_status': 'cancelled',
                'fulfillment_status': None
            }
        
        # Mapeo según estado
        estado_map = {
            'Pendiente': {'order_status': 'open', 'fulfillment_status': 'pending'},
            'En preparación': {'order_status': 'open', 'fulfillment_status': 'pending'},
            'Preparado': {'order_status': 'open', 'fulfillment_status': 'pending'},
            'En Remito': {'order_status': 'open', 'fulfillment_status': 'in_transit'},
            'Parcial': {'order_status': 'open', 'fulfillment_status': 'in_transit'},
            'Facturado': {'order_status': 'closed', 'fulfillment_status': 'delivered'},
            'Cerrado': {'order_status': 'closed', 'fulfillment_status': 'delivered'},
        }
        
        return estado_map.get(estado, {'order_status': 'open', 'fulfillment_status': 'pending'})
    
    def sync_customers_from_tiendanube(self) -> Dict[str, Any]:
        """Sincronizar clientes desde Tiendanube hacia AdministraNET."""
        try:
            # Crear log de sincronización
            sync_log = SyncLog.objects.create(
                sync_type=SyncLog.SyncType.CUSTOMER,
                direction=SyncLog.SyncDirection.TO_ADMINET,
                status=SyncLog.Status.IN_PROGRESS,
                tiendanube_config=self.tiendanube_config,
                adminet_config=self.adminet_config
            )
            
            # Obtener clientes de Tiendanube
            tiendanube_result = self.tiendanube_service.get_customers(limit=100)
            if not tiendanube_result['success']:
                sync_log.complete_sync(False, tiendanube_result['message'])
                return tiendanube_result
            
            customers = tiendanube_result['customers']
            sync_log.total_items = len(customers)
            sync_log.save()
            
            successful_syncs = 0
            failed_syncs = 0
            
            for customer in customers:
                try:
                    # Verificar si ya existe el mapeo
                    mapping, created = CustomerMapping.objects.get_or_create(
                        tiendanube_id=customer['id'],
                        defaults={
                            'tiendanube_email': customer.get('email', ''),
                            'tiendanube_name': customer.get('name', ''),
                            'sync_status': CustomerMapping.SyncStatus.PENDING
                        }
                    )
                    
                    if created or mapping.sync_status != CustomerMapping.SyncStatus.SYNCED:
                        # Crear/actualizar en AdministraNET
                        adminet_data = {
                            'nombre': customer.get('name', ''),
                            'email': customer.get('email', ''),
                            'documento': customer.get('document', ''),
                            'telefono': customer.get('phone', ''),
                            'direccion': customer.get('address', '')
                        }
                        
                        if mapping.adminet_codigo:
                            # Actualizar cliente existente
                            result = self.adminet_service.update_customer(mapping.adminet_codigo, adminet_data)
                        else:
                            # Crear nuevo cliente
                            result = self.adminet_service.create_customer(adminet_data)
                            if result['success']:
                                mapping.adminet_codigo = result.get('customer_id')
                        
                        if result['success']:
                            mapping.sync_status = CustomerMapping.SyncStatus.SYNCED
                            mapping.last_synced = timezone.now()
                            mapping.save()
                            successful_syncs += 1
                        else:
                            mapping.sync_status = CustomerMapping.SyncStatus.ERROR
                            mapping.error_message = result['message']
                            mapping.save()
                            failed_syncs += 1
                    
                    sync_log.processed_items += 1
                    sync_log.save()
                    
                except Exception as e:
                    logger.error(f"Error syncing customer {customer.get('id')}: {e}")
                    failed_syncs += 1
                    sync_log.processed_items += 1
                    sync_log.save()
            
            # Completar sincronización
            sync_log.successful_items = successful_syncs
            sync_log.failed_items = failed_syncs
            sync_log.complete_sync(True)
            
            return {
                'success': True,
                'message': f'Sincronización completada: {successful_syncs} exitosas, {failed_syncs} fallidas',
                'sync_log_id': sync_log.id,
                'total_processed': len(customers),
                'successful': successful_syncs,
                'failed': failed_syncs
            }
            
        except Exception as e:
            logger.error(f"Error in sync_customers_from_tiendanube: {e}")
            if 'sync_log' in locals():
                sync_log.complete_sync(False, str(e))
            return {
                'success': False,
                'message': f'Error en sincronización: {str(e)}'
            }
    
    def sync_customers_from_adminet(self) -> Dict[str, Any]:
        """Sincronizar clientes desde AdministraNET hacia Tiendanube."""
        try:
            # Crear log de sincronización
            sync_log = SyncLog.objects.create(
                sync_type=SyncLog.SyncType.CUSTOMER,
                direction=SyncLog.SyncDirection.FROM_ADMINET,
                status=SyncLog.Status.IN_PROGRESS,
                tiendanube_config=self.tiendanube_config,
                adminet_config=self.adminet_config
            )
            
            # Obtener clientes de AdministraNET
            adminet_result = self.adminet_service.get_customers(limit=100)
            if not adminet_result['success']:
                sync_log.complete_sync(False, adminet_result['message'])
                return adminet_result
            
            customers = adminet_result['results']
            sync_log.total_items = len(customers)
            sync_log.save()
            
            successful_syncs = 0
            failed_syncs = 0
            
            for customer in customers:
                try:
                    # Verificar si ya existe el mapeo
                    mapping, created = CustomerMapping.objects.get_or_create(
                        adminet_codigo=customer['codigo'],
                        defaults={
                            'adminet_nombre': customer.get('nombre', ''),
                            'sync_status': CustomerMapping.SyncStatus.PENDING
                        }
                    )
                    
                    if created or mapping.sync_status != CustomerMapping.SyncStatus.SYNCED:
                        # Crear/actualizar en Tiendanube
                        tiendanube_data = {
                            'name': customer.get('nombre', ''),
                            'email': customer.get('email', ''),
                            'document': customer.get('documento', ''),
                            'phone': customer.get('telefono', ''),
                            'address': customer.get('direccion', '')
                        }
                        
                        if mapping.tiendanube_id:
                            # Actualizar cliente existente
                            result = self.tiendanube_service.update_customer(mapping.tiendanube_id, tiendanube_data)
                        else:
                            # Crear nuevo cliente
                            result = self.tiendanube_service.create_customer(tiendanube_data)
                            if result['success']:
                                mapping.tiendanube_id = result.get('customer_id')
                        
                        if result['success']:
                            mapping.sync_status = CustomerMapping.SyncStatus.SYNCED
                            mapping.last_synced = timezone.now()
                            mapping.save()
                            successful_syncs += 1
                        else:
                            mapping.sync_status = CustomerMapping.SyncStatus.ERROR
                            mapping.error_message = result['message']
                            mapping.save()
                            failed_syncs += 1
                    
                    sync_log.processed_items += 1
                    sync_log.save()
                    
                except Exception as e:
                    logger.error(f"Error syncing customer {customer.get('codigo')}: {e}")
                    failed_syncs += 1
                    sync_log.processed_items += 1
                    sync_log.save()
            
            # Completar sincronización
            sync_log.successful_items = successful_syncs
            sync_log.failed_items = failed_syncs
            sync_log.complete_sync(True)
            
            return {
                'success': True,
                'message': f'Sincronización completada: {successful_syncs} exitosas, {failed_syncs} fallidas',
                'sync_log_id': sync_log.id,
                'total_processed': len(customers),
                'successful': successful_syncs,
                'failed': failed_syncs
            }
            
        except Exception as e:
            logger.error(f"Error in sync_customers_from_adminet: {e}")
            if 'sync_log' in locals():
                sync_log.complete_sync(False, str(e))
            return {
                'success': False,
                'message': f'Error en sincronización: {str(e)}'
            }

    # ============================================================================
    # PRODUCTOS
    # ============================================================================

    def sync_products_from_tiendanube(self) -> Dict[str, Any]:
        """Sincronizar productos desde Tiendanube hacia AdministraNET."""
        try:
            # Crear log de sincronización
            sync_log = SyncLog.objects.create(
                sync_type=SyncLog.SyncType.PRODUCT,
                direction=SyncLog.SyncDirection.TO_ADMINET,
                status=SyncLog.Status.IN_PROGRESS,
                tiendanube_config=self.tiendanube_config,
                adminet_config=self.adminet_config
            )
            
            # Obtener productos de Tiendanube
            tiendanube_result = self.product_service.get_products(limit=100)
            if not tiendanube_result['success']:
                sync_log.complete_sync(False, tiendanube_result['message'])
                return tiendanube_result
            
            products = tiendanube_result['products']
            sync_log.total_items = len(products)
            sync_log.save()
            
            successful_syncs = 0
            failed_syncs = 0
            
            for product in products:
                try:
                    # Verificar si ya existe el mapeo
                    mapping, created = ProductMapping.objects.get_or_create(
                        tiendanube_id=product['id'],
                        defaults={
                            'tiendanube_name': product.get('name', ''),
                            'tiendanube_sku': product.get('sku', ''),
                            'tiendanube_price': product.get('price', 0),
                            'tiendanube_stock': product.get('stock', 0),
                            'sync_status': ProductMapping.SyncStatus.PENDING
                        }
                    )
                    
                    if created or mapping.sync_status != ProductMapping.SyncStatus.SYNCED:
                        # Mapear datos de Tiendanube a AdministraNET
                        adminet_data = self.mapping_service.map_tiendanube_to_adminet_product(product)
                        
                        if mapping.adminet_id:
                            # Actualizar producto existente
                            result = self.adminet_service.update_product(mapping.adminet_id, adminet_data)
                        else:
                            # Crear nuevo producto
                            result = self.adminet_service.create_product(adminet_data)
                            if result['success']:
                                mapping.adminet_id = result.get('product_id')
                        
                        if result['success']:
                            # Actualizar mapeo con datos de Tiendanube
                            self.mapping_service.update_product_mapping_from_tiendanube(mapping, product)
                            mapping.sync_status = ProductMapping.SyncStatus.SYNCED
                            mapping.last_synced = timezone.now()
                            mapping.save()
                            successful_syncs += 1
                        else:
                            mapping.sync_status = ProductMapping.SyncStatus.ERROR
                            mapping.error_message = result['message']
                            mapping.save()
                            failed_syncs += 1
                    
                    sync_log.processed_items += 1
                    sync_log.save()
                    
                except Exception as e:
                    logger.error(f"Error syncing product {product.get('id')}: {e}")
                    failed_syncs += 1
                    sync_log.processed_items += 1
                    sync_log.save()
            
            # Completar sincronización
            sync_log.successful_items = successful_syncs
            sync_log.failed_items = failed_syncs
            sync_log.complete_sync(True)
            
            return {
                'success': True,
                'message': f'Sincronización completada: {successful_syncs} exitosas, {failed_syncs} fallidas',
                'sync_log_id': sync_log.id,
                'total_processed': len(products),
                'successful': successful_syncs,
                'failed': failed_syncs
            }
            
        except Exception as e:
            logger.error(f"Error in sync_products_from_tiendanube: {e}")
            if 'sync_log' in locals():
                sync_log.complete_sync(False, str(e))
            return {
                'success': False,
                'message': f'Error en sincronización: {str(e)}'
            }

    def sync_products_from_adminet(self) -> Dict[str, Any]:
        """Sincronizar productos desde AdministraNET hacia Tiendanube."""
        try:
            # Crear log de sincronización
            sync_log = SyncLog.objects.create(
                sync_type=SyncLog.SyncType.PRODUCT,
                direction=SyncLog.SyncDirection.FROM_ADMINET,
                status=SyncLog.Status.IN_PROGRESS,
                tiendanube_config=self.tiendanube_config,
                adminet_config=self.adminet_config
            )
            
            # Obtener depósito configurado
            deposito_id = self.adminet_config.deposito_tiendanube_id
            
            # Obtener productos de AdministraNET con stock del depósito específico
            if deposito_id:
                logger.info(f"Sincronizando productos desde depósito {deposito_id}")
                adminet_result = self.adminet_service.get_products_with_stock_by_deposito(
                    deposito_id=deposito_id,
                    limit=100, 
                    ecommerce='Si',
                    disponible_vta='Si'
                )
            else:
                logger.warning("No hay depósito configurado, usando stock general")
                adminet_result = self.adminet_service.get_products(
                    limit=100, 
                    ecommerce='Si',
                    disponible_vta='Si'
                )
            
            if not adminet_result['success']:
                sync_log.complete_sync(False, adminet_result['message'])
                return adminet_result
            
            products = adminet_result['results']
            sync_log.total_items = len(products)
            sync_log.save()
            
            successful_syncs = 0
            failed_syncs = 0
            
            for product in products:
                try:
                    # Verificar si ya existe el mapeo
                    mapping, created = ProductMapping.objects.get_or_create(
                        adminet_id=product['IDArt'],
                        defaults={
                            'adminet_nombre': product.get('NombreArticulo', ''),
                            'adminet_codigo_articulo': product.get('CodigoArticuloT', ''),
                            'sync_status': ProductMapping.SyncStatus.PENDING
                        }
                    )
                    
                    if created or mapping.sync_status != ProductMapping.SyncStatus.SYNCED:
                        # Actualizar mapeo con datos de AdministraNET PRIMERO
                        self.mapping_service.update_product_mapping_from_adminet(mapping, product)
                        
                        # Mapear datos de AdministraNET a Tiendanube (pasando deposito_id)
                        tiendanube_data = self.mapping_service.map_adminet_to_tiendanube_product(
                            product, 
                            deposito_id=deposito_id
                        )
                        
                        if mapping.tiendanube_id:
                            # Obtener el producto existente para verificar variantes
                            existing_product = self.product_service.get_product(mapping.tiendanube_id)
                            if existing_product['success']:
                                product_data = existing_product['product']
                                variants = product_data.get('variants', [])
                                
                                if variants:
                                    # Actualizar la primera variante (asumiendo una variante por producto)
                                    variant = variants[0]
                                    variant_id = variant.get('id')
                                    
                                    # Preparar datos de la variante
                                    variant_data = {
                                        'sku': tiendanube_data.get('variants', [{}])[0].get('sku'),
                                        'price': tiendanube_data.get('variants', [{}])[0].get('price'),
                                        'stock': tiendanube_data.get('variants', [{}])[0].get('stock'),
                                        'stock_management': True
                                    }
                                    
                                    # Actualizar variante usando el método correcto
                                    result = self.product_service.update_variant(
                                        mapping.tiendanube_id, 
                                        variant_id, 
                                        variant_data
                                    )
                                else:
                                    # No hay variantes, crear una nueva
                                    variant_data = tiendanube_data.get('variants', [{}])[0]
                                    result = self.product_service.create_variant(
                                        mapping.tiendanube_id, 
                                        variant_data
                                    )
                            else:
                                result = existing_product
                        else:
                            # Crear nuevo producto
                            result = self.product_service.create_product(tiendanube_data)
                            if result['success']:
                                # El ID del producto está en result['product']['id']
                                product = result.get('product', {})
                                mapping.tiendanube_id = product.get('id')
                        
                        if result['success']:
                            mapping.sync_status = ProductMapping.SyncStatus.SYNCED
                            mapping.last_synced = timezone.now()
                            mapping.save()
                            successful_syncs += 1
                        else:
                            mapping.sync_status = ProductMapping.SyncStatus.ERROR
                            mapping.error_message = result['message']
                            mapping.save()
                            failed_syncs += 1
                    
                    sync_log.processed_items += 1
                    sync_log.save()
                    
                except Exception as e:
                    logger.error(f"Error syncing product {product.get('IDArt')}: {e}")
                    failed_syncs += 1
                    sync_log.processed_items += 1
                    sync_log.save()
            
            # Completar sincronización
            sync_log.successful_items = successful_syncs
            sync_log.failed_items = failed_syncs
            sync_log.complete_sync(True)
            
            return {
                'success': True,
                'message': f'Sincronización completada: {successful_syncs} exitosas, {failed_syncs} fallidas',
                'sync_log_id': sync_log.id,
                'total_processed': len(products),
                'successful': successful_syncs,
                'failed': failed_syncs
            }
            
        except Exception as e:
            logger.error(f"Error in sync_products_from_adminet: {e}")
            if 'sync_log' in locals():
                sync_log.complete_sync(False, str(e))
            return {
                'success': False,
                'message': f'Error en sincronización: {str(e)}'
            }

    def sync_product_variants_from_tiendanube(self, product_mapping: ProductMapping) -> Dict[str, Any]:
        """Sincronizar variantes de un producto desde Tiendanube hacia AdministraNET."""
        try:
            if not product_mapping.tiendanube_id:
                return {
                    'success': False,
                    'message': 'El producto no tiene ID de Tiendanube'
                }
            
            # Obtener variantes de Tiendanube
            variants_result = self.product_service.get_product_variants(product_mapping.tiendanube_id)
            if not variants_result['success']:
                return variants_result
            
            variants = variants_result['variants']
            successful_syncs = 0
            failed_syncs = 0
            
            for variant in variants:
                try:
                    # Verificar si ya existe el mapeo de variante
                    variant_mapping, created = ProductVariantMapping.objects.get_or_create(
                        tiendanube_variant_id=variant['id'],
                        product_mapping=product_mapping,
                        defaults={
                            'tiendanube_name': variant.get('name', ''),
                            'tiendanube_sku': variant.get('sku', ''),
                            'tiendanube_price': variant.get('price', 0),
                            'tiendanube_stock': variant.get('stock', 0),
                            'sync_status': ProductVariantMapping.SyncStatus.PENDING
                        }
                    )
                    
                    if created or variant_mapping.sync_status != ProductVariantMapping.SyncStatus.SYNCED:
                        # Mapear datos de variante de Tiendanube a AdministraNET
                        adminet_data = self.mapping_service.map_tiendanube_to_adminet_variant(variant)
                        
                        if variant_mapping.adminet_id:
                            # Actualizar variante existente
                            result = self.adminet_service.update_product(variant_mapping.adminet_id, adminet_data)
                        else:
                            # Crear nueva variante como producto separado
                            result = self.adminet_service.create_product(adminet_data)
                            if result['success']:
                                variant_mapping.adminet_id = result.get('product_id')
                        
                        if result['success']:
                            # Actualizar mapeo de variante
                            self._update_variant_mapping_from_tiendanube(variant_mapping, variant)
                            variant_mapping.sync_status = ProductVariantMapping.SyncStatus.SYNCED
                            variant_mapping.last_synced = timezone.now()
                            variant_mapping.save()
                            successful_syncs += 1
                        else:
                            variant_mapping.sync_status = ProductVariantMapping.SyncStatus.ERROR
                            variant_mapping.error_message = result['message']
                            variant_mapping.save()
                            failed_syncs += 1
                    
                except Exception as e:
                    logger.error(f"Error syncing variant {variant.get('id')}: {e}")
                    failed_syncs += 1
            
            return {
                'success': True,
                'message': f'Sincronización de variantes completada: {successful_syncs} exitosas, {failed_syncs} fallidas',
                'total_processed': len(variants),
                'successful': successful_syncs,
                'failed': failed_syncs
            }
            
        except Exception as e:
            logger.error(f"Error in sync_product_variants_from_tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error en sincronización de variantes: {str(e)}'
            }

    # ============================================================================
    # MÉTODOS DE MAPEO (DEPRECATED - USAR AutomaticMappingService)
    # ============================================================================
    
    # Los métodos de mapeo han sido movidos al AutomaticMappingService
    # para centralizar toda la lógica de mapeo y mantener el código organizado.

    # ============================================================================
    # ÓRDENES (mantener implementación existente)
    # ============================================================================
    
    def sync_orders_from_tiendanube(self) -> Dict[str, Any]:
        """Sincronizar órdenes desde Tiendanube hacia AdministraNET."""
        try:
            # Crear log de sincronización
            sync_log = SyncLog.objects.create(
                sync_type=SyncLog.SyncType.ORDER,
                direction=SyncLog.SyncDirection.TO_ADMINET,
                status=SyncLog.Status.IN_PROGRESS,
                tiendanube_config=self.tiendanube_config,
                adminet_config=self.adminet_config
            )
            
            # Obtener órdenes de Tiendanube
            tiendanube_result = self.tiendanube_service.get_orders(limit=50)
            if not tiendanube_result['success']:
                sync_log.complete_sync(False, tiendanube_result['message'])
                return tiendanube_result
            
            orders = tiendanube_result['orders']
            sync_log.total_items = len(orders)
            sync_log.save()
            
            successful_syncs = 0
            failed_syncs = 0
            
            for order in orders:
                try:
                    # Verificar si ya existe el mapeo
                    mapping, created = OrderMapping.objects.get_or_create(
                        tiendanube_id=order['id'],
                        defaults={
                            'tiendanube_number': order.get('number', ''),
                            'tiendanube_customer_email': order.get('customer_email', ''),
                            'sync_status': OrderMapping.SyncStatus.PENDING
                        }
                    )
                    
                    if created or mapping.sync_status != OrderMapping.SyncStatus.SYNCED:
                        # Verificar si la orden debe crearse en AdministraNET
                        if not mapping.adminet_codigo:
                            # Preparar datos de la orden para AdministraNET
                            order_data_for_adminet = {
                                'id': order.get('id'),
                                'number': order.get('number'),
                                'customer': order.get('customer', {}),
                                'shipping_address': order.get('shipping_address', {}),
                                'shipping': order.get('shipping', {}),
                                'payment': order.get('payment', {}),
                                'products': order.get('products', []),
                                'subtotal': order.get('subtotal', 0),
                                'total': order.get('total', 0),
                                'discount': order.get('discount', 0),
                                'shipping_cost': order.get('shipping_cost', 0),
                                'payment_status': order.get('payment_status', ''),
                                'created_at': order.get('created_at', ''),
                                'updated_at': order.get('updated_at', ''),
                                'adminet_customer_id': mapping.adminet_codigo_cliente or 1
                            }
                            
                            # Mapear productos de TiendaNube a AdministraNET
                            for product in order_data_for_adminet['products']:
                                # Buscar mapeo del producto
                                product_mapping = ProductMapping.objects.filter(
                                    tiendanube_id=product.get('product_id')
                                ).first()
                                
                                if product_mapping and product_mapping.adminet_id:
                                    product['adminet_product_id'] = product_mapping.adminet_id
                                else:
                                    product['adminet_product_id'] = 0  # No mapeado
                                    logger.warning(f"Producto {product.get('product_id')} no está mapeado")
                            
                            # Crear orden en AdministraNET
                            result = self.adminet_service.create_order_from_tiendanube(
                                order_data_for_adminet,
                                deposito_id=self.adminet_config.deposito_tiendanube_id or 1,
                                user_id=1,  # Usuario del sistema
                                sucursal_id=1  # Sucursal por defecto
                            )
                            
                            if result['success']:
                                mapping.adminet_codigo = result['codigo_movimiento']
                                mapping.adminet_numero = result['nro_comprobante']
                                mapping.sync_status = OrderMapping.SyncStatus.SYNCED
                                mapping.last_synced = timezone.now()
                                mapping.save()
                                successful_syncs += 1
                                logger.info(f"Orden {order.get('number')} creada en AdministraNET: {result['nro_comprobante']}")
                            else:
                                mapping.sync_status = OrderMapping.SyncStatus.ERROR
                                mapping.error_message = result['message']
                                mapping.save()
                                failed_syncs += 1
                                logger.error(f"Error creando orden {order.get('number')}: {result['message']}")
                        else:
                            # La orden ya existe en AdministraNET
                            mapping.sync_status = OrderMapping.SyncStatus.SYNCED
                            mapping.last_synced = timezone.now()
                            mapping.save()
                            successful_syncs += 1
                    
                    sync_log.processed_items += 1
                    sync_log.save()
                    
                except Exception as e:
                    logger.error(f"Error syncing order {order.get('id')}: {e}")
                    failed_syncs += 1
                    sync_log.processed_items += 1
                    sync_log.save()
            
            # Completar sincronización
            sync_log.successful_items = successful_syncs
            sync_log.failed_items = failed_syncs
            sync_log.complete_sync(True)
            
            return {
                'success': True,
                'message': f'Sincronización completada: {successful_syncs} exitosas, {failed_syncs} fallidas',
                'sync_log_id': sync_log.id,
                'total_processed': len(orders),
                'successful': successful_syncs,
                'failed': failed_syncs
            }
            
        except Exception as e:
            logger.error(f"Error in sync_orders_from_tiendanube: {e}")
            if 'sync_log' in locals():
                sync_log.complete_sync(False, str(e))
            return {
                'success': False,
                'message': f'Error en sincronización: {str(e)}'
            }
    
    def sync_order_status_to_tiendanube(self, hours: int = 24) -> Dict[str, Any]:
        """
        Sincronizar estados de órdenes desde AdministraNET hacia TiendaNube.
        
        Args:
            hours: Horas hacia atrás para buscar cambios (default: 24)
            
        Returns:
            Dict con el resultado de la sincronización
        """
        try:
            logger.info(f"Iniciando sincronización de estados de órdenes (últimas {hours} horas)")
            
            # Obtener pedidos de TiendaNube modificados recientemente
            result = self.adminet_service.get_tiendanube_orders_with_changes(hours=hours)
            
            if not result['success']:
                return result
            
            orders = result['orders']
            successful_updates = 0
            failed_updates = 0
            
            for order in orders:
                try:
                    tiendanube_id = order.get('id_tiendanube')
                    estado = order.get('Estado', '')
                    anulado = order.get('anulado', 'No')
                    
                    # Mapear estado de AdministraNET a TiendaNube
                    mapped_status = self.map_adminet_estado_to_tiendanube(estado, anulado)
                    
                    logger.info(f"Sincronizando orden {tiendanube_id}: {estado} → {mapped_status}")
                    
                    # Actualizar estado en TiendaNube
                    # Nota: TiendaNube API puede tener limitaciones en actualización de estados
                    # Por ahora, solo registramos el cambio
                    
                    # Actualizar OrderMapping si existe
                    order_mapping = OrderMapping.objects.filter(
                        tiendanube_id=tiendanube_id
                    ).first()
                    
                    if order_mapping:
                        order_mapping.adminet_estado = estado
                        order_mapping.tiendanube_status = mapped_status['order_status']
                        order_mapping.last_synced = timezone.now()
                        order_mapping.save()
                    
                    successful_updates += 1
                    
                except Exception as e:
                    logger.error(f"Error actualizando estado de orden {order.get('id_tiendanube')}: {e}")
                    failed_updates += 1
            
            return {
                'success': True,
                'message': f'Sincronización de estados completada: {successful_updates} exitosas, {failed_updates} fallidas',
                'total_processed': len(orders),
                'successful': successful_updates,
                'failed': failed_updates
            }
            
        except Exception as e:
            logger.error(f"Error in sync_order_status_to_tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error en sincronización de estados: {str(e)}'
            }
    
    def get_sync_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas de sincronización."""
        try:
            # Estadísticas de mapeos
            customer_mappings = CustomerMapping.objects.all()
            product_mappings = ProductMapping.objects.all()
            order_mappings = OrderMapping.objects.all()
            
            # Logs de sincronización recientes
            recent_logs = SyncLog.objects.filter(
                started_at__gte=timezone.now() - timezone.timedelta(days=7)
            ).order_by('-started_at')[:10]
            
            stats = {
                'customer_mappings': {
                    'total': customer_mappings.count(),
                    'synced': customer_mappings.filter(sync_status=CustomerMapping.SyncStatus.SYNCED).count(),
                    'pending': customer_mappings.filter(sync_status=CustomerMapping.SyncStatus.PENDING).count(),
                    'error': customer_mappings.filter(sync_status=CustomerMapping.SyncStatus.ERROR).count()
                },
                'product_mappings': {
                    'total': product_mappings.count(),
                    'synced': product_mappings.filter(sync_status=ProductMapping.SyncStatus.SYNCED).count(),
                    'pending': product_mappings.filter(sync_status=ProductMapping.SyncStatus.PENDING).count(),
                    'error': product_mappings.filter(sync_status=ProductMapping.SyncStatus.ERROR).count()
                },
                'order_mappings': {
                    'total': order_mappings.count(),
                    'synced': order_mappings.filter(sync_status=OrderMapping.SyncStatus.SYNCED).count(),
                    'pending': order_mappings.filter(sync_status=OrderMapping.SyncStatus.PENDING).count(),
                    'error': order_mappings.filter(sync_status=OrderMapping.SyncStatus.ERROR).count()
                },
                'recent_syncs': [
                    {
                        'id': log.id,
                        'type': log.get_sync_type_display(),
                        'direction': log.get_direction_display(),
                        'status': log.get_status_display(),
                        'started_at': log.started_at,
                        'completed_at': log.completed_at,
                        'total_items': log.total_items,
                        'successful_items': log.successful_items,
                        'failed_items': log.failed_items
                    }
                    for log in recent_logs
                ]
            }
            
            return {
                'success': True,
                'statistics': stats
            }
            
        except Exception as e:
            logger.error(f"Error getting sync statistics: {e}")
            return {
                'success': False,
                'message': f'Error obteniendo estadísticas: {str(e)}'
            } 