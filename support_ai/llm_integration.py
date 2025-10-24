import os
import json
import logging
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.core.cache import cache
import openai
from openai import OpenAI

logger = logging.getLogger(__name__)

class LLMIntegration:
    """Integración con diferentes proveedores de LLMs"""
    
    def __init__(self, provider: str = "openai"):
        self.provider = provider
        self.client = None
        self._setup_client()
    
    def _setup_client(self):
        """Configura el cliente del proveedor de LLM"""
        if self.provider == "openai":
            api_key = getattr(settings, 'OPENAI_API_KEY', os.getenv('OPENAI_API_KEY'))
            if not api_key:
                logger.warning("OPENAI_API_KEY no configurada")
                return
            
            self.client = OpenAI(api_key=api_key)
        elif self.provider == "anthropic":
            # Implementar Claude
            pass
        elif self.provider == "mistral":
            # Implementar Mistral
            pass
    
    def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Genera una respuesta usando el LLM configurado
        
        Args:
            messages: Lista de mensajes en formato OpenAI
            model: Modelo a usar
            temperature: Temperatura para la generación
            max_tokens: Máximo de tokens
            stream: Si debe hacer streaming
            
        Returns:
            Dict con la respuesta y metadatos
        """
        if not self.client:
            return {
                "content": "Error: LLM no configurado",
                "confidence": 0.0,
                "model_used": "none",
                "tokens_used": 0
            }
        
        try:
            if self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=stream
                )
                
                if stream:
                    return response
                else:
                    return {
                        "content": response.choices[0].message.content,
                        "confidence": 0.9,  # OpenAI no proporciona confidence
                        "model_used": model,
                        "tokens_used": response.usage.total_tokens if response.usage else 0
                    }
                    
        except Exception as e:
            logger.error(f"Error generando respuesta con {self.provider}: {e}")
            return {
                "content": f"Error en el servicio de IA: {str(e)}",
                "confidence": 0.0,
                "model_used": model,
                "tokens_used": 0
            }
    
    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Analiza el sentimiento del texto"""
        messages = [
            {"role": "system", "content": "Analiza el sentimiento del siguiente texto y responde solo con un JSON con las claves: positive, negative, neutral. Los valores deben sumar 1.0"},
            {"role": "user", "content": text}
        ]
        
        response = self.generate_response(messages, temperature=0.1)
        try:
            return json.loads(response["content"])
        except:
            return {"positive": 0.33, "negative": 0.33, "neutral": 0.34}
    
    def extract_entities(self, text: str) -> List[Dict[str, str]]:
        """Extrae entidades del texto (productos, clientes, etc.)"""
        messages = [
            {"role": "system", "content": "Extrae entidades del texto. Responde con JSON array de objetos con: type (product, customer, company, date, amount), value, confidence"},
            {"role": "user", "content": text}
        ]
        
        response = self.generate_response(messages, temperature=0.1)
        try:
            return json.loads(response["content"])
        except:
            return []
    
    def classify_intent(self, text: str) -> Dict[str, Any]:
        """Clasifica la intención del usuario"""
        intents = [
            "facturacion", "configuracion", "ventas", "inventario", 
            "soporte_general", "escalacion", "consulta"
        ]
        
        messages = [
            {"role": "system", "content": f"Clasifica la intención del usuario. Opciones: {', '.join(intents)}. Responde con JSON: {{'intent': 'intent_name', 'confidence': 0.0-1.0, 'entities': ['entity1', 'entity2']}}"},
            {"role": "user", "content": text}
        ]
        
        response = self.generate_response(messages, temperature=0.1)
        try:
            return json.loads(response["content"])
        except:
            return {"intent": "soporte_general", "confidence": 0.5, "entities": []}

# Instancia global
llm_client = LLMIntegration() 