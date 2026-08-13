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
from ..models import AdministraNETConfig, WebhookConfig, WebhookDeliveryLog, WebhookEvent
from .sync_errors import should_retry_webhook_failure
from .tiendanube_service import NUVEMSHOP_API_VERSION
from .rate_limit import wait_for_rate_limit

logger = logging.getLogger(__name__)


class WebhookService:
    """
    Cliente HTTP para la API de Webhooks Nuvemshop / Tienda Nube (versión documentada 2025-03).

    Prefijo de todas las peticiones:
    ``https://api.tiendanube.com/{version}/{store_id}/...``
    (Brasil: ``https://api.nuvemshop.com.br/...`` si se amplía soporte regional).
    """

    def __init__(self, tiendanube_config):
        self.tiendanube_config = tiendanube_config
        self.headers = {
            'Authentication': f'bearer {tiendanube_config.access_token}',
            'Content-Type': 'application/json; charset=utf-8',
            'User-Agent': 'Synap TiendaNube (soporte@administranet.com.ar)',
        }

    def _api_prefix(self) -> str:
        """Base ``.../2025-03/{store_id}`` según documentación oficial."""
        return (
            f'https://api.tiendanube.com/{NUVEMSHOP_API_VERSION}/'
            f'{self.tiendanube_config.store_id}'
        )

    def _webhooks_collection_url(self) -> str:
        return f'{self._api_prefix()}/webhooks'

    def _webhook_detail_url(self, webhook_id: int) -> str:
        return f'{self._webhooks_collection_url()}/{webhook_id}'

    def _request(self, method: str, url: str, **kwargs):
        wait_for_rate_limit()
        kwargs.setdefault('headers', self.headers)
        return requests.request(method, url, **kwargs)
    
    def ensure_webhooks_configured(self) -> Dict[str, Any]:
        """
        Asegurar que los webhooks estén configurados automáticamente.
        Se ejecuta la primera vez que se usa el sistema.
        
        Returns:
            Dict con el resultado de la configuración
        """
        try:
            logger.info("Verificando configuración automática de webhooks...")
            
            # Obtener webhooks existentes
            existing_result = self.get_webhooks()
            if not existing_result['success']:
                return {
                    'success': False,
                    'message': f'Error obteniendo webhooks existentes: {existing_result.get("error")}'
                }
            
            existing_webhooks = existing_result.get('webhooks', [])
            existing_events = [wh.get('event') for wh in existing_webhooks]
            
            # Eventos requeridos
            required_events = [
                'order/created',
                'order/paid',
                'order/updated', 
                'order/fulfilled',
                'order/cancelled',
                'customer/created',
                'customer/updated'
            ]
            
            # URL del webhook (construir desde la configuración)
            webhook_url = self._get_webhook_url()
            
            created_webhooks = []
            skipped_webhooks = []
            
            for event in required_events:
                if event in existing_events:
                    logger.info(f"Webhook {event} ya existe, omitiendo...")
                    skipped_webhooks.append(event)
                    continue
                
                # Crear webhook faltante
                webhook_data = {
                    'webhook_url': webhook_url,
                    'events': [event],
                    'description': f'Webhook automático para {event} - Synap AdministraNET'
                }
                
                result = self.create_webhook(webhook_data)
                if result['success']:
                    logger.info(f"✅ Webhook {event} creado automáticamente")
                    created_webhooks.append(event)
                else:
                    logger.error(f"❌ Error creando webhook {event}: {result.get('error')}")
            
            return {
                'success': True,
                'message': f'Configuración de webhooks completada',
                'created': created_webhooks,
                'skipped': skipped_webhooks,
                'total_required': len(required_events),
                'webhook_url': webhook_url
            }
            
        except Exception as e:
            logger.error(f"Error en configuración automática de webhooks: {e}")
            return {
                'success': False,
                'message': f'Error configurando webhooks automáticamente: {str(e)}'
            }
    
    def _get_webhook_url(self) -> str:
        """
        Construir la URL del webhook basada en la configuración.
        
        Returns:
            URL completa del webhook
        """
        from django.conf import settings
        
        # Intentar obtener la URL base de la configuración
        try:
            # 1. Prioridad: TIENDANUBE_WEBHOOK_BASE_URL específico
            if hasattr(settings, 'TIENDANUBE_WEBHOOK_BASE_URL'):
                base_url = settings.TIENDANUBE_WEBHOOK_BASE_URL
                logger.info(f"Usando TIENDANUBE_WEBHOOK_BASE_URL: {base_url}")
            
            # 2. Prioridad: SITE_URL del settings
            elif hasattr(settings, 'SITE_URL') and settings.SITE_URL != 'https://tudominio.com':
                base_url = settings.SITE_URL
                logger.info(f"Usando SITE_URL: {base_url}")
            
            # 3. Fallback: Construir desde ALLOWED_HOSTS
            else:
                allowed_hosts = getattr(settings, 'ALLOWED_HOSTS', [])
                if allowed_hosts and allowed_hosts[0] != '*':
                    host = allowed_hosts[0]
                    if not host.startswith('http'):
                        base_url = f"https://{host}"
                    else:
                        base_url = host
                    logger.info(f"Usando ALLOWED_HOSTS[0]: {base_url}")
                else:
                    # Fallback para desarrollo
                    base_url = "https://synap.administranet.com.ar"
                    logger.info(f"Usando fallback: {base_url}")
            
            webhook_url = f"{base_url.rstrip('/')}/tiendanube_administranet/webhook/"
            logger.info(f"URL final del webhook: {webhook_url}")
            return webhook_url
            
        except Exception as e:
            logger.warning(f"Error construyendo URL del webhook: {e}")
            # Fallback
            return "https://synap.administranet.com.ar/tiendanube_administranet/webhook/"
    
    def create_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crear webhook en Tiendanube.
        
        Args:
            webhook_data: Datos del webhook a crear
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            url = self._webhooks_collection_url()
            
            # Un registro por evento; cuerpo: url + event (snake_case)
            event = webhook_data.get('event')
            if not event:
                ev = webhook_data.get('events') or ['order/paid']
                event = ev[0] if isinstance(ev, list) and ev else 'order/paid'
            
            webhook_payload = {
                "url": webhook_data['webhook_url'],
                "event": event,
            }
            
            logger.info(f"Creating webhook for event {event}: {webhook_payload['url']}")
            response = self._request('POST', url, json=webhook_payload, timeout=30)
            
            if response.status_code in [200, 201]:
                webhook_response = response.json()
                logger.info(f"Webhook created successfully: {webhook_response.get('id')}")
                
                return {
                    'success': True,
                    'webhook_id': webhook_response.get('id'),
                    'webhook_data': webhook_response,
                    'event': event,
                    'message': f'Webhook {event} created successfully'
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
            url = self._webhooks_collection_url()
            response = self._request('GET', url, timeout=30)
            
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
            url = self._webhook_detail_url(webhook_id)
            response = self._request('GET', url, timeout=30)
            
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
            url = self._webhook_detail_url(webhook_id)
            
            event = webhook_data.get('event')
            if not event:
                ev = webhook_data.get('events') or []
                event = ev[0] if ev else None
            if not event:
                return {
                    'success': False,
                    'error': 'Se requiere el campo event (o events[0]) para actualizar el webhook',
                }
            
            webhook_payload = {
                'url': webhook_data['webhook_url'],
                'event': event,
            }
            
            logger.info(f"Updating webhook {webhook_id}")
            response = self._request('PUT', url, json=webhook_payload, timeout=30)
            
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
    
    def toggle_webhook_status(self, webhook_id: int, active: bool) -> Dict[str, Any]:
        """
        La API 2025-03 no expone estado activo/inactivo en el recurso Webhook.
        Se reenvía PUT con la misma ``url`` y ``event`` (revalidación).
        El parámetro ``active`` se conserva por compatibilidad con la UI local.
        """
        try:
            _ = active  # La plataforma no permite toggle remoto vía este método
            # Obtener todos los webhooks para encontrar el correcto
            webhooks_result = self.get_webhooks()
            if not webhooks_result.get('success'):
                return {
                    'success': False,
                    'message': f'Error getting webhooks: {webhooks_result.get("message")}'
                }
            
            webhooks = webhooks_result.get('webhooks', [])
            target_webhook = None
            
            # Buscar el webhook específico
            for webhook in webhooks:
                if webhook.get('id') == webhook_id:
                    target_webhook = webhook
                    break
            
            if not target_webhook:
                return {
                    'success': False,
                    'message': f'Webhook {webhook_id} not found in Tiendanube'
                }
            
            # La API 2025-03 no expone "activo"; solo url y event. El toggle local
            # no puede suspender el webhook en la plataforma sin DELETE.
            update_data = {
                'webhook_url': target_webhook.get('url', ''),
                'event': target_webhook.get('event'),
                'events': [target_webhook['event']] if target_webhook.get('event') else [],
            }
            
            # Actualizar webhook
            return self.update_webhook(webhook_id, update_data)
            
        except Exception as e:
            error_msg = f"Exception toggling webhook {webhook_id}: {str(e)}"
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
            url = self._webhook_detail_url(webhook_id)
            
            logger.info(f"Deleting webhook {webhook_id}")
            response = self._request('DELETE', url, timeout=30)
            
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
        La API 2025-03 no define ``POST /webhooks/{id}/test``.
        Se verifica el registro con ``GET /webhooks/{id}`` (misma URL que usa la UI).
        """
        try:
            logger.info(f"Verificando webhook {webhook_id} vía GET /webhooks/{{id}}")
            result = self.get_webhook(webhook_id)
            if result.get('success'):
                return {
                    'success': True,
                    'message': (
                        'Webhook registrado en Tienda Nube (GET /webhooks/{id} correcto). '
                        'Para una prueba real, genere el evento en la tienda o use una URL '
                        'pública de prueba (p. ej. RequestCatcher).'
                    ),
                    'webhook': result.get('webhook'),
                }
            return result
        except Exception as e:
            error_msg = f"Exception testing webhook {webhook_id}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }


class WebhookProcessor:
    """
    Procesador canónico de eventos webhook TN → AdministraNET.

    Auditoría vs ``webhook_processor.py`` (legacy, eliminado en fase 2):
    - **order/***: el canónico ya tenía pipeline completo (enrich→REC→comp_ped→stock);
      el legacy usaba ``sync_orders_from_tiendanube`` (incompleto).
    - **product/***: portado de legacy — ``sync_products_from_tiendanube`` en
      ``product/created`` y ``product/updated`` además del mapeo local.
    - **customer/***: portado de legacy — ``LocationMapper``, payload Adminet
      normalizado, ``create_customer``/``update_customer``, fallback API TN en
      ``customer/updated`` con datos incompletos.
    """
    
    @staticmethod
    def verify_hmac_signature(payload: str, signature: str, secret: str) -> bool:
        """Verifica HMAC según documentación Nuvemshop (hex SHA256 del body)."""
        try:
            if not secret:
                return False
            expected = hmac.new(
                secret.encode('utf-8'),
                payload.encode('utf-8') if isinstance(payload, str) else payload,
                hashlib.sha256,
            ).hexdigest()
            sig = (signature or '').strip()
            if sig.startswith('sha256='):
                sig = sig[7:]
            return hmac.compare_digest(expected, sig)
        except Exception as e:
            logger.error("Error verificando HMAC webhook: %s", e)
            return False

    @staticmethod
    def verify_signature(payload: str, signature: str, secret: str) -> bool:
        """Alias compatible con endpoint legacy."""
        return WebhookProcessor.verify_hmac_signature(payload, signature, secret)
    
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
                retry = should_retry_webhook_failure(
                    http_status=result.get('status_code'),
                )
                webhook_event.mark_failed(result['error'], retry=retry)
                logger.error(f"Webhook event {event_id} failed: {result['error']}")
            
            # Actualizar último trigger del webhook
            webhook_config.last_triggered = timezone.now()
            webhook_config.save(update_fields=['last_triggered'])
            
            return result
            
        except Exception as e:
            error_msg = f"Error processing webhook event: {str(e)}"
            logger.error(error_msg)
            
            if 'webhook_event' in locals():
                webhook_event.mark_failed(
                    error_msg,
                    retry=should_retry_webhook_failure(exc=e),
                )
            
            return {
                'success': False,
                'error': error_msg
            }

    @staticmethod
    def process_stored_webhook_event(webhook_event: WebhookEvent) -> Dict[str, Any]:
        """
        Procesar un WebhookEvent ya persistido (inbox worker / drenaje retry).

        No crea un registro nuevo; reutiliza payload y headers almacenados.
        """
        event_data = webhook_event.payload or {}
        event_id = webhook_event.event_id
        try:
            webhook_event.mark_processing()
            logger.info(
                "Processing stored webhook event: %s - %s",
                webhook_event.event_type,
                event_id,
            )

            result = WebhookProcessor._handle_event_by_type(webhook_event, event_data)

            if result['success']:
                webhook_event.mark_completed(result)
                logger.info("Stored webhook event %s processed successfully", event_id)
            else:
                retry = should_retry_webhook_failure(
                    http_status=result.get('status_code'),
                )
                webhook_event.mark_failed(result['error'], retry=retry)
                logger.error(
                    "Stored webhook event %s failed: %s",
                    event_id,
                    result['error'],
                )

            webhook_config = webhook_event.webhook_config
            webhook_config.last_triggered = timezone.now()
            webhook_config.save(update_fields=['last_triggered'])

            return result

        except Exception as e:
            error_msg = f"Error processing stored webhook event: {str(e)}"
            logger.error(error_msg)
            webhook_event.mark_failed(
                error_msg,
                retry=should_retry_webhook_failure(exc=e),
            )
            return {
                'success': False,
                'error': error_msg,
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
    def _map_location_data(adminet_config, address_data: Dict[str, Any]) -> Tuple[str, int, int]:
        """Mapear dirección TN → calle, provincia y departamento AdministraNET."""
        from .location_mapper import LocationMapper

        street = address_data.get('address', '')
        number = address_data.get('number', '')
        floor = address_data.get('floor', '')
        locality = address_data.get('locality', '')
        city = address_data.get('city', '')
        province = address_data.get('province', '')

        location_mapper = LocationMapper(adminet_config)
        cod_provincia, id_departamento, _location_info = location_mapper.map_location(
            province, city,
        )
        calle_completa = location_mapper.build_complete_address(
            street, number, floor, locality, city, province,
        )

        if cod_provincia is None:
            cod_provincia = 1
            logger.warning(
                "Provincia '%s' no encontrada, usando Buenos Aires (1) como default",
                province,
            )
        if id_departamento is None:
            logger.warning("Ciudad '%s' no encontrada en provincia %s", city, cod_provincia)

        return calle_completa, cod_provincia, id_departamento

    @staticmethod
    def _build_adminet_customer_payload(
        customer_name: str,
        customer_email: str,
        customer_data: Dict[str, Any],
        address_data: Dict[str, Any],
        calle_completa: str,
        cod_provincia,
        id_departamento,
        customer_id,
    ) -> Dict[str, Any]:
        from .customer_payload import normalize_adminet_customer_payload

        return normalize_adminet_customer_payload({
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
            'id_tiendanube': customer_id,
        })

    @staticmethod
    def _process_customer_created(
        sync_service,
        adminet_config,
        customer_id,
        customer_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        from ..models import CustomerMapping

        customer_name = customer_data.get('name', '')
        customer_email = customer_data.get('email', '')
        default_address = customer_data.get('default_address', {})
        addresses = customer_data.get('addresses', [])
        address_data = default_address if default_address else (addresses[0] if addresses else {})

        unique_email = customer_email if customer_email else None
        if not unique_email:
            logger.warning(
                "Cliente Tienda Nube %s sin email; no se creará email ficticio",
                customer_id,
            )
            return {'success': False, 'error': 'Cliente sin email'}

        mapping, created = CustomerMapping.objects.get_or_create(
            tiendanube_id=customer_id,
            defaults={
                'tiendanube_email': unique_email,
                'tiendanube_first_name': customer_name,
                'sync_status': CustomerMapping.SyncStatus.PENDING,
            },
        )

        if created:
            calle_completa, cod_provincia, id_departamento = WebhookProcessor._map_location_data(
                adminet_config, address_data,
            )
            adminet_data = WebhookProcessor._build_adminet_customer_payload(
                customer_name, customer_email, customer_data, address_data,
                calle_completa, cod_provincia, id_departamento, customer_id,
            )
            result = sync_service.adminet_service.create_customer(adminet_data)
            if result['success']:
                mapping.adminet_codigo = result.get('customer_id')
                mapping.sync_status = CustomerMapping.SyncStatus.SYNCED
                mapping.last_synced = timezone.now()
                mapping.save()
            else:
                mapping.sync_status = CustomerMapping.SyncStatus.ERROR
                mapping.error_message = result['message']
                mapping.save()
                return {
                    'success': False,
                    'error': result['message'],
                }

        return {
            'success': True,
            'action': 'customer_created',
            'customer_id': customer_id,
            'message': f'Cliente {customer_name} procesado exitosamente',
        }

    @staticmethod
    def _process_customer_updated(
        sync_service,
        adminet_config,
        tiendanube_config,
        customer_id,
        customer_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        from ..models import CustomerMapping

        customer_name = customer_data.get('name', '')
        customer_email = customer_data.get('email', '')
        default_address = customer_data.get('default_address', {})
        addresses = customer_data.get('addresses', [])
        address_data = default_address if default_address else (addresses[0] if addresses else {})

        if not customer_name and not customer_email and customer_id:
            logger.warning(
                "Datos del cliente incompletos en webhook. Obteniendo desde API TN ID: %s",
                customer_id,
            )
            try:
                from .tiendanube_service import TiendanubeService

                tn_service = TiendanubeService(tiendanube_config)
                customer_result = tn_service.get_customer(customer_id)
                if customer_result.get('success'):
                    customer_data = customer_result.get('customer', {})
                    customer_name = customer_data.get('name', '')
                    customer_email = customer_data.get('email', '')
                    default_address = customer_data.get('default_address', {})
                    addresses = customer_data.get('addresses', [])
                    address_data = default_address if default_address else (
                        addresses[0] if addresses else {}
                    )
                else:
                    logger.error(
                        "Error obteniendo cliente desde API TN: %s",
                        customer_result.get('error'),
                    )
            except Exception as exc:
                logger.error("Error obteniendo cliente desde API TN: %s", exc)

        mapping = CustomerMapping.objects.filter(tiendanube_id=customer_id).first()
        unique_email = customer_email if customer_email else None
        if not unique_email:
            return {'success': False, 'error': 'Cliente sin email'}

        if mapping and mapping.adminet_codigo:
            calle_completa, cod_provincia, id_departamento = WebhookProcessor._map_location_data(
                adminet_config, address_data,
            )
            adminet_data = WebhookProcessor._build_adminet_customer_payload(
                customer_name, customer_email, customer_data, address_data,
                calle_completa, cod_provincia, id_departamento, customer_id,
            )
            result = sync_service.adminet_service.update_customer(
                mapping.adminet_codigo, adminet_data,
            )
            if result['success']:
                mapping.tiendanube_email = customer_email
                mapping.tiendanube_first_name = customer_name
                mapping.tiendanube_name = customer_name
                mapping.tiendanube_phone = customer_data.get('phone', '')
                mapping.tiendanube_document = customer_data.get('identification', '')
                mapping.tiendanube_city = address_data.get('city', '')
                mapping.tiendanube_state = address_data.get('province', '')
                country = address_data.get('country', '')
                mapping.tiendanube_country = (
                    country if country and country.lower() not in ('none', 'null', '') else 'Argentina'
                )
                mapping.tiendanube_postal_code = address_data.get('zipcode', '')
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
                return {
                    'success': True,
                    'action': 'updated',
                    'customer_id': customer_id,
                    'adminet_code': mapping.adminet_codigo,
                }

            mapping.sync_status = CustomerMapping.SyncStatus.ERROR
            mapping.error_message = result['message']
            mapping.save()
            return {
                'success': False,
                'action': 'update_failed',
                'customer_id': customer_id,
                'error': f"Error actualizando cliente en AdministraNET: {result['message']}",
            }

        mapping, created = CustomerMapping.objects.get_or_create(
            tiendanube_id=customer_id,
            defaults={
                'tiendanube_email': unique_email,
                'tiendanube_first_name': customer_name,
                'sync_status': CustomerMapping.SyncStatus.PENDING,
            },
        )
        if not created:
            return {
                'success': True,
                'action': 'skipped',
                'customer_id': customer_id,
                'message': 'Customer mapping already exists',
            }

        calle_completa, cod_provincia, id_departamento = WebhookProcessor._map_location_data(
            adminet_config, address_data,
        )
        adminet_data = WebhookProcessor._build_adminet_customer_payload(
            customer_name, customer_email, customer_data, address_data,
            calle_completa, cod_provincia, id_departamento, customer_id,
        )
        result = sync_service.adminet_service.create_customer(adminet_data)
        if result['success']:
            mapping.adminet_codigo = result.get('customer_id')
            mapping.tiendanube_name = customer_name
            mapping.tiendanube_phone = customer_data.get('phone', '')
            mapping.tiendanube_document = customer_data.get('identification', '')
            mapping.tiendanube_city = address_data.get('city', '')
            mapping.tiendanube_state = address_data.get('province', '')
            country = address_data.get('country', '')
            mapping.tiendanube_country = (
                country if country and country.lower() not in ('none', 'null', '') else 'Argentina'
            )
            mapping.tiendanube_postal_code = address_data.get('zipcode', '')
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
            return {
                'success': True,
                'action': 'created_from_update',
                'customer_id': customer_id,
                'adminet_code': mapping.adminet_codigo,
            }

        mapping.sync_status = CustomerMapping.SyncStatus.FAILED
        mapping.error_message = result.get('error', 'Error desconocido')
        mapping.save()
        return {
            'success': False,
            'action': 'create_failed',
            'customer_id': customer_id,
            'error': f"Error creando cliente en AdministraNET: {result.get('error')}",
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
            adminet_config = AdministraNETConfig.objects.filter(is_active=True).first()
            
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

                sync_result = sync_service.sync_products_from_tiendanube([product_id])
                if not sync_result.get('success'):
                    return {
                        'success': False,
                        'error': sync_result.get('message') or sync_result.get('error', 'Sync failed'),
                    }
                
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

                    sync_result = sync_service.sync_products_from_tiendanube([product_id])
                    if not sync_result.get('success'):
                        return {
                            'success': False,
                            'error': sync_result.get('message') or sync_result.get('error', 'Sync failed'),
                        }
                    
                    return {
                        'success': True,
                        'action': 'product_updated',
                        'product_id': product_id
                    }
                except ProductMapping.DoesNotExist:
                    sync_result = sync_service.sync_products_from_tiendanube([product_id])
                    if sync_result.get('success'):
                        return {
                            'success': True,
                            'action': 'product_updated',
                            'product_id': product_id,
                            'mapping_created': True,
                        }
                    return {
                        'success': False,
                        'error': f'Product mapping not found for ID {product_id}',
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
            adminet_config = AdministraNETConfig.objects.filter(is_active=True).first()
            
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
                from ..services.order_customer import (
                    enrich_order_from_api,
                    resolve_adminet_customer_id,
                )
                from ..services.order_payment import parse_tiendanube_order_payment
                from ..services.order_stock_push import push_stock_for_article_ids

                order_data = enrich_order_from_api(sync_service, order_id, order_data)
                payment_parsed = parse_tiendanube_order_payment(order_data)

                # Crear o actualizar mapeo
                mapping, created = OrderMapping.objects.get_or_create(
                    tiendanube_id=order_id,
                    defaults={
                        'tiendanube_number': order_data.get('number', ''),
                        'tiendanube_status': order_data.get('status', ''),
                        'tiendanube_total': order_data.get('total', 0),
                        'tiendanube_customer_email': order_data.get('customer', {}).get('email', ''),
                        'tiendanube_payment_status': order_data.get('payment_status', ''),
                        'tiendanube_payment_method': payment_parsed.method_label,
                        'sync_status': OrderMapping.SyncStatus.PENDING
                    }
                )

                mapping.tiendanube_payment_status = order_data.get('payment_status', '')
                mapping.tiendanube_payment_method = payment_parsed.method_label
                mapping.tiendanube_total = order_data.get('total', mapping.tiendanube_total)
                mapping.save(
                    update_fields=[
                        'tiendanube_payment_status',
                        'tiendanube_payment_method',
                        'tiendanube_total',
                        'updated_at',
                    ]
                )

                # Si aún no se creó en AdministraNET, crearlo ahora
                if not mapping.adminet_codigo:
                    deposito_id = adminet_config.deposito_tiendanube_id or 1
                    punto_venta_id = (
                        adminet_config.punto_venta_tiendanube_id or 1
                    )
                    sucursal_id = adminet_config.sucursal_tiendanube_id or 1
                    user_id = 1

                    order_data_for_adminet = {
                        'id': order_id,
                        'number': order_data.get('number'),
                        'customer': order_data.get('customer', {}),
                        'shipping_address': order_data.get('shipping_address', {}),
                        'shipping': order_data.get('shipping', {}),
                        'payment': order_data.get('payment', {}),
                        'payment_details': order_data.get('payment_details', {}),
                        'gateway': order_data.get('gateway'),
                        'gateway_id': order_data.get('gateway_id'),
                        'gateway_name': order_data.get('gateway_name'),
                        'gateway_method': order_data.get('gateway_method'),
                        'paid_at': order_data.get('paid_at'),
                        'products': order_data.get('products', []),
                        'subtotal': order_data.get('subtotal', 0),
                        'total': order_data.get('total', 0),
                        'discount': order_data.get('discount', 0),
                        'shipping_cost': order_data.get('shipping_cost', 0),
                        'payment_status': order_data.get('payment_status', 'paid'),
                        'created_at': order_data.get('created_at', ''),
                        'updated_at': order_data.get('updated_at', ''),
                        'adminet_customer_id': resolve_adminet_customer_id(
                            sync_service,
                            order_data.get('customer', {}),
                        ),
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
                            logger.warning(
                                'Producto %s no mapeado en orden %s',
                                product.get('product_id'),
                                order_id,
                            )

                    result = sync_service.adminet_service.create_order_from_tiendanube(
                        order_data_for_adminet,
                        deposito_id=deposito_id,
                        user_id=user_id,
                        punto_venta_id=punto_venta_id,
                        sucursal_id=sucursal_id,
                        registrar_adelanto=True,
                    )

                    if result['success']:
                        mapping.adminet_codigo = str(result['codigo_movimiento'])
                        mapping.adminet_numero = result['nro_comprobante']
                        from .adminet_service import ESTADO_PEDIDO_ECOM_TN

                        mapping.adminet_estado = result.get('estado', ESTADO_PEDIDO_ECOM_TN)
                        mapping.sync_status = OrderMapping.SyncStatus.SYNCED
                        mapping.last_synced = timezone.now()
                        mapping.save()

                        stock_push = push_stock_for_article_ids(
                            sync_service,
                            result.get('affected_article_ids') or [],
                            deposito_id,
                        )

                        logger.info(
                            'Orden %s creada en AdministraNET: %s (adelanto: %s, stock push: %s)',
                            order_id,
                            result['nro_comprobante'],
                            result.get('adelanto', {}).get('nro_recibo'),
                            stock_push.get('pushed', 0),
                        )

                        return {
                            'success': True,
                            'action': 'order_paid_and_created',
                            'order_id': order_id,
                            'adminet_nro': result['nro_comprobante'],
                            'adminet_codigo': result['codigo_movimiento'],
                            'adelanto': result.get('adelanto'),
                            'stock_push': stock_push,
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
        """Manejar eventos de clientes (mapeo + sync AdministraNET enriquecido)."""
        try:
            customer_data = event_data.get('data', {})
            customer_id = customer_data.get('id')

            tiendanube_config = webhook_event.webhook_config.tiendanube_config
            adminet_config = AdministraNETConfig.objects.filter(is_active=True).first()

            if not adminet_config:
                return {
                    'success': False,
                    'error': 'No active AdministraNET configuration found'
                }

            from ..services.sync_service import TiendanubeAdministraNETSyncService
            sync_service = TiendanubeAdministraNETSyncService(tiendanube_config, adminet_config)

            if webhook_event.event_type == 'customer/created':
                return WebhookProcessor._process_customer_created(
                    sync_service, adminet_config, customer_id, customer_data,
                )

            if webhook_event.event_type == 'customer/updated':
                return WebhookProcessor._process_customer_updated(
                    sync_service, adminet_config, tiendanube_config, customer_id, customer_data,
                )

            if webhook_event.event_type == 'customer/deleted':
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