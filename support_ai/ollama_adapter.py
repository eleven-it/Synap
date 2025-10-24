"""
Adaptador para integrar Ollama con el sistema de IA de Eleven Support
"""

import logging
import json
from typing import Dict, Any, Optional
from django.conf import settings
from django.utils import timezone

try:
    import ollama
except ImportError:
    ollama = None

logger = logging.getLogger(__name__)


class OllamaAdapter:
    """
    Adaptador para usar Ollama como proveedor de LLM
    """
    
    def __init__(self, model_name: str = "llama3.1:8b"):
        self.model_name = model_name
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Inicializa el cliente de Ollama"""
        try:
            if ollama is None:
                raise ImportError("Ollama no está instalado")
            
            # Configurar host y puerto desde variables de entorno
            import os
            import socket
            
            # Intentar diferentes métodos para obtener la IP del host
            ollama_host = os.getenv('OLLAMA_HOST')
            if not ollama_host:
                try:
                    # Obtener la IP del host desde el contenedor
                    ollama_host = socket.gethostbyname('host.docker.internal')
                except:
                    # Fallback a la IP conocida de Docker Desktop
                    ollama_host = '192.168.65.254'
            
            ollama_port = os.getenv('OLLAMA_PORT', '11434')
            
            # Configurar el cliente para usar el host específico
            ollama.host = f"http://{ollama_host}:{ollama_port}"
            
            logger.info(f"Configurando Ollama en: {ollama.host}")
            
            # Verificar que el modelo esté disponible
            try:
                models = ollama.list()
                available_models = [model.model for model in models.models]
                
                if self.model_name not in available_models:
                    logger.warning(f"Modelo {self.model_name} no encontrado. Modelos disponibles: {available_models}")
                    # Usar el primer modelo disponible como fallback
                    if available_models:
                        self.model_name = available_models[0]
                        logger.info(f"Usando modelo fallback: {self.model_name}")
                    else:
                        raise ValueError("No hay modelos disponibles en Ollama")
                
                self.client = ollama
                logger.info(f"Cliente Ollama inicializado con modelo: {self.model_name}")
                
            except Exception as e:
                logger.error(f"Error verificando modelos de Ollama: {e}")
                # Intentar con configuración básica
                self.client = ollama
                logger.info(f"Cliente Ollama inicializado con configuración básica")
            
        except Exception as e:
            logger.error(f"Error inicializando Ollama: {e}")
            self.client = None
    
    def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Genera una respuesta usando Ollama
        
        Args:
            prompt: El prompt a enviar al modelo
            context: Contexto adicional (opcional)
            
        Returns:
            Dict con la respuesta y metadatos
        """
        if not self.client:
            return {
                'success': False,
                'error': 'Cliente Ollama no inicializado',
                'response': None,
                'model': self.model_name,
                'timestamp': timezone.now()
            }
        
        try:
            start_time = timezone.now()
            
            # Construir el prompt completo con contexto
            full_prompt = self._build_prompt(prompt, context)
            
            # Generar respuesta
            response = self.client.generate(
                model=self.model_name,
                prompt=full_prompt,
                options={
                    'temperature': 0.7,
                    'top_p': 0.9,
                    'max_tokens': 1000
                }
            )
            
            end_time = timezone.now()
            processing_time = (end_time - start_time).total_seconds()
            
            return {
                'success': True,
                'response': response['response'],
                'model': self.model_name,
                'timestamp': end_time,
                'processing_time': processing_time,
                'tokens_used': response.get('eval_count', 0),
                'context': context
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
    
    def _build_prompt(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Construye el prompt completo con contexto
        
        Args:
            prompt: Prompt principal
            context: Contexto adicional
            
        Returns:
            Prompt completo formateado
        """
        # Usar el system_prompt del agente si está disponible en el contexto
        if context and 'system_prompt' in context:
            system_prompt = context['system_prompt']
        else:
            # Prompt por defecto si no hay uno específico del agente
            system_prompt = """Eres un asistente de soporte técnico especializado en ayudar a usuarios con problemas y consultas sobre sistemas empresariales. 

Debes:
- Ser amigable y profesional
- Proporcionar respuestas claras y útiles
- Si no tienes suficiente información, hacer preguntas específicas
- Responder en español de manera natural y conversacional

Contexto del sistema: Eleven Support - Sistema de soporte empresarial"""

        # Agregar información adicional del contexto
        if context:
            # Filtrar campos que no queremos en el prompt
            excluded_fields = {'system_prompt', 'user_query', 'conversation_history'}
            context_info = {k: v for k, v in context.items() if k not in excluded_fields}
            
            if context_info:
                context_str = "\n".join([f"- {k}: {v}" for k, v in context_info.items()])
                system_prompt += f"\n\nInformación adicional:\n{context_str}"
        
        return f"{system_prompt}\n\nUsuario: {prompt}\n\nAsistente:"
    
    def chat_completion(self, messages: list, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Genera una respuesta para una conversación de chat
        
        Args:
            messages: Lista de mensajes en formato [{"role": "user", "content": "..."}]
            context: Contexto adicional
            
        Returns:
            Dict con la respuesta
        """
        if not messages:
            return {
                'success': False,
                'error': 'No hay mensajes para procesar',
                'response': None
            }
        
        # Tomar el último mensaje del usuario
        user_messages = [msg for msg in messages if msg.get('role') == 'user']
        if not user_messages:
            return {
                'success': False,
                'error': 'No hay mensajes de usuario',
                'response': None
            }
        
        last_user_message = user_messages[-1]['content']
        
        # Construir historial de conversación
        conversation_history = ""
        for msg in messages[:-1]:  # Excluir el último mensaje
            role = "Usuario" if msg.get('role') == 'user' else "Asistente"
            conversation_history += f"{role}: {msg.get('content', '')}\n"
        
        # Agregar historial al contexto
        if context is None:
            context = {}
        context['conversation_history'] = conversation_history
        
        return self.generate_response(last_user_message, context)
    
    def is_available(self) -> bool:
        """Verifica si Ollama está disponible"""
        try:
            if not self.client:
                return False
            
            # Intentar listar modelos para verificar conectividad
            models = self.client.list()
            return len(models.models) > 0
            
        except Exception as e:
            logger.error(f"Error verificando disponibilidad de Ollama: {e}")
            return False


# Instancia global del adaptador
_ollama_adapter = None


def get_ollama_adapter() -> OllamaAdapter:
    """
    Obtiene la instancia global del adaptador de Ollama
    
    Returns:
        Instancia de OllamaAdapter
    """
    global _ollama_adapter
    
    if _ollama_adapter is None:
        _ollama_adapter = OllamaAdapter()
    
    return _ollama_adapter


def test_ollama_connection() -> Dict[str, Any]:
    """
    Prueba la conexión con Ollama
    
    Returns:
        Dict con el resultado de la prueba
    """
    try:
        adapter = get_ollama_adapter()
        
        if not adapter.is_available():
            return {
                'success': False,
                'error': 'Ollama no está disponible',
                'details': 'Verifica que Ollama esté ejecutándose'
            }
        
        # Probar con un prompt simple
        result = adapter.generate_response("Hola, ¿cómo estás?")
        
        return {
            'success': result['success'],
            'model': adapter.model_name,
            'response': result.get('response', '')[:100] + '...' if result.get('response') else None,
            'processing_time': result.get('processing_time'),
            'error': result.get('error')
        }
        
    except Exception as e:
        logger.error(f"Error en prueba de conexión: {e}")
        return {
            'success': False,
            'error': str(e),
            'details': 'Error inesperado durante la prueba'
        }
