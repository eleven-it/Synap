"""
Clase base para todos los agentes del sistema Reports AI
Implementa configuración común y parámetros anti-alucinación
"""
import logging
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
import openai
from django.conf import settings
import os

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Clase base abstracta para todos los agentes CrewAI
    
    Configuración común:
    - Parámetros anti-alucinación (temperature, top_p, etc.)
    - Cliente OpenAI
    - Logging y métricas
    - Validaciones de entrada/salida
    """
    
    # Configuración anti-alucinación por defecto
    DEFAULT_TEMPERATURE = 0.3  # Temperatura baja para máximo determinismo
    DEFAULT_TOP_P = 0.9
    DEFAULT_FREQUENCY_PENALTY = 0.0
    DEFAULT_PRESENCE_PENALTY = 0.0
    DEFAULT_MAX_TOKENS = 2000
    
    def __init__(
        self,
        agent_name: str,
        model: str = "gpt-4",
        temperature: Optional[float] = None,
        **kwargs
    ):
        """
        Inicializa el agente base
        
        Args:
            agent_name: Nombre del agente
            model: Modelo de OpenAI a usar
            temperature: Temperatura (sobrescribe DEFAULT_TEMPERATURE)
            **kwargs: Parámetros adicionales
        """
        self.agent_name = agent_name
        self.model = model
        self.temperature = temperature if temperature is not None else self.DEFAULT_TEMPERATURE
        
        # Parámetros adicionales
        self.top_p = kwargs.get('top_p', self.DEFAULT_TOP_P)
        self.max_tokens = kwargs.get('max_tokens', self.DEFAULT_MAX_TOKENS)
        self.frequency_penalty = kwargs.get('frequency_penalty', self.DEFAULT_FREQUENCY_PENALTY)
        self.presence_penalty = kwargs.get('presence_penalty', self.DEFAULT_PRESENCE_PENALTY)
        
        # Cliente OpenAI
        self.client = self._setup_openai_client()
        
        # Métricas
        self.total_invocations = 0
        self.successful_invocations = 0
        self.failed_invocations = 0
        self.total_tokens_used = 0
        
        logger.info(f"Agente '{agent_name}' inicializado con temperature={self.temperature}")
    
    def _setup_openai_client(self):
        """
        Configura el cliente de OpenAI
        
        Returns:
            Cliente OpenAI configurado
        """
        api_key = getattr(settings, 'OPENAI_API_KEY', os.getenv('OPENAI_API_KEY'))
        
        if not api_key:
            logger.error("OPENAI_API_KEY no configurada")
            raise ValueError("OPENAI_API_KEY es requerida para usar Reports AI")
        
        return openai.OpenAI(api_key=api_key)
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Retorna el system prompt específico del agente
        Debe ser implementado por cada agente
        
        Returns:
            String con el system prompt
        """
        pass
    
    @abstractmethod
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta la tarea principal del agente
        Debe ser implementado por cada agente
        
        Args:
            input_data: Datos de entrada
            
        Returns:
            Dict con resultados
        """
        pass
    
    def _call_llm(
        self,
        messages: List[Dict[str, str]],
        **override_params
    ) -> Dict[str, Any]:
        """
        Llama al LLM con los parámetros configurados
        
        Args:
            messages: Lista de mensajes para el LLM
            **override_params: Parámetros para sobrescribir configuración
            
        Returns:
            Dict con respuesta y metadatos
        """
        import time
        self.total_invocations += 1
        call_start = time.time()
        
        try:
            # Parámetros finales (defaults + overrides)
            params = {
                'model': override_params.get('model', self.model),
                'messages': messages,
                'temperature': override_params.get('temperature', self.temperature),
                'top_p': override_params.get('top_p', self.top_p),
                'max_tokens': override_params.get('max_tokens', self.max_tokens),
                'frequency_penalty': override_params.get('frequency_penalty', self.frequency_penalty),
                'presence_penalty': override_params.get('presence_penalty', self.presence_penalty),
            }
            
            # Log inicio de llamada LLM
            logger.info(
                f"[{self.agent_name}] 🤖 LLAMADA LLM INICIADA\n"
                f"  ├─ Modelo: {params['model']}\n"
                f"  ├─ Temperature: {params['temperature']}\n"
                f"  ├─ Max Tokens: {params['max_tokens']}\n"
                f"  └─ Mensajes: {len(messages)} mensaje(s)"
            )
            
            # Llamada a OpenAI
            response = self.client.chat.completions.create(**params)
            
            call_duration = time.time() - call_start
            
            # Extraer resultados
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            prompt_tokens = response.usage.prompt_tokens if response.usage else 0
            completion_tokens = response.usage.completion_tokens if response.usage else 0
            
            # Actualizar métricas
            self.successful_invocations += 1
            self.total_tokens_used += tokens_used
            
            # Log resultado exitoso
            logger.info(
                f"[{self.agent_name}] ✅ LLAMADA LLM EXITOSA\n"
                f"  ├─ Duración: {call_duration:.2f}s\n"
                f"  ├─ Tokens Prompt: {prompt_tokens}\n"
                f"  ├─ Tokens Completion: {completion_tokens}\n"
                f"  ├─ Tokens Totales: {tokens_used}\n"
                f"  ├─ Finish Reason: {response.choices[0].finish_reason}\n"
                f"  └─ Respuesta: {len(content)} caracteres"
            )
            
            # Log preview de la respuesta (primeros 200 chars)
            preview = content[:200].replace('\n', ' ')
            logger.debug(f"[{self.agent_name}] 📄 Preview: {preview}...")
            
            return {
                'success': True,
                'content': content,
                'tokens_used': tokens_used,
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'model': params['model'],
                'temperature': params['temperature'],
                'finish_reason': response.choices[0].finish_reason,
                'duration': call_duration
            }
            
        except Exception as e:
            call_duration = time.time() - call_start
            logger.error(
                f"[{self.agent_name}] ❌ ERROR EN LLAMADA LLM\n"
                f"  ├─ Duración: {call_duration:.2f}s\n"
                f"  ├─ Error: {type(e).__name__}\n"
                f"  └─ Mensaje: {str(e)}"
            )
            self.failed_invocations += 1
            
            return {
                'success': False,
                'error': str(e),
                'content': None,
                'tokens_used': 0,
                'duration': call_duration
            }
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Obtiene métricas del agente
        
        Returns:
            Dict con métricas de uso
        """
        success_rate = 0.0
        if self.total_invocations > 0:
            success_rate = (self.successful_invocations / self.total_invocations) * 100
        
        return {
            'agent_name': self.agent_name,
            'total_invocations': self.total_invocations,
            'successful_invocations': self.successful_invocations,
            'failed_invocations': self.failed_invocations,
            'success_rate': success_rate,
            'total_tokens_used': self.total_tokens_used,
            'avg_tokens_per_call': (
                self.total_tokens_used / self.successful_invocations
                if self.successful_invocations > 0 else 0
            )
        }
    
    def log_execution(
        self,
        input_summary: str,
        output_summary: str,
        success: bool,
        duration: float
    ):
        """
        Registra la ejecución del agente para auditoría
        
        Args:
            input_summary: Resumen de la entrada
            output_summary: Resumen de la salida
            success: Si fue exitoso
            duration: Duración en segundos
        """
        log_level = logging.INFO if success else logging.ERROR
        
        logger.log(
            log_level,
            f"[{self.agent_name}] Input: {input_summary[:100]}... | "
            f"Output: {output_summary[:100]}... | "
            f"Success: {success} | Duration: {duration:.2f}s"
        )

