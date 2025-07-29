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
                        adminet_data = self._map_tiendanube_to_adminet_product(product)
                        
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
                            self._update_product_mapping_from_tiendanube(mapping, product)
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
            
            # Obtener productos de AdministraNET (solo ecommerce)
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
                        # Mapear datos de AdministraNET a Tiendanube
                        tiendanube_data = self._map_adminet_to_tiendanube_product(product)
                        
                        if mapping.tiendanube_id:
                            # Actualizar producto existente
                            result = self.product_service.update_product(mapping.tiendanube_id, tiendanube_data)
                        else:
                            # Crear nuevo producto
                            result = self.product_service.create_product(tiendanube_data)
                            if result['success']:
                                mapping.tiendanube_id = result.get('product_id')
                        
                        if result['success']:
                            # Actualizar mapeo con datos de AdministraNET
                            self._update_product_mapping_from_adminet(mapping, product)
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
                        adminet_data = self._map_tiendanube_to_adminet_variant(variant)
                        
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
    # MÉTODOS DE MAPEO
    # ============================================================================

    def _map_tiendanube_to_adminet_product(self, tiendanube_product: Dict[str, Any]) -> Dict[str, Any]:
        """Mapear datos de producto de Tiendanube a AdministraNET."""
        return {
            'NombreArticulo': tiendanube_product.get('name', ''),
            'Detalle': tiendanube_product.get('description', ''),
            'Precio1V': float(tiendanube_product.get('price', 0)),
            'PrecioCosto': float(tiendanube_product.get('cost', 0)),
            'saldo_articulo': int(tiendanube_product.get('stock', 0)),
            'NroCodBarra': tiendanube_product.get('sku', ''),
            'ecommerce': 'Si' if tiendanube_product.get('published', True) else 'No',
            'disponible_vta': 'Si',
            'disponible_comp': 'Si',
            'Discontinuo': 'No',
            'detalle_web': tiendanube_product.get('description', ''),
            'Alicuota': 1,  # Por defecto
            'AlicuotaIB': 1,  # Por defecto
            'Moneda': 'ARS',  # Por defecto
            'TipoIVA': 'Responsable Inscripto',  # Por defecto
            'TipoIB': 'Responsable Inscripto'  # Por defecto
        }

    def _map_adminet_to_tiendanube_product(self, adminet_product: Dict[str, Any]) -> Dict[str, Any]:
        """Mapear datos de producto de AdministraNET a Tiendanube."""
        return {
            'name': adminet_product.get('NombreArticulo', ''),
            'description': adminet_product.get('Detalle', ''),
            'price': float(adminet_product.get('Precio1V', 0)),
            'cost': float(adminet_product.get('PrecioCosto', 0)),
            'stock': int(adminet_product.get('saldo_articulo', 0)),
            'sku': adminet_product.get('CodigoArticuloT', ''),
            'published': adminet_product.get('ecommerce') == 'Si',
            'handle': adminet_product.get('CodigoArticuloT', '').lower().replace(' ', '-'),
            'product_type': 'physical',
            'free_shipping': False,
            'featured': False
        }

    def _map_tiendanube_to_adminet_variant(self, tiendanube_variant: Dict[str, Any]) -> Dict[str, Any]:
        """Mapear datos de variante de Tiendanube a AdministraNET."""
        return {
            'NombreArticulo': tiendanube_variant.get('name', ''),
            'Detalle': f"Variante: {tiendanube_variant.get('name', '')}",
            'Precio1V': float(tiendanube_variant.get('price', 0)),
            'PrecioCosto': float(tiendanube_variant.get('cost', 0)),
            'saldo_articulo': int(tiendanube_variant.get('stock', 0)),
            'NroCodBarra': tiendanube_variant.get('sku', ''),
            'ecommerce': 'Si',
            'disponible_vta': 'Si',
            'disponible_comp': 'Si',
            'Discontinuo': 'No',
            'Alicuota': 1,
            'AlicuotaIB': 1,
            'Moneda': 'ARS',
            'TipoIVA': 'Responsable Inscripto',
            'TipoIB': 'Responsable Inscripto'
        }

    def _update_product_mapping_from_tiendanube(self, mapping: ProductMapping, tiendanube_product: Dict[str, Any]):
        """Actualizar mapeo de producto con datos de Tiendanube."""
        mapping.tiendanube_name = tiendanube_product.get('name', '')
        mapping.tiendanube_handle = tiendanube_product.get('handle', '')
        mapping.tiendanube_description = tiendanube_product.get('description', '')
        mapping.tiendanube_sku = tiendanube_product.get('sku', '')
        mapping.tiendanube_price = float(tiendanube_product.get('price', 0))
        mapping.tiendanube_compare_at_price = float(tiendanube_product.get('compare_at_price', 0))
        mapping.tiendanube_cost = float(tiendanube_product.get('cost', 0))
        mapping.tiendanube_stock = int(tiendanube_product.get('stock', 0))
        mapping.tiendanube_weight = float(tiendanube_product.get('weight', 0))
        mapping.tiendanube_width = float(tiendanube_product.get('width', 0))
        mapping.tiendanube_height = float(tiendanube_product.get('height', 0))
        mapping.tiendanube_depth = float(tiendanube_product.get('depth', 0))
        mapping.tiendanube_free_shipping = tiendanube_product.get('free_shipping', False)
        mapping.tiendanube_published = tiendanube_product.get('published', True)
        mapping.tiendanube_featured = tiendanube_product.get('featured', False)
        mapping.tiendanube_product_type = tiendanube_product.get('product_type', 'physical')
        mapping.tiendanube_categories = tiendanube_product.get('categories', [])
        mapping.tiendanube_images = tiendanube_product.get('images', [])
        mapping.tiendanube_videos = tiendanube_product.get('videos', [])
        mapping.tiendanube_seo_title = tiendanube_product.get('seo_title', '')
        mapping.tiendanube_seo_description = tiendanube_product.get('seo_description', '')
        mapping.tiendanube_created_at = tiendanube_product.get('created_at')
        mapping.tiendanube_updated_at = tiendanube_product.get('updated_at')

    def _update_product_mapping_from_adminet(self, mapping: ProductMapping, adminet_product: Dict[str, Any]):
        """Actualizar mapeo de producto con datos de AdministraNET."""
        mapping.adminet_id = adminet_product.get('IDArt')
        mapping.adminet_id_manual = adminet_product.get('id_manual', '')
        mapping.adminet_codigo_articulo = adminet_product.get('CodigoArticuloT', '')
        mapping.adminet_nombre = adminet_product.get('NombreArticulo', '')
        mapping.adminet_detalle = adminet_product.get('Detalle', '')
        mapping.adminet_precio_costo = float(adminet_product.get('PrecioCosto', 0))
        mapping.adminet_precio_1v = float(adminet_product.get('Precio1V', 0))
        mapping.adminet_precio_2v = float(adminet_product.get('Precio2V', 0))
        mapping.adminet_precio_3v = float(adminet_product.get('Precio3V', 0))
        mapping.adminet_precio_4v = float(adminet_product.get('Precio4V', 0))
        mapping.adminet_precio_5v = float(adminet_product.get('Precio5V', 0))
        mapping.adminet_stock = int(adminet_product.get('saldo_articulo', 0))
        mapping.adminet_stock_max = float(adminet_product.get('stock_max', 0))
        mapping.adminet_stock_min = float(adminet_product.get('stock_min', 0))
        mapping.adminet_codigo_barra = adminet_product.get('NroCodBarra', '')
        mapping.adminet_codigo_barra_f = adminet_product.get('NroCodBarraF', '')
        mapping.adminet_codigo_proveedor = adminet_product.get('CodigoProveedor')
        mapping.adminet_codigo_marca = adminet_product.get('CodigoMarca')
        mapping.adminet_codigo_modelo = adminet_product.get('CodigoModelo')
        mapping.adminet_codigo_rubro = adminet_product.get('CodigoRubro')
        mapping.adminet_codigo_subrubro = adminet_product.get('CodigoSubRubro')
        mapping.adminet_alicuota = adminet_product.get('Alicuota')
        mapping.adminet_alicuota_ib = adminet_product.get('AlicuotaIB')
        mapping.adminet_moneda = adminet_product.get('Moneda', '')
        mapping.adminet_tipo_iva = adminet_product.get('TipoIVA', '')
        mapping.adminet_tipo_ib = adminet_product.get('TipoIB', '')
        mapping.adminet_discontinuo = adminet_product.get('Discontinuo', '')
        mapping.adminet_ecommerce = adminet_product.get('ecommerce', '')
        mapping.adminet_detalle_web = adminet_product.get('detalle_web', '')
        mapping.adminet_disponible_venta = adminet_product.get('disponible_vta', '')
        mapping.adminet_disponible_compra = adminet_product.get('disponible_comp', '')
        mapping.adminet_fecha_alta = adminet_product.get('fecha_alta')
        mapping.adminet_fecha_mod = adminet_product.get('fecha_mod')

    def _update_variant_mapping_from_tiendanube(self, mapping: ProductVariantMapping, tiendanube_variant: Dict[str, Any]):
        """Actualizar mapeo de variante con datos de Tiendanube."""
        mapping.tiendanube_name = tiendanube_variant.get('name', '')
        mapping.tiendanube_sku = tiendanube_variant.get('sku', '')
        mapping.tiendanube_price = float(tiendanube_variant.get('price', 0))
        mapping.tiendanube_compare_at_price = float(tiendanube_variant.get('compare_at_price', 0))
        mapping.tiendanube_cost = float(tiendanube_variant.get('cost', 0))
        mapping.tiendanube_stock = int(tiendanube_variant.get('stock', 0))
        mapping.tiendanube_weight = float(tiendanube_variant.get('weight', 0))
        mapping.tiendanube_width = float(tiendanube_variant.get('width', 0))
        mapping.tiendanube_height = float(tiendanube_variant.get('height', 0))
        mapping.tiendanube_depth = float(tiendanube_variant.get('depth', 0))
        mapping.tiendanube_free_shipping = tiendanube_variant.get('free_shipping', False)
        mapping.tiendanube_published = tiendanube_variant.get('published', True)
        mapping.tiendanube_values = tiendanube_variant.get('values', {})
        mapping.tiendanube_images = tiendanube_variant.get('images', [])
        mapping.tiendanube_created_at = tiendanube_variant.get('created_at')
        mapping.tiendanube_updated_at = tiendanube_variant.get('updated_at')

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
                        # Crear/actualizar en AdministraNET
                        adminet_data = {
                            'numero': order.get('number', ''),
                            'cliente_email': order.get('customer_email', ''),
                            'total': order.get('total', 0),
                            'estado': order.get('status', 'pending')
                        }
                        
                        if mapping.adminet_codigo:
                            # Actualizar orden existente (implementar según estructura de AdministraNET)
                            pass
                        else:
                            # Crear nueva orden (implementar según estructura de AdministraNET)
                            pass
                        
                        # Por ahora, marcamos como sincronizado
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