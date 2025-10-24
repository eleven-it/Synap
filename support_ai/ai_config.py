"""
Configuración y gestión de APIs de IA avanzadas
"""
import os
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


@dataclass
class AIModelConfig:
    """Configuración de un modelo de IA"""
    name: str
    provider: str
    model_id: str
    max_tokens: int
    temperature: float
    cost_per_1k_tokens: float
    is_available: bool = True
    features: List[str] = None
    
    def __post_init__(self):
        if self.features is None:
            self.features = []


class AIServiceManager:
    """
    Gestor centralizado de servicios de IA
    """
    
    def __init__(self):
        self.models = {
            # OpenAI Models
            'gpt-4o': AIModelConfig(
                name="GPT-4 Omni",
                provider="openai",
                model_id="gpt-4o",
                max_tokens=4096,
                temperature=0.7,
                cost_per_1k_tokens=0.005,
                features=['text', 'vision', 'code', 'reasoning']
            ),
            'gpt-4o-mini': AIModelConfig(
                name="GPT-4 Omni Mini",
                provider="openai",
                model_id="gpt-4o-mini",
                max_tokens=16384,
                temperature=0.7,
                cost_per_1k_tokens=0.00015,
                features=['text', 'code', 'reasoning']
            ),
            'gpt-4-turbo': AIModelConfig(
                name="GPT-4 Turbo",
                provider="openai",
                model_id="gpt-4-turbo-preview",
                max_tokens=4096,
                temperature=0.7,
                cost_per_1k_tokens=0.01,
                features=['text', 'code', 'reasoning']
            ),
            
            # Anthropic Models
            'claude-3-5-sonnet': AIModelConfig(
                name="Claude 3.5 Sonnet",
                provider="anthropic",
                model_id="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                temperature=0.7,
                cost_per_1k_tokens=0.003,
                features=['text', 'vision', 'code', 'reasoning']
            ),
            'claude-3-haiku': AIModelConfig(
                name="Claude 3 Haiku",
                provider="anthropic",
                model_id="claude-3-haiku-20240307",
                max_tokens=4096,
                temperature=0.7,
                cost_per_1k_tokens=0.00025,
                features=['text', 'vision', 'code']
            ),
            
            # Local Models (para desarrollo)
            'local-llama': AIModelConfig(
                name="Local Llama",
                provider="local",
                model_id="llama-3.1-8b-instruct",
                max_tokens=2048,
                temperature=0.7,
                cost_per_1k_tokens=0.0,
                features=['text', 'code'],
                is_available=False
            )
        }
        
        # Configuración de proveedores
        self.providers = {
            'openai': {
                'api_key': os.getenv('OPENAI_API_KEY'),
                'base_url': os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
                'timeout': 30,
                'max_retries': 3
            },
            'anthropic': {
                'api_key': os.getenv('ANTHROPIC_API_KEY'),
                'base_url': os.getenv('ANTHROPIC_BASE_URL', 'https://api.anthropic.com'),
                'timeout': 30,
                'max_retries': 3
            }
        }
    
    def get_model_config(self, model_id: str) -> Optional[AIModelConfig]:
        """Obtiene la configuración de un modelo específico"""
        return self.models.get(model_id)
    
    def get_available_models(self, provider: str = None) -> List[AIModelConfig]:
        """Obtiene modelos disponibles, opcionalmente filtrados por proveedor"""
        models = [model for model in self.models.values() if model.is_available]
        if provider:
            models = [model for model in models if model.provider == provider]
        return models
    
    def get_best_model_for_task(self, task_type: str, budget: float = None) -> AIModelConfig:
        """
        Selecciona el mejor modelo para una tarea específica
        """
        available_models = self.get_available_models()
        
        # Filtrar por características según la tarea
        if task_type == 'vision':
            available_models = [m for m in available_models if 'vision' in m.features]
        elif task_type == 'code':
            available_models = [m for m in available_models if 'code' in m.features]
        elif task_type == 'reasoning':
            available_models = [m for m in available_models if 'reasoning' in m.features]
        
        if not available_models:
            # Fallback al modelo más básico
            return self.models.get('gpt-4o-mini')
        
        # Si hay restricción de presupuesto, filtrar por costo
        if budget is not None:
            available_models = [m for m in available_models if m.cost_per_1k_tokens <= budget]
        
        # Seleccionar el modelo con mejor relación costo/calidad
        if available_models:
            return min(available_models, key=lambda x: x.cost_per_1k_tokens)
        
        return self.models.get('gpt-4o-mini')
    
    def estimate_cost(self, model_id: str, input_tokens: int, output_tokens: int) -> float:
        """Estima el costo de una llamada a la API"""
        model = self.get_model_config(model_id)
        if not model:
            return 0.0
        
        # Costo por tokens de entrada y salida
        input_cost = (input_tokens / 1000) * model.cost_per_1k_tokens
        output_cost = (output_tokens / 1000) * model.cost_per_1k_tokens * 2  # Salida suele ser más cara
        
        return input_cost + output_cost


class AIPromptManager:
    """
    Gestor de prompts y plantillas para diferentes tareas
    """
    
    def __init__(self):
        self.prompts = {
            'support_general': {
                'system': """Eres un asistente de soporte técnico experto y empático. Tu objetivo es ayudar a los usuarios de manera clara, precisa y amigable.

CARACTERÍSTICAS:
- Responde de manera profesional pero cercana
- Proporciona soluciones paso a paso cuando sea posible
- Si no estás seguro, sugiere contactar a un agente humano
- Adapta tu tono según el sentimiento del usuario
- Usa emojis moderadamente para hacer la conversación más amigable

CONTEXTO DEL SISTEMA:
- Es un sistema de gestión empresarial (ERP)
- Incluye módulos de facturación, inventario, ventas, etc.
- Los usuarios pueden ser principiantes o avanzados

FORMATO DE RESPUESTA:
- Responde en español
- Sé conciso pero completo
- Incluye pasos numerados cuando sea apropiado
- Sugiere recursos adicionales si es relevante""",
                
                'user_template': """Usuario: {message}

Contexto adicional:
- Sentimiento detectado: {sentiment}
- Categoría: {category}
- Experiencia del usuario: {experience_level}
- Historial de tickets: {ticket_history}"""
            },
            
            'support_technical': {
                'system': """Eres un especialista técnico en sistemas empresariales. Proporciona soluciones técnicas detalladas y precisas.

ENFOQUE:
- Análisis técnico profundo
- Soluciones paso a paso
- Consideraciones de seguridad
- Mejores prácticas
- Troubleshooting sistemático""",
                
                'user_template': """Problema técnico reportado: {message}

Detalles del sistema:
- Versión: {system_version}
- Configuración: {configuration}
- Logs de error: {error_logs}
- Pasos previos intentados: {previous_attempts}"""
            },
            
            'support_billing': {
                'system': """Eres un especialista en facturación y pagos. Ayuda a los usuarios con consultas relacionadas con facturas, pagos y configuraciones de cuenta.

ÁREAS DE EXPERTISE:
- Facturación y cobros
- Métodos de pago
- Configuración de cuenta
- Resolución de disputas
- Políticas de reembolso""",
                
                'user_template': """Consulta de facturación: {message}

Información de la cuenta:
- Plan actual: {current_plan}
- Estado de facturación: {billing_status}
- Método de pago: {payment_method}
- Historial de pagos: {payment_history}"""
            },
            
            'sentiment_analysis': {
                'system': """Analiza el sentimiento y las emociones del mensaje del usuario. Proporciona un análisis detallado que incluya:

1. Sentimiento general (positivo/negativo/neutral/urgente)
2. Emociones específicas detectadas
3. Nivel de urgencia
4. Palabras clave importantes
5. Sugerencias de respuesta apropiada

Responde en formato JSON.""",
                
                'user_template': """Mensaje a analizar: {message}

Contexto adicional:
- Historial de interacciones: {interaction_history}
- Tipo de ticket: {ticket_type}
- Tiempo transcurrido: {time_elapsed}"""
            },
            
            'code_analysis': {
                'system': """Eres un experto en análisis de código y debugging. Analiza el código proporcionado y ofrece:

1. Identificación de problemas
2. Sugerencias de mejora
3. Explicaciones claras
4. Ejemplos de código corregido
5. Mejores prácticas aplicables""",
                
                'user_template': """Código a analizar:
{code}

Contexto:
- Lenguaje: {language}
- Propósito: {purpose}
- Error reportado: {error_message}"""
            }
        }
    
    def get_prompt(self, prompt_type: str, **kwargs) -> Dict[str, str]:
        """Obtiene un prompt específico con variables sustituidas"""
        if prompt_type not in self.prompts:
            raise ValueError(f"Tipo de prompt no encontrado: {prompt_type}")
        
        prompt = self.prompts[prompt_type].copy()
        
        # Sustituir variables en las plantillas
        for key, template in prompt.items():
            if isinstance(template, str):
                try:
                    prompt[key] = template.format(**kwargs)
                except KeyError as e:
                    logger.warning(f"Variable faltante en prompt {prompt_type}: {e}")
                    # Mantener la plantilla original si faltan variables
                    pass
        
        return prompt
    
    def create_custom_prompt(self, system_message: str, user_message: str, **kwargs) -> Dict[str, str]:
        """Crea un prompt personalizado"""
        return {
            'system': system_message.format(**kwargs),
            'user': user_message.format(**kwargs)
        }


# Instancias globales
ai_service_manager = AIServiceManager()
ai_prompt_manager = AIPromptManager() 