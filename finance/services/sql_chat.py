"""
Servicio para interactuar con el agente IA de SQL de n8n.
"""
import requests
import json
from django.conf import settings
from typing import Dict, Any, Optional


def run_sql_chat(
    message: str,
    *,
    user_id: str,
    year: Optional[int] = None,
    currency: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    timeout: int = 25
) -> Dict[str, Any]:
    """
    Envía una consulta al agente IA de SQL de n8n y devuelve la respuesta.
    
    Args:
        message: Consulta en lenguaje natural
        user_id: ID del usuario que hace la consulta
        year: Año para filtrar (opcional)
        currency: Moneda para filtrar (opcional)
        date_from: Fecha de inicio (opcional)
        date_to: Fecha de fin (opcional)
        timeout: Timeout en segundos para la petición
        
    Returns:
        Dict con la respuesta del agente IA o error
    """
    webhook_url = getattr(settings, 'N8N_SQL_CHAT_WEBHOOK', None)
    
    if not webhook_url:
        return {
            'ok': False,
            'reason': 'Webhook de n8n no configurado',
            'details': {'error': 'N8N_SQL_CHAT_WEBHOOK no está definido en la configuración'}
        }
    
    # Construir payload con solo los campos presentes
    payload = {
        'user_id': user_id,
        'message': message
    }
    
    if year is not None:
        payload['year'] = year
    if currency:
        payload['currency'] = currency
    if date_from:
        payload['date_from'] = date_from
    if date_to:
        payload['date_to'] = date_to
    
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Synap-Finance-UI/1.0'
    }
    
    # Agregar API key si está configurada
    if hasattr(settings, 'N8N_API_KEY') and settings.N8N_API_KEY:
        headers['X-API-KEY'] = settings.N8N_API_KEY
    
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers=headers,
            timeout=timeout
        )
        
        # Verificar que la respuesta sea JSON válido
        try:
            result = response.json()
        except json.JSONDecodeError:
            return {
                'ok': False,
                'reason': 'Respuesta inválida del servidor',
                'details': {
                    'status_code': response.status_code,
                    'content': response.text[:500]  # Limitar contenido
                }
            }
        
        # Aplicar límite de filas por seguridad adicional
        max_rows = getattr(settings, 'FINANCE_MAX_ROWS', 200)
        if result.get('ok') and 'rows' in result:
            if len(result['rows']) > max_rows:
                result['rows'] = result['rows'][:max_rows]
                result['meta'] = result.get('meta', {})
                result['meta']['autoLimited'] = True
                result['meta']['explanation'] = (
                    result['meta'].get('explanation', '') + 
                    f' [Resultado limitado a {max_rows} filas por seguridad]'
                )
        
        return result
        
    except requests.exceptions.Timeout:
        return {
            'ok': False,
            'reason': 'Timeout: El servidor tardó demasiado en responder',
            'details': {'timeout': timeout}
        }
        
    except requests.exceptions.ConnectionError:
        return {
            'ok': False,
            'reason': 'Error de conexión: No se pudo conectar al servidor',
            'details': {'url': webhook_url}
        }
        
    except requests.exceptions.RequestException as e:
        return {
            'ok': False,
            'reason': f'Error de red: {str(e)}',
            'details': {'error_type': type(e).__name__}
        }
        
    except Exception as e:
        return {
            'ok': False,
            'reason': f'Error inesperado: {str(e)}',
            'details': {'error_type': type(e).__name__}
        }


