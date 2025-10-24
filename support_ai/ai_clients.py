"""
Clientes para APIs de IA avanzadas
"""
import os
import json
import logging
import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import time

# OpenAI
try:
    from openai import OpenAI, AsyncOpenAI
    from openai.types.chat import ChatCompletion
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Anthropic
try:
    import anthropic
    from anthropic import Anthropic, AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from django.core.cache import cache
from django.conf import settings
from .ai_config import ai_service_manager, ai_prompt_manager

logger = logging.getLogger(__name__)


class BaseAIClient:
    """Cliente base para APIs de IA"""
    
    def __init__(self, provider: str):
        self.provider = provider
        self.config = ai_service_manager.providers.get(provider, {})
        self.api_key = self.config.get('api_key')
        self.base_url = self.config.get('base_url')
        self.timeout = self.config.get('timeout', 30)
        self.max_retries = self.config.get('max_retries', 3)
        
        if not self.api_key:
            logger.warning(f"No se encontró API key para {provider}")
    
    def _get_cache_key(self, model_id: str, prompt: str) -> str:
        """Genera una clave de caché para la respuesta"""
        import hashlib
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
        return f"ai_response:{self.provider}:{model_id}:{prompt_hash}"
    
    def _get_cached_response(self, cache_key: str) -> Optional[Dict]:
        """Obtiene respuesta del caché si existe"""
        return cache.get(cache_key)
    
    def _cache_response(self, cache_key: str, response: Dict, ttl: int = 3600):
        """Guarda respuesta en caché"""
        cache.set(cache_key, response, ttl)
    
    def _log_request(self, model_id: str, input_tokens: int, output_tokens: int, 
                    cost: float, response_time: float):
        """Registra métricas de la solicitud"""
        logger.info(f"AI Request - Provider: {self.provider}, Model: {model_id}, "
                   f"Tokens: {input_tokens}/{output_tokens}, Cost: ${cost:.6f}, "
                   f"Time: {response_time:.2f}s")


class OpenAIClient(BaseAIClient):
    """Cliente para OpenAI API"""
    
    def __init__(self):
        super().__init__('openai')
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI library not available")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
        )
        self.async_client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
        )
    
    def generate_response(self, model_id: str, messages: List[Dict], 
                         temperature: float = 0.7, max_tokens: int = None,
                         use_cache: bool = True) -> Dict[str, Any]:
        """
        Genera una respuesta usando OpenAI
        """
        if not self.api_key:
            return self._fallback_response("OpenAI API key no configurada")
        
        start_time = time.time()
        
        # Configurar tokens máximos
        if max_tokens is None:
            model_config = ai_service_manager.get_model_config(model_id)
            max_tokens = model_config.max_tokens if model_config else 4096
        
        # Verificar caché
        if use_cache:
            cache_key = self._get_cache_key(model_id, json.dumps(messages))
            cached_response = self._get_cached_response(cache_key)
            if cached_response:
                logger.info(f"Respuesta obtenida de caché para {model_id}")
                return cached_response
        
        try:
            response = self.client.chat.completions.create(
                model=model_id,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=self.timeout
            )
            
            # Procesar respuesta
            content = response.choices[0].message.content
            usage = response.usage
            
            # Calcular costo
            cost = ai_service_manager.estimate_cost(
                model_id, usage.prompt_tokens, usage.completion_tokens
            )
            
            # Calcular tiempo de respuesta
            response_time = time.time() - start_time
            
            # Registrar métricas
            self._log_request(model_id, usage.prompt_tokens, usage.completion_tokens, 
                            cost, response_time)
            
            result = {
                'content': content,
                'model': model_id,
                'provider': 'openai',
                'usage': {
                    'prompt_tokens': usage.prompt_tokens,
                    'completion_tokens': usage.completion_tokens,
                    'total_tokens': usage.total_tokens
                },
                'cost': cost,
                'response_time': response_time,
                'timestamp': datetime.now().isoformat()
            }
            
            # Guardar en caché
            if use_cache:
                self._cache_response(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error en OpenAI API: {str(e)}")
            return self._fallback_response(f"Error en OpenAI: {str(e)}")
    
    async def generate_response_async(self, model_id: str, messages: List[Dict],
                                    temperature: float = 0.7, max_tokens: int = None) -> Dict[str, Any]:
        """
        Genera una respuesta asíncrona usando OpenAI
        """
        if not self.api_key:
            return self._fallback_response("OpenAI API key no configurada")
        
        start_time = time.time()
        
        if max_tokens is None:
            model_config = ai_service_manager.get_model_config(model_id)
            max_tokens = model_config.max_tokens if model_config else 4096
        
        try:
            response = await self.async_client.chat.completions.create(
                model=model_id,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=self.timeout
            )
            
            content = response.choices[0].message.content
            usage = response.usage
            
            cost = ai_service_manager.estimate_cost(
                model_id, usage.prompt_tokens, usage.completion_tokens
            )
            
            response_time = time.time() - start_time
            
            self._log_request(model_id, usage.prompt_tokens, usage.completion_tokens, 
                            cost, response_time)
            
            return {
                'content': content,
                'model': model_id,
                'provider': 'openai',
                'usage': {
                    'prompt_tokens': usage.prompt_tokens,
                    'completion_tokens': usage.completion_tokens,
                    'total_tokens': usage.total_tokens
                },
                'cost': cost,
                'response_time': response_time,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error en OpenAI API async: {str(e)}")
            return self._fallback_response(f"Error en OpenAI: {str(e)}")
    
    def _fallback_response(self, error_message: str) -> Dict[str, Any]:
        """Respuesta de fallback cuando hay errores"""
        return {
            'content': f"Lo siento, no puedo procesar tu solicitud en este momento. {error_message}",
            'model': 'fallback',
            'provider': 'openai',
            'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
            'cost': 0.0,
            'response_time': 0.0,
            'timestamp': datetime.now().isoformat(),
            'error': error_message
        }


class AnthropicClient(BaseAIClient):
    """Cliente para Anthropic API"""
    
    def __init__(self):
        super().__init__('anthropic')
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("Anthropic library not available")
        
        self.client = Anthropic(
            api_key=self.api_key,
            base_url=self.base_url
        )
        self.async_client = AsyncAnthropic(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def generate_response(self, model_id: str, messages: List[Dict],
                         temperature: float = 0.7, max_tokens: int = None,
                         use_cache: bool = True) -> Dict[str, Any]:
        """
        Genera una respuesta usando Anthropic
        """
        if not self.api_key:
            return self._fallback_response("Anthropic API key no configurada")
        
        start_time = time.time()
        
        if max_tokens is None:
            model_config = ai_service_manager.get_model_config(model_id)
            max_tokens = model_config.max_tokens if model_config else 4096
        
        # Verificar caché
        if use_cache:
            cache_key = self._get_cache_key(model_id, json.dumps(messages))
            cached_response = self._get_cached_response(cache_key)
            if cached_response:
                logger.info(f"Respuesta obtenida de caché para {model_id}")
                return cached_response
        
        try:
            # Convertir formato de mensajes para Anthropic
            anthropic_messages = self._convert_messages_format(messages)
            
            response = self.client.messages.create(
                model=model_id,
                messages=anthropic_messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            content = response.content[0].text
            usage = response.usage
            
            cost = ai_service_manager.estimate_cost(
                model_id, usage.input_tokens, usage.output_tokens
            )
            
            response_time = time.time() - start_time
            
            self._log_request(model_id, usage.input_tokens, usage.output_tokens, 
                            cost, response_time)
            
            result = {
                'content': content,
                'model': model_id,
                'provider': 'anthropic',
                'usage': {
                    'prompt_tokens': usage.input_tokens,
                    'completion_tokens': usage.output_tokens,
                    'total_tokens': usage.input_tokens + usage.output_tokens
                },
                'cost': cost,
                'response_time': response_time,
                'timestamp': datetime.now().isoformat()
            }
            
            if use_cache:
                self._cache_response(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error en Anthropic API: {str(e)}")
            return self._fallback_response(f"Error en Anthropic: {str(e)}")
    
    def _convert_messages_format(self, messages: List[Dict]) -> List[Dict]:
        """Convierte el formato de mensajes de OpenAI a Anthropic"""
        converted = []
        for msg in messages:
            if msg['role'] == 'system':
                # Anthropic no usa mensajes de sistema, los convertimos a user
                converted.append({
                    'role': 'user',
                    'content': f"System: {msg['content']}"
                })
            else:
                converted.append(msg)
        return converted
    
    def _fallback_response(self, error_message: str) -> Dict[str, Any]:
        """Respuesta de fallback cuando hay errores"""
        return {
            'content': f"Lo siento, no puedo procesar tu solicitud en este momento. {error_message}",
            'model': 'fallback',
            'provider': 'anthropic',
            'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
            'cost': 0.0,
            'response_time': 0.0,
            'timestamp': datetime.now().isoformat(),
            'error': error_message
        }


class AIServiceOrchestrator:
    """
    Orquestador principal para gestionar múltiples servicios de IA
    """
    
    def __init__(self):
        self.clients = {}
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Inicializa los clientes disponibles"""
        try:
            if OPENAI_AVAILABLE:
                self.clients['openai'] = OpenAIClient()
                logger.info("Cliente OpenAI inicializado")
        except Exception as e:
            logger.warning(f"No se pudo inicializar cliente OpenAI: {e}")
        
        try:
            if ANTHROPIC_AVAILABLE:
                self.clients['anthropic'] = AnthropicClient()
                logger.info("Cliente Anthropic inicializado")
        except Exception as e:
            logger.warning(f"No se pudo inicializar cliente Anthropic: {e}")
    
    def get_client(self, provider: str):
        """Obtiene un cliente específico"""
        return self.clients.get(provider)
    
    def generate_response(self, model_id: str, messages: List[Dict],
                         temperature: float = 0.7, max_tokens: int = None,
                         provider: str = None, use_cache: bool = True) -> Dict[str, Any]:
        """
        Genera una respuesta usando el mejor cliente disponible
        """
        # Si no se especifica proveedor, usar el del modelo
        if not provider:
            model_config = ai_service_manager.get_model_config(model_id)
            if model_config:
                provider = model_config.provider
        
        # Intentar con el proveedor especificado
        if provider and provider in self.clients:
            client = self.clients[provider]
            return client.generate_response(model_id, messages, temperature, max_tokens, use_cache)
        
        # Fallback: intentar con cualquier cliente disponible
        for client in self.clients.values():
            try:
                return client.generate_response(model_id, messages, temperature, max_tokens, use_cache)
            except Exception as e:
                logger.warning(f"Error con cliente {client.provider}: {e}")
                continue
        
        # Si no hay clientes disponibles, usar respuesta de fallback
        return {
            'content': "Lo siento, no hay servicios de IA disponibles en este momento.",
            'model': 'fallback',
            'provider': 'none',
            'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
            'cost': 0.0,
            'response_time': 0.0,
            'timestamp': datetime.now().isoformat(),
            'error': 'No hay clientes de IA disponibles'
        }
    
    def generate_support_response(self, user_message: str, context: Dict = None,
                                model_id: str = None) -> Dict[str, Any]:
        """
        Genera una respuesta específica para soporte
        """
        if context is None:
            context = {}
        
        # Seleccionar modelo si no se especifica
        if not model_id:
            task_type = context.get('task_type', 'text')
            model_config = ai_service_manager.get_best_model_for_task(task_type)
            model_id = model_config.model_id if model_config else 'gpt-4o-mini'
        
        # Obtener prompt apropiado
        prompt_type = context.get('prompt_type', 'support_general')
        try:
            prompt = ai_prompt_manager.get_prompt(prompt_type, **context)
        except ValueError:
            prompt = ai_prompt_manager.get_prompt('support_general', **context)
        
        # Construir mensajes
        messages = [
            {'role': 'system', 'content': prompt['system']},
            {'role': 'user', 'content': prompt['user']}
        ]
        
        # Generar respuesta
        return self.generate_response(model_id, messages, temperature=0.7)
    
    def analyze_sentiment(self, message: str, context: Dict = None) -> Dict[str, Any]:
        """
        Analiza el sentimiento de un mensaje usando IA
        """
        if context is None:
            context = {}
        
        # Usar modelo optimizado para análisis
        model_config = ai_service_manager.get_best_model_for_task('reasoning')
        model_id = model_config.model_id if model_config else 'gpt-4o-mini'
        
        # Obtener prompt de análisis de sentimientos
        prompt = ai_prompt_manager.get_prompt('sentiment_analysis', message=message, **context)
        
        messages = [
            {'role': 'system', 'content': prompt['system']},
            {'role': 'user', 'content': prompt['user']}
        ]
        
        response = self.generate_response(model_id, messages, temperature=0.3)
        
        # Intentar parsear JSON de la respuesta
        try:
            sentiment_data = json.loads(response['content'])
            return {
                'success': True,
                'data': sentiment_data,
                'model_used': model_id,
                'response_time': response['response_time']
            }
        except json.JSONDecodeError:
            # Si no es JSON válido, usar análisis básico
            return {
                'success': False,
                'fallback': True,
                'message': 'No se pudo analizar el sentimiento con IA, usando análisis básico',
                'content': response['content']
            }


# Instancia global del orquestador
ai_orchestrator = AIServiceOrchestrator() 