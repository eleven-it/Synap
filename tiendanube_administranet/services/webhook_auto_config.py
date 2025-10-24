"""
Servicio para configuración automática de webhooks de TiendaNube.
"""

import requests
import logging
from typing import Dict, List, Any
from django.conf import settings

logger = logging.getLogger(__name__)


class WebhookAutoConfig:
    """
    Servicio para configurar automáticamente webhooks de TiendaNube.
    """
    
    def __init__(self, tiendanube_config):
        self.tiendanube_config = tiendanube_config
        self.base_url = f"https://api.tiendanube.com/v1/{tiendanube_config.store_id}/webhooks"
        self.headers = {
            'Authentication': f'bearer {tiendanube_config.access_token}',
            'Content-Type': 'application/json',
            'User-Agent': 'AdministraNET (soporte@administranet.com.ar)'
        }
    
    def get_webhook_base_url(self) -> str:
        """
        Obtener la URL base para webhooks.
        
        Returns:
            URL base para webhooks
        """
        # Usar SITE_URL desde settings
        site_url = getattr(settings, 'SITE_URL', None)
        if site_url:
            return site_url
        
        # Construir desde ALLOWED_HOSTS como fallback
        allowed_hosts = getattr(settings, 'ALLOWED_HOSTS', [])
        if allowed_hosts and allowed_hosts[0] != '*':
            host = allowed_hosts[0]
            if not host.startswith('http'):
                return f"https://{host}"
            return host
        
        # Fallback para desarrollo
        return "https://api.administranet.com"
    
    def get_valid_events(self) -> List[str]:
        """
        Obtener lista de eventos válidos en TiendaNube.
        
        Returns:
            Lista de eventos válidos
        """
        return [
            # Eventos de órdenes
            'order/created',
            'order/paid',
            'order/updated',
            'order/fulfilled',
            'order/cancelled',
            
            # Eventos de productos
            'product/created',
            'product/updated',
            'product/deleted',
        ]
    
    def configure_all_webhooks(self) -> Dict[str, Any]:
        """
        Configurar todos los webhooks válidos automáticamente.
        
        Returns:
            Dict con resultado de la configuración
        """
        try:
            logger.info("🔧 Iniciando configuración automática de webhooks...")
            
            # Obtener webhooks existentes
            existing_webhooks = self.get_existing_webhooks()
            existing_events = [wh.get('event') for wh in existing_webhooks]
            
            # Obtener eventos válidos
            valid_events = self.get_valid_events()
            
            # URL base para webhooks
            webhook_base_url = self.get_webhook_base_url()
            
            created_webhooks = []
            skipped_webhooks = []
            failed_webhooks = []
            
            for event in valid_events:
                if event in existing_events:
                    logger.info(f"⏭️  Webhook {event} ya existe, omitiendo...")
                    skipped_webhooks.append(event)
                    continue
                
                # Crear webhook
                result = self.create_webhook(event, webhook_base_url)
                
                if result['success']:
                    created_webhooks.append(event)
                    logger.info(f"✅ Webhook {event} creado exitosamente")
                else:
                    failed_webhooks.append({
                        'event': event,
                        'error': result['error']
                    })
                    logger.error(f"❌ Error creando webhook {event}: {result['error']}")
            
            return {
                'success': True,
                'message': f'Configuración de webhooks completada',
                'created': created_webhooks,
                'skipped': skipped_webhooks,
                'failed': failed_webhooks,
                'total_created': len(created_webhooks),
                'total_skipped': len(skipped_webhooks),
                'total_failed': len(failed_webhooks),
                'webhook_base_url': webhook_base_url
            }
            
        except Exception as e:
            logger.error(f"Error en configuración automática de webhooks: {e}")
            return {
                'success': False,
                'message': f'Error configurando webhooks: {str(e)}'
            }
    
    def get_existing_webhooks(self) -> List[Dict[str, Any]]:
        """
        Obtener webhooks existentes.
        
        Returns:
            Lista de webhooks existentes
        """
        try:
            response = requests.get(self.base_url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error obteniendo webhooks existentes: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error obteniendo webhooks existentes: {e}")
            return []
    
    def create_webhook(self, event: str, base_url: str) -> Dict[str, Any]:
        """
        Crear un webhook específico.
        
        Args:
            event: Evento del webhook
            base_url: URL base para webhooks
            
        Returns:
            Dict con resultado de la creación
        """
        try:
            # Construir URL del webhook
            webhook_url = f"{base_url}/tiendanube-adminet/webhook/{event.replace('/', '_')}"
            
            payload = {
                'event': event,
                'url': webhook_url
            }
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                webhook_data = response.json()
                return {
                    'success': True,
                    'webhook_id': webhook_data.get('id'),
                    'webhook_url': webhook_url,
                    'message': f'Webhook {event} creado exitosamente'
                }
            else:
                error_msg = f"Error {response.status_code}: {response.text}"
                return {
                    'success': False,
                    'error': error_msg
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_webhook_endpoint(self, webhook_url: str) -> Dict[str, Any]:
        """
        Probar endpoint de webhook.
        
        Args:
            webhook_url: URL del webhook a probar
            
        Returns:
            Dict con resultado de la prueba
        """
        try:
            # Enviar request de prueba
            test_payload = {
                'test': True,
                'event': 'test',
                'message': 'Webhook endpoint test'
            }
            
            response = requests.post(
                webhook_url,
                json=test_payload,
                timeout=10
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'message': 'Webhook endpoint funcionando correctamente'
                }
            else:
                return {
                    'success': False,
                    'error': f'Endpoint no responde correctamente: {response.status_code}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Error probando endpoint: {str(e)}'
            }
