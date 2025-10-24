"""
Adaptador de Ollama usando requests directamente
Resuelve problemas de conectividad con la librería ollama de Python
"""

import logging
import json
import time
import requests
from typing import Dict, Any, Optional, List
from django.conf import settings
from django.utils import timezone
import os

logger = logging.getLogger(__name__)


class OllamaAdapterRequests:
    """
    Adaptador para Ollama usando requests directamente
    Resuelve problemas de conectividad con la librería ollama de Python
    """
    
    def __init__(self, model_name: str = "llama3.1:8b"):
        self.model_name = model_name
        self.base_url = self._get_ollama_url()
        self.available_models = []
        self._initialize_client()
    
    def _get_ollama_url(self) -> str:
        """Obtiene la URL de Ollama desde variables de entorno o configuración por defecto"""
        # Intentar diferentes hosts en orden de prioridad
        hosts_to_try = [
            os.getenv('OLLAMA_HOST'),
            '192.168.65.254',  # Docker Desktop conocido
            'host.docker.internal',
            'localhost'
        ]
        
        port = os.getenv('OLLAMA_PORT', '11434')
        
        for host in hosts_to_try:
            if host:
                try:
                    # Probar conectividad
                    test_url = f"http://{host}:{port}/api/tags"
                    response = requests.get(test_url, timeout=5)
                    if response.status_code == 200:
                        logger.info(f"✅ Ollama encontrado en: {host}:{port}")
                        return f"http://{host}:{port}"
                except Exception as e:
                    logger.debug(f"Host {host}:{port} no accesible: {e}")
                    continue
        
        # Fallback a la configuración por defecto
        default_url = "http://192.168.65.254:11434"
        logger.warning(f"⚠️ Usando URL por defecto: {default_url}")
        return default_url
    
    def _initialize_client(self):
        """Inicializa el cliente verificando conectividad y modelos"""
        try:
            # Verificar conectividad
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code != 200:
                raise ConnectionError(f"Ollama no responde en {self.base_url}")
            
            # Obtener modelos disponibles
            data = response.json()
            self.available_models = [model['name'] for model in data.get('models', [])]
            
            # Verificar que el modelo solicitado esté disponible
            if self.model_name not in self.available_models:
                logger.warning(f"Modelo {self.model_name} no encontrado. Modelos disponibles: {self.available_models}")
                if self.available_models:
                    self.model_name = self.available_models[0]
                    logger.info(f"Usando modelo fallback: {self.model_name}")
                else:
                    raise ValueError("No hay modelos disponibles en Ollama")
            
            logger.info(f"✅ Cliente Ollama inicializado con modelo: {self.model_name}")
            logger.info(f"   URL: {self.base_url}")
            logger.info(f"   Modelos disponibles: {self.available_models}")
            
        except Exception as e:
            logger.error(f"Error inicializando cliente Ollama: {e}")
            self.available_models = []
    
    def is_available(self) -> bool:
        """Verifica si Ollama está disponible"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Genera una respuesta usando Ollama
        
        Args:
            prompt: El prompt a enviar al modelo
            context: Contexto adicional (opcional)
            
        Returns:
            Dict con la respuesta y metadatos
        """
        if not self.is_available():
            return {
                'success': False,
                'error': 'Ollama no está disponible',
                'response': None,
                'model': self.model_name,
                'timestamp': timezone.now()
            }
        
        try:
            # Preparar el payload
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "options": {
                    "temperature": 0.7,
                    "max_tokens": 500,
                    "top_p": 0.9,
                    "repeat_penalty": 1.1
                }
            }
            
            # Agregar contexto si está disponible
            if context:
                if 'system_prompt' in context:
                    payload['system'] = context['system_prompt']
                if 'temperature' in context:
                    payload['options']['temperature'] = context['temperature']
                if 'max_tokens' in context:
                    payload['options']['max_tokens'] = context['max_tokens']
            
            start_time = time.time()
            
            # Enviar solicitud
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=60,
                stream=True
            )
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f'Error HTTP {response.status_code}: {response.text}',
                    'response': None,
                    'model': self.model_name,
                    'timestamp': timezone.now()
                }
            
            # Procesar respuesta streaming
            full_response = ""
            response_data = {}
            
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        full_response += data.get('response', '')
                        
                        # Capturar metadatos
                        if 'model' in data:
                            response_data['model'] = data['model']
                        if 'done' in data:
                            response_data['done'] = data['done']
                        if 'total_duration' in data:
                            response_data['total_duration'] = data['total_duration']
                        
                        # Si terminó, salir del loop
                        if data.get('done', False):
                            break
                            
                    except json.JSONDecodeError as e:
                        logger.warning(f"Error decodificando línea: {e}")
                        continue
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            return {
                'success': True,
                'response': full_response.strip(),
                'model': response_data.get('model', self.model_name),
                'processing_time': processing_time,
                'total_duration': response_data.get('total_duration'),
                'timestamp': timezone.now(),
                'context_used': context
            }
            
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': 'Timeout: La solicitud tardó demasiado',
                'response': None,
                'model': self.model_name,
                'timestamp': timezone.now()
            }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'error': 'Error de conexión: No se pudo conectar con Ollama',
                'response': None,
                'model': self.model_name,
                'timestamp': timezone.now()
            }
        except Exception as e:
            logger.error(f"Error generando respuesta con Ollama: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': None,
                'model': self.model_name,
                'timestamp': timezone.now()
            }
    
    def chat_completion(self, messages: List[Dict[str, str]], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Genera una respuesta de chat usando el formato de mensajes
        
        Args:
            messages: Lista de mensajes en formato [{"role": "user", "content": "..."}]
            context: Contexto adicional (opcional)
            
        Returns:
            Dict con la respuesta del chat
        """
        try:
            # Convertir mensajes a prompt
            prompt = self._messages_to_prompt(messages)
            
            # Generar respuesta
            result = self.generate_response(prompt, context)
            
            if result['success']:
                return {
                    'success': True,
                    'choices': [{
                        'message': {
                            'role': 'assistant',
                            'content': result['response']
                        },
                        'finish_reason': 'stop'
                    }],
                    'model': result['model'],
                    'usage': {
                        'prompt_tokens': len(prompt),
                        'completion_tokens': len(result['response']),
                        'total_tokens': len(prompt) + len(result['response'])
                    },
                    'processing_time': result.get('processing_time', 0)
                }
            else:
                return {
                    'success': False,
                    'error': result['error'],
                    'choices': []
                }
                
        except Exception as e:
            logger.error(f"Error en chat completion: {e}")
            return {
                'success': False,
                'error': str(e),
                'choices': []
            }
    
    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Convierte mensajes de chat a un prompt de texto"""
        prompt = ""
        
        for message in messages:
            role = message.get('role', 'user')
            content = message.get('content', '')
            
            if role == 'system':
                prompt += f"Instrucciones del sistema: {content}\n\n"
            elif role == 'user':
                prompt += f"Usuario: {content}\n"
            elif role == 'assistant':
                prompt += f"Asistente: {content}\n"
        
        prompt += "Asistente: "
        return prompt
    
    def get_models(self) -> List[str]:
        """Obtiene la lista de modelos disponibles"""
        return self.available_models.copy()
    
    def health_check(self) -> Dict[str, Any]:
        """Verifica el estado de salud de Ollama"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            end_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                models = [model['name'] for model in data.get('models', [])]
                
                return {
                    'status': 'healthy',
                    'url': self.base_url,
                    'response_time': end_time - start_time,
                    'models_available': len(models),
                    'models': models,
                    'current_model': self.model_name
                }
            else:
                return {
                    'status': 'unhealthy',
                    'url': self.base_url,
                    'error': f'HTTP {response.status_code}',
                    'response_time': end_time - start_time
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'url': self.base_url,
                'error': str(e),
                'response_time': None
            }


# Instancia global
_ollama_adapter_requests = None


def get_ollama_adapter_requests() -> OllamaAdapterRequests:
    """Obtiene la instancia global del adaptador de Ollama con requests"""
    global _ollama_adapter_requests
    
    if _ollama_adapter_requests is None:
        _ollama_adapter_requests = OllamaAdapterRequests()
    
    return _ollama_adapter_requests


def test_ollama_adapter_requests() -> Dict[str, Any]:
    """Prueba el adaptador de Ollama con requests"""
    try:
        adapter = get_ollama_adapter_requests()
        
        # Verificar disponibilidad
        if not adapter.is_available():
            return {
                'success': False,
                'error': 'Ollama no está disponible'
            }
        
        # Health check
        health = adapter.health_check()
        print(f"Estado de salud: {health['status']}")
        print(f"Modelos disponibles: {health['models']}")
        
        # Probar generación simple
        print("\nProbando generación simple...")
        result = adapter.generate_response("Hola, ¿cómo estás? Responde en español de manera amigable.")
        
        if result['success']:
            print(f"✅ Generación exitosa")
            print(f"   Respuesta: {result['response']}")
            print(f"   Modelo: {result['model']}")
            print(f"   Tiempo: {result['processing_time']:.2f}s")
            
            return {
                'success': True,
                'response': result['response'],
                'model': result['model'],
                'processing_time': result['processing_time'],
                'health': health
            }
        else:
            print(f"❌ Error en generación: {result['error']}")
            return {
                'success': False,
                'error': result['error']
            }
            
    except Exception as e:
        logger.error(f"Error probando adaptador de Ollama: {e}")
        return {
            'success': False,
            'error': str(e)
        }
