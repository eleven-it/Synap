"""
Servicio para gestión de webhooks de Tiendanube.
"""

import json
import hashlib
import hmac
import logging
import requests
from typing import Dict, List, Optional, Any, Tuple
from django.utils import timezone
from django.conf import settings
from ..models import WebhookConfig, WebhookEvent, WebhookDeliveryLog

logger = logging.getLogger(__name__)


class WebhookService:
    """
    Servicio para gestionar webhooks de Tiendanube.
    """
    
    def __init__(self, tiendanube_config):
        self.tiendanube_config = tiendanube_config
        self.base_url = tiendanube_config.api_url
        self.headers = {
            'Authentication': f'token {tiendanube_config.access_token}',
            'Content-Type': 'application/json',
            'User-Agent': 'Synap-Tiendanube-Webhook/1.0'
        }
    
    def create_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crear webhook en Tiendanube.
        
        Args:
            webhook_data: Datos del webhook a crear
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            url = f"{self.base_url}/stores/{self.tiendanube_config.store_id}/webhooks"
            
            # Preparar datos del webhook
            webhook_payload = {
                "url": webhook_data['webhook_url'],
                "events": webhook_data.get('events', []),
                "description": webhook_data.get('description', '')
            }
            
            logger.info(f"Creating webhook: {webhook_payload['url']}")
            response = requests.post(url, headers=self.headers, json=webhook_payload)
            
            if response.status_code in [200, 201]:
                webhook_response = response.json()
                logger.info(f"Webhook created successfully: {webhook_response.get('id')}")
                
                return {
                    'success': True,
                    'webhook_id': webhook_response.get('id'),
                    'webhook_data': webhook_response,
                    'message': 'Webhook created successfully'
                }
            else:
                error_msg = f"Error creating webhook: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            error_msg = f"Exception creating webhook: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def get_webhooks(self) -> Dict[str, Any]:
        """
        Obtener lista de webhooks configurados en Tiendanube.
        
        Returns:
            Dict con lista de webhooks
        """
        try:
            url = f"{self.base_url}/stores/{self.tiendanube_config.store_id}/webhooks"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                webhooks = response.json()
                logger.info(f"Retrieved {len(webhooks)} webhooks")
                
                return {
                    'success': True,
                    'webhooks': webhooks,
                    'count': len(webhooks)
                }
            else:
                error_msg = f"Error getting webhooks: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            error_msg = f"Exception getting webhooks: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def get_webhook(self, webhook_id: int) -> Dict[str, Any]:
        """
        Obtener webhook específico de Tiendanube.
        
        Args:
            webhook_id: ID del webhook
            
        Returns:
            Dict con datos del webhook
        """
        try:
            url = f"{self.base_url}/stores/{self.tiendanube_config.store_id}/webhooks/{webhook_id}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                webhook = response.json()
                logger.info(f"Retrieved webhook {webhook_id}")
                
                return {
                    'success': True,
                    'webhook': webhook
                }
            else:
                error_msg = f"Error getting webhook {webhook_id}: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            error_msg = f"Exception getting webhook {webhook_id}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def update_webhook(self, webhook_id: int, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualizar webhook en Tiendanube.
        
        Args:
            webhook_id: ID del webhook
            webhook_data: Datos a actualizar
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            url = f"{self.base_url}/stores/{self.tiendanube_config.store_id}/webhooks/{webhook_id}"
            
            # Preparar datos del webhook
            webhook_payload = {
                "url": webhook_data['webhook_url'],
                "events": webhook_data.get('events', []),
                "description": webhook_data.get('description', '')
            }
            
            logger.info(f"Updating webhook {webhook_id}")
            response = requests.put(url, headers=self.headers, json=webhook_payload)
            
            if response.status_code == 200:
                webhook_response = response.json()
                logger.info(f"Webhook {webhook_id} updated successfully")
                
                return {
                    'success': True,
                    'webhook_data': webhook_response,
                    'message': 'Webhook updated successfully'
                }
            else:
                error_msg = f"Error updating webhook {webhook_id}: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            error_msg = f"Exception updating webhook {webhook_id}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def delete_webhook(self, webhook_id: int) -> Dict[str, Any]:
        """
        Eliminar webhook de Tiendanube.
        
        Args:
            webhook_id: ID del webhook
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            url = f"{self.base_url}/stores/{self.tiendanube_config.store_id}/webhooks/{webhook_id}"
            
            logger.info(f"Deleting webhook {webhook_id}")
            response = requests.delete(url, headers=self.headers)
            
            if response.status_code == 200:
                logger.info(f"Webhook {webhook_id} deleted successfully")
                
                return {
                    'success': True,
                    'message': 'Webhook deleted successfully'
                }
            else:
                error_msg = f"Error deleting webhook {webhook_id}: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            error_msg = f"Exception deleting webhook {webhook_id}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def test_webhook(self, webhook_id: int) -> Dict[str, Any]:
        """
        Probar webhook enviando un evento de prueba.
        
        Args:
            webhook_id: ID del webhook
            
        Returns:
            Dict con resultado de la prueba
        """
        try:
            url = f"{self.base_url}/stores/{self.tiendanube_config.store_id}/webhooks/{webhook_id}/test"
            
            logger.info(f"Testing webhook {webhook_id}")
            response = requests.post(url, headers=self.headers)
            
            if response.status_code == 200:
                logger.info(f"Webhook {webhook_id} test successful")
                
                return {
                    'success': True,
                    'message': 'Webhook test successful'
                }
            else:
                error_msg = f"Error testing webhook {webhook_id}: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            error_msg = f"Exception testing webhook {webhook_id}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }


class WebhookProcessor:
    """
    Procesador de eventos de webhook recibidos.
    """
    
    @staticmethod
    def verify_signature(payload: str, signature: str, secret: str) -> bool:
        """
        Verificar firma del webhook para autenticidad.
        
        Args:
            payload: Cuerpo del request
            signature: Firma recibida
            secret: Secreto del webhook
            
        Returns:
            True si la firma es válida
        """
        try:
            if not secret:
                logger.warning("No webhook secret configured, skipping signature verification")
                return True
            
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(f"sha256={expected_signature}", signature)
            
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {str(e)}")
            return False
    
    @staticmethod
    def process_webhook_event(webhook_config: WebhookConfig, event_data: Dict[str, Any], 
                            headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Procesar evento de webhook recibido.
        
        Args:
            webhook_config: Configuración del webhook
            event_data: Datos del evento
            headers: Headers del request
            
        Returns:
            Dict con resultado del procesamiento
        """
        try:
            # Extraer información del evento
            event_type = event_data.get('type')
            event_id = event_data.get('id')
            resource_id = event_data.get('data', {}).get('id')
            resource_type = event_type.split('/')[0] if event_type else None
            
            # Crear registro del evento
            webhook_event = WebhookEvent.objects.create(
                webhook_config=webhook_config,
                event_type=event_type,
                event_id=event_id,
                resource_id=resource_id,
                resource_type=resource_type,
                payload=event_data,
                headers=headers
            )
            
            logger.info(f"Processing webhook event: {event_type} - {event_id}")
            
            # Marcar como en procesamiento
            webhook_event.mark_processing()
            
            # Procesar según el tipo de evento
            result = WebhookProcessor._handle_event_by_type(webhook_event, event_data)
            
            if result['success']:
                webhook_event.mark_completed(result)
                logger.info(f"Webhook event {event_id} processed successfully")
            else:
                webhook_event.mark_failed(result['error'])
                logger.error(f"Webhook event {event_id} failed: {result['error']}")
            
            # Actualizar último trigger del webhook
            webhook_config.last_triggered = timezone.now()
            webhook_config.save(update_fields=['last_triggered'])
            
            return result
            
        except Exception as e:
            error_msg = f"Error processing webhook event: {str(e)}"
            logger.error(error_msg)
            
            if 'webhook_event' in locals():
                webhook_event.mark_failed(error_msg, retry=False)
            
            return {
                'success': False,
                'error': error_msg
            }
    
    @staticmethod
    def _handle_event_by_type(webhook_event: WebhookEvent, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manejar evento según su tipo.
        
        Args:
            webhook_event: Evento de webhook
            event_data: Datos del evento
            
        Returns:
            Dict con resultado del procesamiento
        """
        event_type = webhook_event.event_type
        
        try:
            if event_type.startswith('product/'):
                return WebhookProcessor._handle_product_event(webhook_event, event_data)
            elif event_type.startswith('order/'):
                return WebhookProcessor._handle_order_event(webhook_event, event_data)
            elif event_type.startswith('customer/'):
                return WebhookProcessor._handle_customer_event(webhook_event, event_data)
            elif event_type.startswith('inventory/'):
                return WebhookProcessor._handle_inventory_event(webhook_event, event_data)
            elif event_type.startswith('category/'):
                return WebhookProcessor._handle_category_event(webhook_event, event_data)
            else:
                logger.warning(f"Unknown event type: {event_type}")
                return {
                    'success': True,
                    'message': f'Unknown event type {event_type} - ignored'
                }
                
        except Exception as e:
            error_msg = f"Error handling event {event_type}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    @staticmethod
    def _handle_product_event(webhook_event: WebhookEvent, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Manejar eventos de productos."""
        from ..services.sync_service import TiendanubeAdministraNETSyncService
        
        try:
            product_data = event_data.get('data', {})
            product_id = product_data.get('id')
            
            # Obtener configuraciones activas
            tiendanube_config = webhook_event.webhook_config.tiendanube_config
            adminet_config = tiendanube_config.administraNETconfig_set.filter(is_active=True).first()
            
            if not adminet_config:
                return {
                    'success': False,
                    'error': 'No active AdministraNET configuration found'
                }
            
            # Crear servicio de sincronización
            sync_service = TiendanubeAdministraNETSyncService(tiendanube_config, adminet_config)
            
            # Procesar según el tipo de evento
            if webhook_event.event_type == 'product/created':
                # Crear mapeo de producto
                from ..models import ProductMapping
                mapping, created = ProductMapping.objects.get_or_create(
                    tiendanube_id=product_id,
                    defaults={
                        'tiendanube_name': product_data.get('name', ''),
                        'tiendanube_sku': product_data.get('sku', ''),
                        'tiendanube_price': product_data.get('price', 0),
                        'tiendanube_stock': product_data.get('stock', 0),
                        'sync_status': ProductMapping.SyncStatus.PENDING
                    }
                )
                
                return {
                    'success': True,
                    'action': 'product_created',
                    'mapping_created': created,
                    'product_id': product_id
                }
                
            elif webhook_event.event_type == 'product/updated':
                # Actualizar mapeo de producto
                from ..models import ProductMapping
                try:
                    mapping = ProductMapping.objects.get(tiendanube_id=product_id)
                    mapping.tiendanube_name = product_data.get('name', mapping.tiendanube_name)
                    mapping.tiendanube_sku = product_data.get('sku', mapping.tiendanube_sku)
                    mapping.tiendanube_price = product_data.get('price', mapping.tiendanube_price)
                    mapping.tiendanube_stock = product_data.get('stock', mapping.tiendanube_stock)
                    mapping.sync_status = ProductMapping.SyncStatus.PENDING
                    mapping.save()
                    
                    return {
                        'success': True,
                        'action': 'product_updated',
                        'product_id': product_id
                    }
                except ProductMapping.DoesNotExist:
                    return {
                        'success': False,
                        'error': f'Product mapping not found for ID {product_id}'
                    }
                    
            elif webhook_event.event_type == 'product/deleted':
                # Marcar mapeo como eliminado
                from ..models import ProductMapping
                try:
                    mapping = ProductMapping.objects.get(tiendanube_id=product_id)
                    mapping.sync_status = ProductMapping.SyncStatus.ERROR
                    mapping.error_message = 'Product deleted in Tiendanube'
                    mapping.save()
                    
                    return {
                        'success': True,
                        'action': 'product_deleted',
                        'product_id': product_id
                    }
                except ProductMapping.DoesNotExist:
                    return {
                        'success': True,
                        'action': 'product_deleted',
                        'message': f'Product mapping not found for ID {product_id}'
                    }
            
            return {
                'success': True,
                'action': 'product_event_processed',
                'event_type': webhook_event.event_type
            }
            
        except Exception as e:
            error_msg = f"Error handling product event: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    @staticmethod
    def _handle_order_event(webhook_event: WebhookEvent, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Manejar eventos de órdenes."""
        try:
            order_data = event_data.get('data', {})
            order_id = order_data.get('id')
            
            # Obtener configuraciones activas
            tiendanube_config = webhook_event.webhook_config.tiendanube_config
            adminet_config = tiendanube_config.administraNETconfig_set.filter(is_active=True).first()
            
            if not adminet_config:
                return {
                    'success': False,
                    'error': 'No active AdministraNET configuration found'
                }
            
            # Crear servicio de sincronización
            from ..services.sync_service import TiendanubeAdministraNETSyncService
            sync_service = TiendanubeAdministraNETSyncService(tiendanube_config, adminet_config)
            
            # Procesar según el tipo de evento
            if webhook_event.event_type == 'order/created':
                # Crear mapeo de orden (solo registro inicial)
                from ..models import OrderMapping
                mapping, created = OrderMapping.objects.get_or_create(
                    tiendanube_id=order_id,
                    defaults={
                        'tiendanube_number': order_data.get('number', ''),
                        'tiendanube_status': order_data.get('status', ''),
                        'tiendanube_total': order_data.get('total', 0),
                        'tiendanube_customer_email': order_data.get('customer', {}).get('email', ''),
                        'sync_status': OrderMapping.SyncStatus.PENDING
                    }
                )
                
                return {
                    'success': True,
                    'action': 'order_created',
                    'mapping_created': created,
                    'order_id': order_id,
                    'message': 'Order mapping created, waiting for payment confirmation'
                }
                
            elif webhook_event.event_type == 'order/paid':
                # Orden pagada → Crear en AdministraNET
                from ..models import OrderMapping, ProductMapping
                
                # Crear o actualizar mapeo
                mapping, created = OrderMapping.objects.get_or_create(
                    tiendanube_id=order_id,
                    defaults={
                        'tiendanube_number': order_data.get('number', ''),
                        'tiendanube_status': order_data.get('status', ''),
                        'tiendanube_total': order_data.get('total', 0),
                        'tiendanube_customer_email': order_data.get('customer', {}).get('email', ''),
                        'sync_status': OrderMapping.SyncStatus.PENDING
                    }
                )
                
                # Si aún no se creó en AdministraNET, crearlo ahora
                if not mapping.adminet_codigo:
                    # Preparar datos de la orden
                    order_data_for_adminet = {
                        'id': order_id,
                        'number': order_data.get('number'),
                        'customer': order_data.get('customer', {}),
                        'shipping_address': order_data.get('shipping_address', {}),
                        'shipping': order_data.get('shipping', {}),
                        'payment': order_data.get('payment', {}),
                        'products': order_data.get('products', []),
                        'subtotal': order_data.get('subtotal', 0),
                        'total': order_data.get('total', 0),
                        'discount': order_data.get('discount', 0),
                        'shipping_cost': order_data.get('shipping_cost', 0),
                        'payment_status': order_data.get('payment_status', 'paid'),
                        'created_at': order_data.get('created_at', ''),
                        'updated_at': order_data.get('updated_at', ''),
                        'adminet_customer_id': 1  # TODO: Obtener o crear cliente
                    }
                    
                    # Mapear productos a AdministraNET IDs
                    for product in order_data_for_adminet['products']:
                        product_mapping = ProductMapping.objects.filter(
                            tiendanube_id=product.get('product_id')
                        ).first()
                        
                        if product_mapping and product_mapping.adminet_id:
                            product['adminet_product_id'] = product_mapping.adminet_id
                        else:
                            product['adminet_product_id'] = 0
                            logger.warning(f"Producto {product.get('product_id')} no mapeado en orden {order_id}")
                    
                    # Crear orden en AdministraNET
                    result = sync_service.adminet_service.create_order_from_tiendanube(
                        order_data_for_adminet,
                        deposito_id=adminet_config.deposito_tiendanube_id or 1,
                        user_id=1,
                        sucursal_id=1
                    )
                    
                    if result['success']:
                        mapping.adminet_codigo = result['codigo_movimiento']
                        mapping.adminet_numero = result['nro_comprobante']
                        mapping.adminet_estado = 'Pendiente'
                        mapping.sync_status = OrderMapping.SyncStatus.SYNCED
                        mapping.last_synced = timezone.now()
                        mapping.save()
                        
                        logger.info(f"Orden {order_id} creada en AdministraNET: {result['nro_comprobante']}")
                        
                        return {
                            'success': True,
                            'action': 'order_paid_and_created',
                            'order_id': order_id,
                            'adminet_nro': result['nro_comprobante'],
                            'adminet_codigo': result['codigo_movimiento']
                        }
                    else:
                        mapping.sync_status = OrderMapping.SyncStatus.ERROR
                        mapping.error_message = result['message']
                        mapping.save()
                        
                        return {
                            'success': False,
                            'error': f"Error creando orden en AdministraNET: {result['message']}"
                        }
                
                return {
                    'success': True,
                    'action': 'order_paid',
                    'message': 'Order already created in AdministraNET',
                    'order_id': order_id
                }
                
            elif webhook_event.event_type in ['order/updated', 'order/fulfilled']:
                # Actualizar mapeo de orden
                from ..models import OrderMapping
                try:
                    mapping = OrderMapping.objects.get(tiendanube_id=order_id)
                    mapping.tiendanube_status = order_data.get('status', mapping.tiendanube_status)
                    mapping.tiendanube_total = order_data.get('total', mapping.tiendanube_total)
                    mapping.sync_status = OrderMapping.SyncStatus.PENDING
                    mapping.save()
                    
                    # Si el evento es fulfilled, podríamos registrar la entrega
                    if webhook_event.event_type == 'order/fulfilled':
                        logger.info(f"Orden {order_id} marcada como fulfilled en TiendaNube")
                    
                    return {
                        'success': True,
                        'action': 'order_updated',
                        'order_id': order_id
                    }
                except OrderMapping.DoesNotExist:
                    # Si no existe el mapeo, crearlo
                    mapping = OrderMapping.objects.create(
                        tiendanube_id=order_id,
                        tiendanube_number=order_data.get('number', ''),
                        tiendanube_status=order_data.get('status', ''),
                        tiendanube_total=order_data.get('total', 0),
                        tiendanube_customer_email=order_data.get('customer', {}).get('email', ''),
                        sync_status=OrderMapping.SyncStatus.PENDING
                    )
                    
                    return {
                        'success': True,
                        'action': 'order_updated',
                        'mapping_created': True,
                        'order_id': order_id
                    }
                    
            elif webhook_event.event_type == 'order/cancelled':
                # Marcar orden como cancelada en TiendaNube y AdministraNET
                from ..models import OrderMapping
                try:
                    mapping = OrderMapping.objects.get(tiendanube_id=order_id)
                    mapping.tiendanube_status = 'cancelled'
                    mapping.sync_status = OrderMapping.SyncStatus.SYNCED
                    mapping.save()
                    
                    # Si existe en AdministraNET, marcar como anulada
                    if mapping.adminet_codigo:
                        cancel_query = """
                        UPDATE comp_ped 
                        SET anulado = 'Si'
                        WHERE CodigoMovimiento = %s
                        """
                        
                        result = sync_service.adminet_service.execute_query(
                            cancel_query, 
                            (mapping.adminet_codigo,)
                        )
                        
                        if result['success']:
                            logger.info(f"Orden {mapping.adminet_numero} (CodigoMovimiento: {mapping.adminet_codigo}) marcada como anulada en AdministraNET")
                            
                            # También liberar stock comprometido
                            # (AdministraNET debería hacer esto automáticamente con un trigger o procedimiento)
                            
                            return {
                                'success': True,
                                'action': 'order_cancelled_both_systems',
                                'order_id': order_id,
                                'adminet_codigo': mapping.adminet_codigo
                            }
                        else:
                            logger.error(f"Error anulando orden en AdministraNET: {result.get('message')}")
                            return {
                                'success': False,
                                'error': f"Error anulando orden en AdministraNET: {result.get('message')}"
                            }
                    else:
                        # Solo existe en TiendaNube
                        return {
                            'success': True,
                            'action': 'order_cancelled',
                            'order_id': order_id,
                            'message': 'Order cancelled in TiendaNube only (not yet created in AdministraNET)'
                        }
                    
                except OrderMapping.DoesNotExist:
                    return {
                        'success': True,
                        'action': 'order_cancelled',
                        'message': f'Order mapping not found for ID {order_id} (order was never synced)'
                    }
            
            return {
                'success': True,
                'action': 'order_event_processed',
                'event_type': webhook_event.event_type
            }
            
        except Exception as e:
            error_msg = f"Error handling order event: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    @staticmethod
    def _handle_customer_event(webhook_event: WebhookEvent, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Manejar eventos de clientes."""
        try:
            customer_data = event_data.get('data', {})
            customer_id = customer_data.get('id')
            
            # Obtener configuraciones activas
            tiendanube_config = webhook_event.webhook_config.tiendanube_config
            adminet_config = tiendanube_config.administraNETconfig_set.filter(is_active=True).first()
            
            if not adminet_config:
                return {
                    'success': False,
                    'error': 'No active AdministraNET configuration found'
                }
            
            # Crear servicio de sincronización
            from ..services.sync_service import TiendanubeAdministraNETSyncService
            sync_service = TiendanubeAdministraNETSyncService(tiendanube_config, adminet_config)
            
            # Procesar según el tipo de evento
            if webhook_event.event_type == 'customer/created':
                # Crear mapeo de cliente
                from ..models import CustomerMapping
                mapping, created = CustomerMapping.objects.get_or_create(
                    tiendanube_id=customer_id,
                    defaults={
                        'tiendanube_email': customer_data.get('email', ''),
                        'tiendanube_name': customer_data.get('name', ''),
                        'tiendanube_document': customer_data.get('document', ''),
                        'tiendanube_phone': customer_data.get('phone', ''),
                        'tiendanube_address': customer_data.get('address', ''),
                        'sync_status': CustomerMapping.SyncStatus.PENDING
                    }
                )
                
                return {
                    'success': True,
                    'action': 'customer_created',
                    'mapping_created': created,
                    'customer_id': customer_id
                }
                
            elif webhook_event.event_type == 'customer/updated':
                # Actualizar mapeo de cliente
                from ..models import CustomerMapping
                try:
                    mapping = CustomerMapping.objects.get(tiendanube_id=customer_id)
                    mapping.tiendanube_email = customer_data.get('email', mapping.tiendanube_email)
                    mapping.tiendanube_name = customer_data.get('name', mapping.tiendanube_name)
                    mapping.tiendanube_document = customer_data.get('document', mapping.tiendanube_document)
                    mapping.tiendanube_phone = customer_data.get('phone', mapping.tiendanube_phone)
                    mapping.tiendanube_address = customer_data.get('address', mapping.tiendanube_address)
                    mapping.sync_status = CustomerMapping.SyncStatus.PENDING
                    mapping.save()
                    
                    return {
                        'success': True,
                        'action': 'customer_updated',
                        'customer_id': customer_id
                    }
                except CustomerMapping.DoesNotExist:
                    return {
                        'success': False,
                        'error': f'Customer mapping not found for ID {customer_id}'
                    }
                    
            elif webhook_event.event_type == 'customer/deleted':
                # Marcar cliente como eliminado
                from ..models import CustomerMapping
                try:
                    mapping = CustomerMapping.objects.get(tiendanube_id=customer_id)
                    mapping.sync_status = CustomerMapping.SyncStatus.ERROR
                    mapping.error_message = 'Customer deleted in Tiendanube'
                    mapping.save()
                    
                    return {
                        'success': True,
                        'action': 'customer_deleted',
                        'customer_id': customer_id
                    }
                except CustomerMapping.DoesNotExist:
                    return {
                        'success': True,
                        'action': 'customer_deleted',
                        'message': f'Customer mapping not found for ID {customer_id}'
                    }
            
            return {
                'success': True,
                'action': 'customer_event_processed',
                'event_type': webhook_event.event_type
            }
            
        except Exception as e:
            error_msg = f"Error handling customer event: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    @staticmethod
    def _handle_inventory_event(webhook_event: WebhookEvent, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Manejar eventos de inventario."""
        try:
            inventory_data = event_data.get('data', {})
            product_id = inventory_data.get('product_id')
            
            # Actualizar stock del producto
            from ..models import ProductMapping
            try:
                mapping = ProductMapping.objects.get(tiendanube_id=product_id)
                mapping.tiendanube_stock = inventory_data.get('stock', mapping.tiendanube_stock)
                mapping.sync_status = ProductMapping.SyncStatus.PENDING
                mapping.save()
                
                return {
                    'success': True,
                    'action': 'inventory_updated',
                    'product_id': product_id,
                    'new_stock': inventory_data.get('stock')
                }
            except ProductMapping.DoesNotExist:
                return {
                    'success': False,
                    'error': f'Product mapping not found for ID {product_id}'
                }
                
        except Exception as e:
            error_msg = f"Error handling inventory event: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    @staticmethod
    def _handle_category_event(webhook_event: WebhookEvent, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Manejar eventos de categorías."""
        try:
            category_data = event_data.get('data', {})
            category_id = category_data.get('id')
            
            # Por ahora solo loguear eventos de categoría
            logger.info(f"Category event received: {webhook_event.event_type} - {category_id}")
            
            return {
                'success': True,
                'action': 'category_event_processed',
                'event_type': webhook_event.event_type,
                'category_id': category_id
            }
            
        except Exception as e:
            error_msg = f"Error handling category event: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            } 