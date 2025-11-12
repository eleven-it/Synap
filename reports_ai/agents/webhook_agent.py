"""
Agente de Webhooks (Interface Externa)
Recibe solicitudes externas y devuelve respuestas en formato pactado
"""
import logging
from typing import Dict, Any
from .base import BaseAgent

logger = logging.getLogger(__name__)


class WebhookAgent(BaseAgent):
    """
    Agente de Webhooks - Interface externa
    Valida payload, normaliza formato y gestiona respuestas JSON no técnicas
    """
    
    def __init__(self, **kwargs):
        super().__init__(
            agent_name="Webhook",
            model="gpt-4",
            temperature=0.0,
            max_tokens=500,
            **kwargs
        )
    
    def get_system_prompt(self) -> str:
        return """Eres Agente de Webhooks.

Validar payload de negocio, normalizar y responder en JSON no técnico.

Formato de respuesta:
{
  "resumen": ["..."],
  "metricas": {},
  "desglose": [],
  "periodo_cubierto": "...",
  "notas": ["..."]
}

Nunca retornar SQL, nombres técnicos, rutas o archivos.
"""
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Valida y normaliza payloads de webhooks"""
        payload = input_data.get('payload', {})
        
        # Validar campos requeridos
        required = ['intent']
        for field in required:
            if field not in payload:
                return {
                    'success': False,
                    'error': f'Campo requerido faltante: {field}',
                    'agent': 'webhook'
                }
        
        # Normalizar a formato interno
        normalized = {
            'query': payload.get('intent', ''),
            'context': {
                'periodo': payload.get('periodo', {}),
                'filtros': payload.get('filtros', {}),
                'segmentacion': payload.get('segmentacion', [])
            }
        }
        
        return {
            'success': True,
            'normalized': normalized,
            'agent': 'webhook'
        }

