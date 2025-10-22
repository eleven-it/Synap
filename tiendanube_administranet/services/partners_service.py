"""
Servicio para interactuar con la API de Partners de TiendaNube.
Permite obtener el store_id desde un installation_id.
"""

import requests
import logging
from typing import Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class TiendaNubePartnersService:
    """
    Servicio para interactuar con la API de Partners de TiendaNube.
    """
    
    def __init__(self, partner_token: Optional[str] = None):
        """
        Inicializar el servicio de Partners.
        
        Args:
            partner_token: Token de Partners de TiendaNube
        """
        self.partner_token = partner_token or getattr(settings, 'TIENDANUBE_PARTNER_TOKEN', None)
        self.base_url = "https://partners.tiendanube.com/api/v1"
        
        if not self.partner_token:
            logger.warning("TiendaNube Partner Token no configurado")
    
    def get_store_id_from_installation(self, installation_id: str) -> Dict[str, Any]:
        """
        Obtener el store_id desde un installation_id usando la API de Partners.
        
        Args:
            installation_id: ID de la instalación
            
        Returns:
            Dict con el resultado de la operación
        """
        try:
            if not self.partner_token:
                return {
                    'success': False,
                    'message': 'Partner Token no configurado',
                    'error': 'TIENDANUBE_PARTNER_TOKEN no está configurado'
                }
            
            # Construir URL del endpoint
            url = f"{self.base_url}/installations/{installation_id}"
            
            # Headers para la API de Partners
            headers = {
                'Authorization': f'Bearer {self.partner_token}',
                'Content-Type': 'application/json',
                'User-Agent': 'Synap-Tiendanube-Integration/1.0'
            }
            
            logger.info(f"Llamando a API de Partners: {url}")
            
            # Realizar la llamada
            response = requests.get(url, headers=headers, timeout=30)
            
            logger.info(f"Respuesta de Partners API: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                store_id = data.get('store_id')
                
                if store_id:
                    logger.info(f"Store ID obtenido: {store_id} desde installation_id: {installation_id}")
                    return {
                        'success': True,
                        'store_id': str(store_id),
                        'installation_id': installation_id,
                        'data': data,
                        'message': f'Store ID obtenido exitosamente: {store_id}'
                    }
                else:
                    return {
                        'success': False,
                        'message': 'No se encontró store_id en la respuesta',
                        'error': 'store_id no encontrado en la respuesta de la API'
                    }
            else:
                error_data = response.json() if response.content else {}
                return {
                    'success': False,
                    'message': f'Error en API de Partners: {response.status_code}',
                    'error': error_data.get('message', response.text),
                    'status_code': response.status_code
                }
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout al llamar a Partners API para installation_id: {installation_id}")
            return {
                'success': False,
                'message': 'Timeout al conectar con la API de Partners',
                'error': 'Timeout'
            }
        except requests.exceptions.ConnectionError:
            logger.error(f"Error de conexión al llamar a Partners API para installation_id: {installation_id}")
            return {
                'success': False,
                'message': 'Error de conexión con la API de Partners',
                'error': 'Connection Error'
            }
        except Exception as e:
            logger.error(f"Error inesperado al obtener store_id desde installation_id {installation_id}: {e}")
            return {
                'success': False,
                'message': f'Error inesperado: {str(e)}',
                'error': str(e)
            }
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Probar la conexión con la API de Partners.
        
        Returns:
            Dict con el resultado de la prueba
        """
        try:
            if not self.partner_token:
                return {
                    'success': False,
                    'message': 'Partner Token no configurado',
                    'error': 'TIENDANUBE_PARTNER_TOKEN no está configurado'
                }
            
            # Probar con un endpoint básico
            url = f"{self.base_url}/apps"
            headers = {
                'Authorization': f'Bearer {self.partner_token}',
                'Content-Type': 'application/json',
                'User-Agent': 'Synap-Tiendanube-Integration/1.0'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'message': 'Conexión exitosa con API de Partners',
                    'status_code': response.status_code
                }
            else:
                return {
                    'success': False,
                    'message': f'Error de conexión: {response.status_code}',
                    'error': response.text,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            logger.error(f"Error probando conexión con Partners API: {e}")
            return {
                'success': False,
                'message': f'Error de conexión: {str(e)}',
                'error': str(e)
            }

