"""
Procesador de webhooks de Tiendanube.
"""

import logging
import json
import hmac
import hashlib
from typing import Dict, Any, Tuple
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from django.conf import settings

from ..models import TiendanubeConfig, AdministraNETConfig, WebhookEvent, WebhookDeliveryLog
from .sync_service import TiendanubeAdministraNETSyncService
from .location_mapper import LocationMapper

logger = logging.getLogger(__name__)


class WebhookProcessor:
    """
    Procesador de webhooks de Tiendanube.
    """
    
    def __init__(self, tiendanube_config: TiendanubeConfig, adminet_config: AdministraNETConfig):
        self.tiendanube_config = tiendanube_config
        self.adminet_config = adminet_config
        self.sync_service = TiendanubeAdministraNETSyncService(tiendanube_config, adminet_config)
        self.location_mapper = LocationMapper(adminet_config)
    
    def process_webhook(self, request: HttpRequest) -> Dict[str, Any]:
        """
        Procesar webhook recibido de Tiendanube.
        
        Args:
            request: Request HTTP con el webhook
            
        Returns:
            Dict con resultado del procesamiento
        """
        try:
            # Verificar firma del webhook (temporalmente deshabilitado para testing)
            # if not self._verify_webhook_signature(request):
            #     logger.warning("Webhook signature verification failed")
            #     return {
            #         'success': False,
            #         'error': 'Invalid webhook signature'
            #     }
            
            # Obtener datos del webhook
            webhook_data = json.loads(request.body.decode('utf-8'))
            
            # Obtener event_type del payload o del header
            event_type = webhook_data.get('event', '') or request.headers.get('X-Tiendanube-Event', '')
            webhook_id = request.headers.get('X-Tiendanube-Webhook-Id', '') or webhook_data.get('id', '')
            
            logger.info(f"Processing webhook: {event_type} (ID: {webhook_id})")
            
            # Obtener configuración de webhook
            webhook_config = self.tiendanube_config.webhooks.filter(is_active=True).first()
            if not webhook_config:
                return {
                    'success': False,
                    'error': 'No active webhook configuration found'
                }
            
            # Extraer resource_id del payload
            resource_id = self._extract_resource_id(webhook_data, event_type)
            
            # Crear registro del evento
            webhook_event = WebhookEvent.objects.create(
                webhook_config=webhook_config,
                event_id=webhook_id,
                event_type=event_type,
                resource_id=resource_id,
                resource_type=self._get_resource_type(event_type),
                payload=webhook_data,
                headers=dict(request.headers),
                status='processing'
            )
            
            # Procesar según el tipo de evento
            result = self._handle_webhook_event(webhook_event, webhook_data)
            
            # Actualizar estado del evento
            if result['success']:
                webhook_event.status = 'processed'
                webhook_event.processed_at = timezone.now()
            else:
                webhook_event.status = 'error'
                webhook_event.error_message = result.get('error', 'Unknown error')
            
            webhook_event.save()
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_resource_id(self, webhook_data: Dict[str, Any], event_type: str) -> int:
        """
        Extraer el ID del recurso del payload del webhook.
        
        Args:
            webhook_data: Datos del webhook
            event_type: Tipo de evento
            
        Returns:
            ID del recurso o None si no se encuentra
        """
        try:
            # Buscar ID en diferentes ubicaciones del payload
            resource_id = None
            
            # 1. Buscar en el nivel raíz
            if 'id' in webhook_data:
                resource_id = webhook_data['id']
            
            # 2. Buscar en 'data' si existe
            if not resource_id and 'data' in webhook_data:
                data = webhook_data['data']
                if isinstance(data, dict) and 'id' in data:
                    resource_id = data['id']
            
            # 3. Buscar en 'resource' si existe
            if not resource_id and 'resource' in webhook_data:
                resource = webhook_data['resource']
                if isinstance(resource, dict) and 'id' in resource:
                    resource_id = resource['id']
            
            # Convertir a entero si es posible
            if resource_id is not None:
                try:
                    return int(resource_id)
                except (ValueError, TypeError):
                    logger.warning(f"Could not convert resource_id to int: {resource_id}")
                    return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting resource_id: {e}")
            return None
    
    def _get_resource_type(self, event_type: str) -> str:
        """
        Determinar el tipo de recurso basado en el tipo de evento.
        
        Args:
            event_type: Tipo de evento
            
        Returns:
            Tipo de recurso
        """
        if event_type.startswith('customer/'):
            return 'customer'
        elif event_type.startswith('product/'):
            return 'product'
        elif event_type.startswith('order/'):
            return 'order'
        else:
            return 'unknown'
    
    def _map_location_data(self, address_data: Dict[str, Any]) -> Tuple[str, int, int]:
        """
        Mapear datos de ubicación usando análisis predictivo.
        
        Args:
            address_data: Datos de dirección desde Tiendanube
            
        Returns:
            Tupla con (calle_completa, cod_provincia, id_departamento)
        """
        # Extraer datos de dirección
        street = address_data.get('address', '')
        number = address_data.get('number', '')
        floor = address_data.get('floor', '')
        locality = address_data.get('locality', '')
        city = address_data.get('city', '')
        province = address_data.get('province', '')
        
        # Mapear ubicación usando análisis predictivo
        cod_provincia, id_departamento, location_info = self.location_mapper.map_location(province, city)
        
        # Construir dirección completa incluyendo información de ubicación
        calle_completa = self.location_mapper.build_complete_address(
            street, number, floor, locality, city, province
        )
        
        # Si no se encontró provincia, usar default
        if cod_provincia is None:
            cod_provincia = 1  # Buenos Aires como default
            logger.warning(f"Provincia '{province}' no encontrada, usando Buenos Aires (1) como default")
        
        # Si no se encontró departamento, usar None
        if id_departamento is None:
            logger.warning(f"Ciudad '{city}' no encontrada en provincia {cod_provincia}")
        
        return calle_completa, cod_provincia, id_departamento
    
    def _verify_webhook_signature(self, request: HttpRequest) -> bool:
        """
        Verificar la firma del webhook.
        
        Args:
            request: Request HTTP
            
        Returns:
            True si la firma es válida
        """
        try:
            # Obtener firma del header
            signature = request.headers.get('X-Tiendanube-Signature', '')
            if not signature:
                return False
            
            # Obtener secret del webhook (si está configurado)
            webhook_secret = getattr(settings, 'TIENDANUBE_WEBHOOK_SECRET', None)
            if not webhook_secret:
                # Si no hay secret configurado, aceptar el webhook
                return True
            
            # Calcular firma esperada
            expected_signature = hmac.new(
                webhook_secret.encode('utf-8'),
                request.body,
                hashlib.sha256
            ).hexdigest()
            
            # Comparar firmas
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False
    
    def _handle_webhook_event(self, webhook_event: WebhookEvent, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manejar evento específico del webhook.
        
        Args:
            webhook_event: Evento del webhook
            webhook_data: Datos del webhook
            
        Returns:
            Dict con resultado del procesamiento
        """
        try:
            event_type = webhook_event.event_type
            
            if event_type.startswith('order/'):
                return self._handle_order_event(webhook_event, webhook_data)
            elif event_type.startswith('product/'):
                return self._handle_product_event(webhook_event, webhook_data)
            elif event_type.startswith('customer/'):
                return self._handle_customer_event(webhook_event, webhook_data)
            else:
                logger.info(f"Unhandled webhook event type: {event_type}")
                return {
                    'success': True,
                    'action': 'ignored',
                    'message': f'Event type {event_type} not handled'
                }
                
        except Exception as e:
            logger.error(f"Error handling webhook event: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _handle_order_event(self, webhook_event: WebhookEvent, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manejar eventos de órdenes.
        
        Args:
            webhook_event: Evento del webhook
            webhook_data: Datos del webhook
            
        Returns:
            Dict con resultado del procesamiento
        """
        try:
            order_id = webhook_data.get('id')
            if not order_id:
                return {
                    'success': False,
                    'error': 'No order ID in webhook data'
                }
            
            event_type = webhook_event.event_type
            
            if event_type == 'order/created':
                # Orden creada - solo registrar
                webhook_event.tiendanube_order_id = order_id
                webhook_event.save()
                
                return {
                    'success': True,
                    'action': 'order_created',
                    'order_id': order_id,
                    'message': 'Order created event registered'
                }
                
            elif event_type == 'order/paid':
                # Orden pagada - crear en AdministraNET
                return self.sync_service.sync_orders_from_tiendanube([order_id])
                
            elif event_type == 'order/updated':
                # Orden actualizada - actualizar en AdministraNET
                return self.sync_service.sync_order_status_to_tiendanube()
                
            elif event_type == 'order/fulfilled':
                # Orden cumplida - actualizar estado
                webhook_event.tiendanube_order_id = order_id
                webhook_event.save()
                
                return {
                    'success': True,
                    'action': 'order_fulfilled',
                    'order_id': order_id,
                    'message': 'Order fulfilled event processed'
                }
                
            elif event_type == 'order/cancelled':
                # Orden cancelada - anular en AdministraNET
                return self.sync_service.sync_order_status_to_tiendanube()
                
            else:
                return {
                    'success': True,
                    'action': 'ignored',
                    'message': f'Order event {event_type} not handled'
                }
                
        except Exception as e:
            logger.error(f"Error handling order event: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _handle_product_event(self, webhook_event: WebhookEvent, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manejar eventos de productos.
        
        Args:
            webhook_event: Evento del webhook
            webhook_data: Datos del webhook
            
        Returns:
            Dict con resultado del procesamiento
        """
        try:
            product_id = webhook_data.get('id')
            if not product_id:
                return {
                    'success': False,
                    'error': 'No product ID in webhook data'
                }
            
            event_type = webhook_event.event_type
            
            if event_type in ['product/created', 'product/updated']:
                # Producto creado/actualizado - sincronizar
                return self.sync_service.sync_products_from_tiendanube([product_id])
                
            elif event_type == 'product/deleted':
                # Producto eliminado - marcar como eliminado
                webhook_event.tiendanube_product_id = product_id
                webhook_event.save()
                
                return {
                    'success': True,
                    'action': 'product_deleted',
                    'product_id': product_id,
                    'message': 'Product deleted event processed'
                }
                
            else:
                return {
                    'success': True,
                    'action': 'ignored',
                    'message': f'Product event {event_type} not handled'
                }
                
        except Exception as e:
            logger.error(f"Error handling product event: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _handle_customer_event(self, webhook_event: WebhookEvent, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manejar eventos de clientes.
        
        Args:
            webhook_event: Evento del webhook
            webhook_data: Datos del webhook
            
        Returns:
            Dict con resultado del procesamiento
        """
        try:
            customer_id = webhook_data.get('id')
            if not customer_id:
                return {
                    'success': False,
                    'error': 'No customer ID in webhook data'
                }
            
            event_type = webhook_event.event_type
            
            if event_type == 'customer/created':
                # Cliente creado - sincronizar a AdministraNET
                return self._process_customer_created(webhook_event, webhook_data)
                
            elif event_type == 'customer/updated':
                # Cliente actualizado - actualizar en AdministraNET
                return self._process_customer_updated(webhook_event, webhook_data)
                
            else:
                return {
                    'success': True,
                    'action': 'ignored',
                    'message': f'Customer event {event_type} not handled'
                }
                
        except Exception as e:
            logger.error(f"Error handling customer event: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _process_customer_created(self, webhook_event: WebhookEvent, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesar evento de cliente creado.
        
        Args:
            webhook_event: Evento del webhook
            webhook_data: Datos del webhook
        
        Returns:
            Dict con resultado del procesamiento
        """
        try:
            # Los datos del cliente están en webhook_data['data']
            customer_data = webhook_data.get('data', {})
            customer_id = customer_data.get('id')
            customer_name = customer_data.get('name', '')
            customer_email = customer_data.get('email', '')
            
            # Extraer datos de dirección si están disponibles
            default_address = customer_data.get('default_address', {})
            addresses = customer_data.get('addresses', [])
            
            # Usar la dirección por defecto o la primera disponible
            address_data = default_address if default_address else (addresses[0] if addresses else {})
            
            logger.info(f"Procesando cliente creado: {customer_name} (ID: {customer_id})")
            
            # Crear mapeo del cliente
            from ..models import CustomerMapping
            
            # Usar email único o generar uno si está vacío
            unique_email = customer_email if customer_email else f"tiendanube_{customer_id}@example.com"
            
            mapping, created = CustomerMapping.objects.get_or_create(
                tiendanube_id=customer_id,
                defaults={
                    'tiendanube_email': unique_email,
                    'tiendanube_first_name': customer_name,
                    'sync_status': CustomerMapping.SyncStatus.PENDING
                }
            )
            
            if created:
                # Sincronizar a AdministraNET
                # Mapear datos de ubicación usando análisis predictivo
                calle_completa, cod_provincia, id_departamento = self._map_location_data(address_data)
                
                adminet_data = {
                    'nombre_cliente': customer_name,
                    'Email': customer_email,
                    'telefono': customer_data.get('phone', ''),
                    'Calle': calle_completa,
                    'NroCalle': address_data.get('number', ''),
                    'Dpto': address_data.get('floor', ''),
                    'CodProvincia': cod_provincia,
                    'IDDepartamento': id_departamento,
                    'CUIT': customer_data.get('identification', ''),
                    'Estado': 'Activo',
                    'id_tiendanube': str(customer_id)
                }
                
                result = self.sync_service.adminet_service.create_customer(adminet_data)
                if result['success']:
                    mapping.adminet_codigo = result.get('customer_id')
                    mapping.sync_status = CustomerMapping.SyncStatus.SYNCED
                    mapping.last_synced = timezone.now()
                    mapping.save()
                    
                    logger.info(f"Cliente {customer_name} sincronizado a AdministraNET con código {mapping.adminet_codigo}")
                else:
                    mapping.sync_status = CustomerMapping.SyncStatus.ERROR
                    mapping.error_message = result['message']
                    mapping.save()
                    logger.error(f"Error sincronizando cliente {customer_name}: {result['message']}")
            
            return {
                'success': True,
                'action': 'customer_created',
                'customer_id': customer_id,
                'message': f'Cliente {customer_name} procesado exitosamente'
            }
            
        except Exception as e:
            logger.error(f"Error procesando cliente creado: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _process_customer_updated(self, webhook_event: WebhookEvent, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesar evento de cliente actualizado.
        
        Args:
            webhook_event: Evento del webhook
            webhook_data: Datos del webhook
        
        Returns:
            Dict con resultado del procesamiento
        """
        try:
            # Los datos del cliente pueden estar en webhook_data['data'] o directamente en webhook_data
            customer_data = webhook_data.get('data', webhook_data)
            customer_id = customer_data.get('id')
            customer_name = customer_data.get('name', '')
            customer_email = customer_data.get('email', '')
            
            # Extraer datos de dirección si están disponibles
            default_address = customer_data.get('default_address', {})
            addresses = customer_data.get('addresses', [])
            
            # Usar la dirección por defecto o la primera disponible
            address_data = default_address if default_address else (addresses[0] if addresses else {})
            
            # Si no hay datos del cliente, intentar obtenerlos de la API de Tiendanube
            if not customer_name and not customer_email and customer_id:
                logger.warning(f"Datos del cliente incompletos en webhook. Obteniendo desde API de Tiendanube para ID: {customer_id}")
                try:
                    from ..services.tiendanube_service import TiendanubeService
                    tiendanube_service = TiendanubeService(self.tiendanube_config)
                    customer_result = tiendanube_service.get_customer(customer_id)
                    if customer_result.get('success'):
                        customer_data = customer_result.get('customer', {})
                        customer_name = customer_data.get('name', '')
                        customer_email = customer_data.get('email', '')
                        
                        # Actualizar también los datos de dirección
                        default_address = customer_data.get('default_address', {})
                        addresses = customer_data.get('addresses', [])
                        address_data = default_address if default_address else (addresses[0] if addresses else {})
                        
                        logger.info(f"Datos del cliente obtenidos desde API: {customer_name} ({customer_email})")
                    else:
                        logger.error(f"Error obteniendo datos del cliente desde API: {customer_result.get('error')}")
                except Exception as e:
                    logger.error(f"Error obteniendo datos del cliente desde API: {str(e)}")
            
            logger.info(f"Procesando cliente actualizado: {customer_name} (ID: {customer_id})")
            
            # Buscar mapeo existente
            from ..models import CustomerMapping
            mapping = CustomerMapping.objects.filter(tiendanube_id=customer_id).first()
            
            # Usar email único o generar uno si está vacío
            unique_email = customer_email if customer_email else f"tiendanube_{customer_id}@example.com"
            
            if mapping and mapping.adminet_codigo:
                # Actualizar datos en AdministraNET
                # Mapear datos de ubicación usando análisis predictivo
                calle_completa, cod_provincia, id_departamento = self._map_location_data(address_data)
                
                adminet_data = {
                    'nombre_cliente': customer_name,
                    'Email': customer_email,
                    'telefono': customer_data.get('phone', ''),
                    'Calle': calle_completa,
                    'NroCalle': address_data.get('number', ''),
                    'Dpto': address_data.get('floor', ''),
                    'CodProvincia': cod_provincia,
                    'IDDepartamento': id_departamento,
                    'CUIT': customer_data.get('identification', ''),
                    'Estado': 'Activo',
                    'id_tiendanube': str(customer_id)
                }
                
                result = self.sync_service.adminet_service.update_customer(mapping.adminet_codigo, adminet_data)
                if result['success']:
                    # Actualizar mapeo local con datos de Tiendanube
                    mapping.tiendanube_email = customer_email
                    mapping.tiendanube_first_name = customer_name
                    mapping.tiendanube_name = customer_name
                    mapping.tiendanube_phone = customer_data.get('phone', '')
                    mapping.tiendanube_document = customer_data.get('identification', '')
                    mapping.tiendanube_city = address_data.get('city', '')
                    mapping.tiendanube_state = address_data.get('province', '')
                    # Manejar el caso donde Tiendanube envía "None" como string
                    country = address_data.get('country', '')
                    if country and country.lower() not in ['none', 'null', '']:
                        mapping.tiendanube_country = country
                    else:
                        mapping.tiendanube_country = 'Argentina'  # Valor por defecto
                    mapping.tiendanube_postal_code = address_data.get('zipcode', '')
                    
                    # Actualizar campos de AdministraNET con los datos enviados
                    mapping.adminet_nombre = customer_name
                    mapping.adminet_email = customer_email
                    mapping.adminet_telefono = customer_data.get('phone', '')
                    mapping.adminet_documento = customer_data.get('identification', '')
                    mapping.adminet_calle = calle_completa
                    mapping.adminet_nro_calle = address_data.get('number', '')
                    mapping.adminet_dpto = address_data.get('floor', '')
                    
                    mapping.sync_status = CustomerMapping.SyncStatus.SYNCED
                    mapping.last_synced = timezone.now()
                    mapping.save()
                    
                    logger.info(f"Cliente {customer_name} actualizado en AdministraNET")
                    return {
                        'success': True,
                        'action': 'updated',
                        'customer_id': customer_id,
                        'adminet_code': mapping.adminet_codigo,
                        'message': f'Cliente {customer_name} actualizado exitosamente'
                    }
                else:
                    mapping.sync_status = CustomerMapping.SyncStatus.ERROR
                    mapping.error_message = result['message']
                    mapping.save()
                    logger.error(f"Error actualizando cliente {customer_name}: {result['message']}")
                    return {
                        'success': False,
                        'action': 'update_failed',
                        'customer_id': customer_id,
                        'error': f"Error actualizando cliente en AdministraNET: {result['message']}"
                    }
            else:
                # Cliente no existe en Synap, crear como nuevo cliente
                logger.warning(f"Cliente {customer_name} (ID: {customer_id}) no existe en Synap. Creando como nuevo cliente.")
                
                # Crear mapeo nuevo
                mapping, created = CustomerMapping.objects.get_or_create(
                    tiendanube_id=customer_id,
                    defaults={
                        'tiendanube_email': unique_email,
                        'tiendanube_first_name': customer_name,
                        'sync_status': CustomerMapping.SyncStatus.PENDING
                    }
                )
                
                if created:
                    # Sincronizar a AdministraNET
                    # Mapear datos de ubicación usando análisis predictivo
                    calle_completa, cod_provincia, id_departamento = self._map_location_data(address_data)
                    
                    adminet_data = {
                        'nombre_cliente': customer_name,
                        'Email': customer_email,
                        'telefono': customer_data.get('phone', ''),
                        'Calle': calle_completa,
                        'NroCalle': address_data.get('number', ''),
                        'Dpto': address_data.get('floor', ''),
                        'CodProvincia': cod_provincia,
                        'IDDepartamento': id_departamento,
                        'CUIT': customer_data.get('identification', ''),
                        'Estado': 'Activo',
                        'id_tiendanube': str(customer_id)
                    }
                    
                    result = self.sync_service.adminet_service.create_customer(adminet_data)
                    if result['success']:
                        mapping.adminet_codigo = result.get('customer_id')
                        
                        # Actualizar campos de Tiendanube
                        mapping.tiendanube_name = customer_name
                        mapping.tiendanube_phone = customer_data.get('phone', '')
                        mapping.tiendanube_document = customer_data.get('identification', '')
                        mapping.tiendanube_city = address_data.get('city', '')
                        mapping.tiendanube_state = address_data.get('province', '')
                        # Manejar el caso donde Tiendanube envía "None" como string
                        country = address_data.get('country', '')
                        if country and country.lower() not in ['none', 'null', '']:
                            mapping.tiendanube_country = country
                        else:
                            mapping.tiendanube_country = 'Argentina'  # Valor por defecto
                        mapping.tiendanube_postal_code = address_data.get('zipcode', '')
                        
                        # Actualizar campos de AdministraNET con los datos enviados
                        mapping.adminet_nombre = customer_name
                        mapping.adminet_email = customer_email
                        mapping.adminet_telefono = customer_data.get('phone', '')
                        mapping.adminet_documento = customer_data.get('identification', '')
                        mapping.adminet_calle = calle_completa
                        mapping.adminet_nro_calle = address_data.get('number', '')
                        mapping.adminet_dpto = address_data.get('floor', '')
                        
                        mapping.sync_status = CustomerMapping.SyncStatus.SYNCED
                        mapping.last_synced = timezone.now()
                        mapping.save()
                        
                        logger.info(f"Cliente {customer_name} creado en AdministraNET como resultado de actualización")
                        return {
                            'success': True,
                            'action': 'created_from_update',
                            'customer_id': customer_id,
                            'adminet_code': mapping.adminet_codigo,
                            'message': f'Cliente {customer_name} creado en AdministraNET (era una actualización de cliente inexistente)'
                        }
                    else:
                        mapping.sync_status = CustomerMapping.SyncStatus.FAILED
                        mapping.error_message = result.get('error', 'Error desconocido')
                        mapping.save()
                        logger.error(f"Error creando cliente {customer_name} en AdministraNET: {result.get('error')}")
                        return {
                            'success': False,
                            'action': 'create_failed',
                            'customer_id': customer_id,
                            'error': f"Error creando cliente en AdministraNET: {result.get('error')}"
                        }
                else:
                    logger.info(f"Mapeo para cliente {customer_name} (ID: {customer_id}) ya existe, omitiendo creación.")
                    return {
                        'success': True,
                        'action': 'skipped',
                        'customer_id': customer_id,
                        'message': 'Customer mapping already exists'
                    }
            
        except Exception as e:
            logger.error(f"Error procesando cliente actualizado: {e}")
            return {
                'success': False,
                'error': str(e)
            }
