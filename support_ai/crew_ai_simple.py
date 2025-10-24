"""
CrewAI Simplificado para Eleven Support
Versión compatible con las dependencias actuales
"""

import logging
import time
from typing import Dict, List, Any, Optional
from django.utils import timezone
from .ollama_adapter import get_ollama_adapter

logger = logging.getLogger(__name__)


class SimpleCrewAI:
    """
    Implementación simplificada de CrewAI usando Ollama
    """
    
    def __init__(self):
        self.ollama_adapter = get_ollama_adapter()
        self.available = self.ollama_adapter.is_available()
        
        if self.available:
            logger.info("✅ CrewAI Simplificado inicializado correctamente")
        else:
            logger.warning("⚠️ CrewAI Simplificado no disponible - Ollama no está conectado")
    
    def is_available(self) -> bool:
        """Verifica si CrewAI está disponible"""
        return self.available
    
    def create_support_agent(self, agent_type: str = "general") -> Dict[str, Any]:
        """Crea un agente de soporte simplificado"""
        system_prompts = {
            "general": """Eres Elevenito, un asistente de soporte técnico especializado en ayudar a usuarios con problemas y consultas sobre sistemas empresariales.

Tu personalidad:
- Eres amigable, profesional y empático
- Proporcionas respuestas claras, útiles y paso a paso
- Si no tienes suficiente información, haces preguntas específicas
- Respondes en español de manera natural y conversacional
- Siempre buscas la mejor solución para el usuario

Contexto: Eleven Support - Sistema de soporte empresarial inteligente""",
            
            "technical": """Eres un especialista técnico de Eleven Support, experto en resolver problemas técnicos complejos.

Especialidades:
- Configuración de sistemas
- Resolución de errores
- Optimización de rendimiento
- Integración de APIs
- Base de datos y servidores

Enfoque:
- Análisis detallado del problema
- Soluciones paso a paso
- Verificación de la solución
- Prevención de problemas futuros""",
            
            "billing": """Eres un especialista en facturación y pagos de Eleven Support.

Especialidades:
- Facturación y cobros
- Planes y suscripciones
- Métodos de pago
- Reembolsos y ajustes
- Reportes financieros

Enfoque:
- Claridad en la información
- Soluciones rápidas
- Transparencia en los procesos
- Atención al cliente""",
            
            "sales": """Eres un especialista en ventas de Eleven Support, experto en ayudar a clientes potenciales.

Especialidades:
- Presentación de productos
- Demostraciones
- Cotizaciones
- Negociaciones
- Onboarding de clientes

Enfoque:
- Entender las necesidades del cliente
- Proponer soluciones adecuadas
- Facilitar el proceso de compra
- Seguimiento post-venta"""
        }
        
        return {
            "type": agent_type,
            "name": f"Agente {agent_type.title()}",
            "system_prompt": system_prompts.get(agent_type, system_prompts["general"]),
            "available": self.available
        }
    
    def execute_task(self, task_description: str, agent_type: str = "general", context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Ejecuta una tarea usando el agente especificado"""
        try:
            if not self.available:
                return {
                    'success': False,
                    'error': 'CrewAI no está disponible',
                    'content': None
                }
            
            # Crear el agente
            agent = self.create_support_agent(agent_type)
            
            # Construir el contexto completo
            full_context = {
                'system_prompt': agent['system_prompt'],
                'agent_type': agent_type,
                'task_description': task_description,
                'timestamp': timezone.now().isoformat()
            }
            
            if context:
                full_context.update(context)
            
            # Generar respuesta usando Ollama
            result = self.ollama_adapter.generate_response(task_description, full_context)
            
            if result['success']:
                return {
                    'success': True,
                    'content': result['response'],
                    'agent_type': agent_type,
                    'agent_name': agent['name'],
                    'provider': 'crewai_simple',
                    'model': result['model'],
                    'processing_time': result.get('processing_time'),
                    'timestamp': result['timestamp']
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Error desconocido'),
                    'content': None
                }
                
        except Exception as e:
            logger.error(f"Error ejecutando tarea CrewAI: {e}")
            return {
                'success': False,
                'error': str(e),
                'content': None
            }
    
    def process_message(self, message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Procesa un mensaje usando CrewAI"""
        try:
            # Determinar el tipo de agente basado en el contexto
            agent_type = "general"
            
            if context:
                # Determinar agente basado en categoría o palabras clave
                category = context.get('category', '').lower()
                message_lower = message.lower()
                
                if any(word in message_lower for word in ['factura', 'pago', 'cobro', 'precio', 'plan']):
                    agent_type = "billing"
                elif any(word in message_lower for word in ['error', 'problema', 'configurar', 'instalar', 'técnico']):
                    agent_type = "technical"
                elif any(word in message_lower for word in ['comprar', 'vender', 'demo', 'cotización', 'precio']):
                    agent_type = "sales"
            
            # Ejecutar la tarea
            return self.execute_task(message, agent_type, context)
            
        except Exception as e:
            logger.error(f"Error procesando mensaje con CrewAI: {e}")
            return {
                'success': False,
                'error': str(e),
                'content': None
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Obtiene el estado del sistema CrewAI"""
        return {
            'available': self.available,
            'provider': 'crewai_simple',
            'ollama_available': self.ollama_adapter.is_available(),
            'model': self.ollama_adapter.model_name if self.available else None,
            'timestamp': timezone.now().isoformat()
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Verifica la salud del sistema CrewAI"""
        try:
            if not self.available:
                return {
                    'healthy': False,
                    'status': 'not_available',
                    'error': 'Ollama no está conectado'
                }
            
            # Probar con un mensaje simple
            test_result = self.process_message("Hola, ¿cómo estás?")
            
            return {
                'healthy': test_result['success'],
                'status': 'healthy' if test_result['success'] else 'error',
                'response_time': test_result.get('processing_time'),
                'error': test_result.get('error')
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'status': 'error',
                'error': str(e)
            }


# Instancia global
_crew_ai_simple = None


def get_crew_ai_simple() -> SimpleCrewAI:
    """Obtiene la instancia global de CrewAI Simplificado"""
    global _crew_ai_simple
    
    if _crew_ai_simple is None:
        _crew_ai_simple = SimpleCrewAI()
    
    return _crew_ai_simple


def test_crew_ai_simple() -> Dict[str, Any]:
    """Prueba CrewAI Simplificado"""
    try:
        crew_ai = get_crew_ai_simple()
        
        if not crew_ai.is_available():
            return {
                'success': False,
                'error': 'CrewAI no está disponible',
                'details': 'Verifica que Ollama esté ejecutándose'
            }
        
        # Probar con diferentes tipos de agentes
        test_cases = [
            ("Hola, necesito ayuda con mi factura", "billing"),
            ("Tengo un error técnico en el sistema", "technical"),
            ("Me interesa comprar el producto", "sales"),
            ("¿Cómo puedo configurar mi cuenta?", "general")
        ]
        
        results = []
        for message, agent_type in test_cases:
            result = crew_ai.execute_task(message, agent_type)
            results.append({
                'message': message,
                'agent_type': agent_type,
                'success': result['success'],
                'response_length': len(result.get('content', '')) if result.get('content') else 0
            })
        
        success_count = sum(1 for r in results if r['success'])
        
        return {
            'success': success_count == len(test_cases),
            'total_tests': len(test_cases),
            'successful_tests': success_count,
            'results': results,
            'status': crew_ai.get_status()
        }
        
    except Exception as e:
        logger.error(f"Error en prueba de CrewAI: {e}")
        return {
            'success': False,
            'error': str(e),
            'details': 'Error inesperado durante la prueba'
        }
