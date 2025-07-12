"""
Cliente de API para MercadoPago
Soporte completo para APIs de pagos y SmartPOS
"""

import requests
import json
import logging
import time
from typing import Dict, Any, Optional
from django.conf import settings
from mercadopago.settings import (
    MERCADOPAGO_API_TIMEOUT,
    MERCADOPAGO_API_RETRY_ATTEMPTS,
    MERCADOPAGO_API_RETRY_DELAY,
    MERCADOPAGO_DEVICE_TIMEOUT
)

logger = logging.getLogger(__name__)


class MercadoPagoAPIClient:
    """
    Cliente para interactuar con las APIs de MercadoPago
    """
    
    def __init__(self, config):
        """
        Inicializar cliente con configuración
        
        Args:
            config: Instancia de MercadoPagoConfig
        """
        self.config = config
        self.base_url = config.get_api_base_url()
        self.smartpos_url = config.get_smartpos_api_url()
        self.headers = {
            'Authorization': f'Bearer {config.client_secret}',
            'Content-Type': 'application/json',
            'User-Agent': 'Synap-MercadoPago-Integration/1.0'
        }
        self.timeout = MERCADOPAGO_API_TIMEOUT
        self.retry_attempts = MERCADOPAGO_API_RETRY_ATTEMPTS
        self.retry_delay = MERCADOPAGO_API_RETRY_DELAY
    
    def _make_request(self, method: str, url: str, data: Optional[Dict] = None, 
                     headers: Optional[Dict] = None, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Realizar petición HTTP con reintentos
        
        Args:
            method: Método HTTP (GET, POST, PUT, DELETE)
            url: URL de la petición
            data: Datos a enviar
            headers: Headers adicionales
            timeout: Timeout específico para esta petición
            
        Returns:
            Respuesta de la API como diccionario
        """
        request_headers = self.headers.copy()
        if headers:
            request_headers.update(headers)
        
        request_timeout = timeout or self.timeout
        
        for attempt in range(self.retry_attempts):
            try:
                logger.debug(f"MercadoPago API request: {method} {url} (attempt {attempt + 1})")
                
                response = requests.request(
                    method=method,
                    url=url,
                    json=data if data else None,
                    headers=request_headers,
                    timeout=request_timeout
                )
                
                # Log response
                logger.debug(f"MercadoPago API response: {response.status_code}")
                
                # Verificar si la respuesta es exitosa
                if response.status_code in [200, 201, 202]:
                    return response.json()
                elif response.status_code == 404:
                    logger.warning(f"Resource not found: {url}")
                    return {'error': 'Resource not found', 'status_code': 404}
                elif response.status_code == 401:
                    logger.error("Unauthorized access to MercadoPago API")
                    return {'error': 'Unauthorized', 'status_code': 401}
                elif response.status_code == 429:
                    logger.warning("Rate limit exceeded, retrying...")
                    if attempt < self.retry_attempts - 1:
                        time.sleep(self.retry_delay * (attempt + 1))
                        continue
                    return {'error': 'Rate limit exceeded', 'status_code': 429}
                else:
                    logger.error(f"API error: {response.status_code} - {response.text}")
                    return {
                        'error': f'API error: {response.status_code}',
                        'status_code': response.status_code,
                        'response': response.text
                    }
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on attempt {attempt + 1}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                return {'error': 'Request timeout', 'status_code': 408}
                
            except requests.exceptions.ConnectionError:
                logger.error("Connection error to MercadoPago API")
                return {'error': 'Connection error', 'status_code': 503}
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error: {str(e)}")
                return {'error': f'Request error: {str(e)}', 'status_code': 500}
                
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                return {'error': f'Unexpected error: {str(e)}', 'status_code': 500}
        
        return {'error': 'Max retry attempts exceeded', 'status_code': 500}
    
    # ==================== MÉTODOS DE PAGOS ====================
    
    def create_preference(self, preference_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crear preferencia de pago
        
        Args:
            preference_data: Datos de la preferencia
            
        Returns:
            Respuesta de la API con la preferencia creada
        """
        url = f"{self.base_url}/checkout/preferences"
        return self._make_request('POST', url, preference_data)
    
    def get_preference(self, preference_id: str) -> Dict[str, Any]:
        """
        Obtener preferencia de pago
        
        Args:
            preference_id: ID de la preferencia
            
        Returns:
            Datos de la preferencia
        """
        url = f"{self.base_url}/checkout/preferences/{preference_id}"
        return self._make_request('GET', url)
    
    def update_preference(self, preference_id: str, preference_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualizar preferencia de pago
        
        Args:
            preference_id: ID de la preferencia
            preference_data: Nuevos datos de la preferencia
            
        Returns:
            Respuesta de la API
        """
        url = f"{self.base_url}/checkout/preferences/{preference_id}"
        return self._make_request('PUT', url, preference_data)
    
    def get_payment(self, payment_id: str) -> Dict[str, Any]:
        """
        Obtener información de pago
        
        Args:
            payment_id: ID del pago
            
        Returns:
            Datos del pago
        """
        url = f"{self.base_url}/v1/payments/{payment_id}"
        return self._make_request('GET', url)
    
    def refund_payment(self, payment_id: str, amount: Optional[float] = None) -> Dict[str, Any]:
        """
        Reembolsar pago
        
        Args:
            payment_id: ID del pago
            amount: Monto a reembolsar (si no se especifica, se reembolsa todo)
            
        Returns:
            Respuesta de la API
        """
        url = f"{self.base_url}/v1/payments/{payment_id}/refunds"
        data = {}
        if amount:
            data['amount'] = amount
        return self._make_request('POST', url, data)
    
    def get_payment_methods(self) -> Dict[str, Any]:
        """
        Obtener métodos de pago disponibles
        
        Returns:
            Lista de métodos de pago
        """
        url = f"{self.base_url}/v1/payment_methods"
        return self._make_request('GET', url)
    
    # ==================== MÉTODOS DE SMARTPOS ====================
    
    def register_smartpos_device(self, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Registrar dispositivo SmartPOS
        
        Args:
            device_data: Datos del dispositivo
            
        Returns:
            Respuesta de la API con el ID del dispositivo
        """
        url = f"{self.smartpos_url}/devices"
        return self._make_request('POST', url, device_data, timeout=MERCADOPAGO_DEVICE_TIMEOUT)
    
    def get_smartpos_devices(self) -> Dict[str, Any]:
        """
        Obtener lista de dispositivos SmartPOS
        
        Returns:
            Lista de dispositivos
        """
        url = f"{self.smartpos_url}/devices"
        return self._make_request('GET', url)
    
    def get_smartpos_device(self, device_id: str) -> Dict[str, Any]:
        """
        Obtener información de un dispositivo SmartPOS
        
        Args:
            device_id: ID del dispositivo
            
        Returns:
            Datos del dispositivo
        """
        url = f"{self.smartpos_url}/devices/{device_id}"
        return self._make_request('GET', url, timeout=MERCADOPAGO_DEVICE_TIMEOUT)
    
    def get_smartpos_device_status(self, device_id: str) -> Dict[str, Any]:
        """
        Obtener estado de un dispositivo SmartPOS
        
        Args:
            device_id: ID del dispositivo
            
        Returns:
            Estado del dispositivo
        """
        url = f"{self.smartpos_url}/devices/{device_id}/status"
        return self._make_request('GET', url, timeout=MERCADOPAGO_DEVICE_TIMEOUT)
    
    def process_smartpos_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesar pago en dispositivo SmartPOS
        
        Args:
            payment_data: Datos del pago
            
        Returns:
            Respuesta de la API con el resultado del pago
        """
        device_id = payment_data.get('device_id')
        if not device_id:
            return {'error': 'Device ID is required', 'status_code': 400}
        
        url = f"{self.smartpos_url}/devices/{device_id}/payment"
        return self._make_request('POST', url, payment_data, timeout=MERCADOPAGO_DEVICE_TIMEOUT)
    
    def get_smartpos_device_config(self, device_id: str) -> Dict[str, Any]:
        """
        Obtener configuración de un dispositivo SmartPOS
        
        Args:
            device_id: ID del dispositivo
            
        Returns:
            Configuración del dispositivo
        """
        url = f"{self.smartpos_url}/devices/{device_id}/config"
        return self._make_request('GET', url, timeout=MERCADOPAGO_DEVICE_TIMEOUT)
    
    def update_smartpos_device_config(self, device_id: str, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualizar configuración de un dispositivo SmartPOS
        
        Args:
            device_id: ID del dispositivo
            config_data: Nueva configuración
            
        Returns:
            Respuesta de la API
        """
        url = f"{self.smartpos_url}/devices/{device_id}/config"
        return self._make_request('PUT', url, config_data, timeout=MERCADOPAGO_DEVICE_TIMEOUT)
    
    def delete_smartpos_device(self, device_id: str) -> Dict[str, Any]:
        """
        Eliminar dispositivo SmartPOS
        
        Args:
            device_id: ID del dispositivo
            
        Returns:
            Respuesta de la API
        """
        url = f"{self.smartpos_url}/devices/{device_id}"
        return self._make_request('DELETE', url, timeout=MERCADOPAGO_DEVICE_TIMEOUT)
    
    # ==================== MÉTODOS DE WEBHOOKS ====================
    
    def create_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crear webhook
        
        Args:
            webhook_data: Datos del webhook
            
        Returns:
            Respuesta de la API
        """
        url = f"{self.base_url}/webhooks"
        return self._make_request('POST', url, webhook_data)
    
    def get_webhooks(self) -> Dict[str, Any]:
        """
        Obtener lista de webhooks
        
        Returns:
            Lista de webhooks
        """
        url = f"{self.base_url}/webhooks"
        return self._make_request('GET', url)
    
    def delete_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """
        Eliminar webhook
        
        Args:
            webhook_id: ID del webhook
            
        Returns:
            Respuesta de la API
        """
        url = f"{self.base_url}/webhooks/{webhook_id}"
        return self._make_request('DELETE', url)
    
    # ==================== MÉTODOS DE UTILIDAD ====================
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Probar conexión con la API
        
        Returns:
            Resultado de la prueba de conexión
        """
        try:
            # Intentar obtener métodos de pago como prueba de conexión
            result = self.get_payment_methods()
            if 'error' not in result:
                return {'success': True, 'message': 'Connection successful'}
            else:
                return {'success': False, 'error': result.get('error', 'Unknown error')}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_account_info(self) -> Dict[str, Any]:
        """
        Obtener información de la cuenta
        
        Returns:
            Información de la cuenta
        """
        url = f"{self.base_url}/users/me"
        return self._make_request('GET', url)
    
    def validate_credentials(self) -> Dict[str, Any]:
        """
        Validar credenciales de la API
        
        Returns:
            Resultado de la validación
        """
        try:
            account_info = self.get_account_info()
            if 'error' not in account_info:
                return {
                    'valid': True,
                    'account_info': account_info
                }
            else:
                return {
                    'valid': False,
                    'error': account_info.get('error', 'Invalid credentials')
                }
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            } 