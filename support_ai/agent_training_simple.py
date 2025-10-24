"""
Sistema de Entrenamiento de Agentes Simplificado
Compatible con CrewAI Simplificado y Ollama
"""

import logging
import json
import time
from typing import Dict, List, Any, Optional
from django.utils import timezone
from django.db import transaction
from .crew_ai_simple import get_crew_ai_simple
from .ollama_adapter import get_ollama_adapter
from .dynamic_agent_models import DynamicAgent
from .dynamic_agent_service import DynamicAgentService

logger = logging.getLogger(__name__)


class AgentTrainingService:
    """
    Servicio de entrenamiento de agentes simplificado
    """
    
    def __init__(self):
        self.crew_ai = get_crew_ai_simple()
        self.ollama_adapter = get_ollama_adapter()
        self.dynamic_agent_service = DynamicAgentService()
    
    def train_agent(self, agent_id: str, training_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Entrena un agente con datos específicos
        
        Args:
            agent_id: ID del agente a entrenar
            training_data: Lista de ejemplos de entrenamiento
            
        Returns:
            Resultado del entrenamiento
        """
        try:
            # Obtener el agente
            agent = DynamicAgent.objects.get(id=agent_id)
            
            if not agent.training_enabled:
                return {
                    'success': False,
                    'error': 'El agente no tiene habilitado el entrenamiento'
                }
            
            logger.info(f"Iniciando entrenamiento del agente: {agent.name}")
            
            # Procesar datos de entrenamiento
            processed_data = self._process_training_data(training_data)
            
            # Generar prompt de entrenamiento
            training_prompt = self._generate_training_prompt(agent, processed_data)
            
            # Ejecutar entrenamiento con Ollama
            training_result = self._execute_training(agent, training_prompt)
            
            # Actualizar el agente con los resultados
            self._update_agent_training(agent, training_result)
            
            return {
                'success': True,
                'agent_id': str(agent.id),
                'agent_name': agent.name,
                'training_data_count': len(training_data),
                'training_result': training_result,
                'timestamp': timezone.now().isoformat()
            }
            
        except DynamicAgent.DoesNotExist:
            return {
                'success': False,
                'error': f'Agente con ID {agent_id} no encontrado'
            }
        except Exception as e:
            logger.error(f"Error entrenando agente {agent_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _process_training_data(self, training_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Procesa los datos de entrenamiento"""
        processed = []
        
        for item in training_data:
            processed_item = {
                'input': item.get('input', ''),
                'expected_output': item.get('expected_output', ''),
                'category': item.get('category', 'general'),
                'difficulty': item.get('difficulty', 'medium'),
                'tags': item.get('tags', [])
            }
            processed.append(processed_item)
        
        return processed
    
    def _generate_training_prompt(self, agent: DynamicAgent, training_data: List[Dict[str, Any]]) -> str:
        """Genera el prompt de entrenamiento"""
        
        # Prompt base del agente
        base_prompt = agent.system_prompt or """Eres un asistente de soporte técnico especializado."""
        
        # Agregar ejemplos de entrenamiento
        examples = []
        for i, item in enumerate(training_data[:10]):  # Limitar a 10 ejemplos
            example = f"""
Ejemplo {i+1}:
Entrada: {item['input']}
Respuesta esperada: {item['expected_output']}
Categoría: {item['category']}
"""
            examples.append(example)
        
        # Construir prompt completo
        training_prompt = f"""
{base_prompt}

Basándote en los siguientes ejemplos de entrenamiento, mejora tu capacidad de respuesta:

{''.join(examples)}

Instrucciones de entrenamiento:
1. Analiza los patrones en los ejemplos
2. Identifica las mejores prácticas de respuesta
3. Adapta tu estilo de comunicación según la categoría
4. Mantén consistencia en el tono y formato
5. Asegúrate de ser útil, claro y profesional

¿Estás listo para aplicar estos aprendizajes en futuras interacciones?
"""
        
        return training_prompt
    
    def _execute_training(self, agent: DynamicAgent, training_prompt: str) -> Dict[str, Any]:
        """Ejecuta el entrenamiento usando Ollama"""
        try:
            start_time = time.time()
            
            # Contexto para el entrenamiento
            context = {
                'system_prompt': agent.system_prompt,
                'agent_type': agent.module,
                'training_mode': True,
                'agent_name': agent.name
            }
            
            # Ejecutar entrenamiento
            result = self.ollama_adapter.generate_response(training_prompt, context)
            
            end_time = time.time()
            training_time = end_time - start_time
            
            if result['success']:
                return {
                    'success': True,
                    'training_response': result['response'],
                    'training_time': training_time,
                    'model_used': result['model'],
                    'tokens_used': result.get('tokens_used', 0)
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Error desconocido en entrenamiento'),
                    'training_time': training_time
                }
                
        except Exception as e:
            logger.error(f"Error ejecutando entrenamiento: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _update_agent_training(self, agent: DynamicAgent, training_result: Dict[str, Any]):
        """Actualiza el agente con los resultados del entrenamiento"""
        try:
            with transaction.atomic():
                # Actualizar metadatos del agente
                agent.last_training = timezone.now()
                agent.training_status = 'completed' if training_result['success'] else 'failed'
                
                # Guardar resultados del entrenamiento
                training_metadata = {
                    'last_training_result': training_result,
                    'training_count': getattr(agent, 'training_count', 0) + 1,
                    'last_training_time': timezone.now().isoformat()
                }
                
                agent.training_metadata = training_metadata
                agent.save()
                
                logger.info(f"Agente {agent.name} actualizado con resultados de entrenamiento")
                
        except Exception as e:
            logger.error(f"Error actualizando agente después del entrenamiento: {e}")
    
    def batch_train_agents(self, agent_ids: List[str], training_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Entrena múltiples agentes en lote"""
        results = []
        success_count = 0
        
        for agent_id in agent_ids:
            try:
                result = self.train_agent(agent_id, training_data)
                results.append({
                    'agent_id': agent_id,
                    'result': result
                })
                
                if result['success']:
                    success_count += 1
                    
            except Exception as e:
                results.append({
                    'agent_id': agent_id,
                    'result': {
                        'success': False,
                        'error': str(e)
                    }
                })
        
        return {
            'success': success_count == len(agent_ids),
            'total_agents': len(agent_ids),
            'successful_trainings': success_count,
            'failed_trainings': len(agent_ids) - success_count,
            'results': results,
            'timestamp': timezone.now().isoformat()
        }
    
    def get_training_status(self, agent_id: str) -> Dict[str, Any]:
        """Obtiene el estado de entrenamiento de un agente"""
        try:
            agent = DynamicAgent.objects.get(id=agent_id)
            
            return {
                'agent_id': str(agent.id),
                'agent_name': agent.name,
                'training_enabled': agent.training_enabled,
                'last_training': agent.last_training.isoformat() if agent.last_training else None,
                'training_status': agent.training_status,
                'training_metadata': agent.training_metadata or {},
                'system_prompt': agent.system_prompt
            }
            
        except DynamicAgent.DoesNotExist:
            return {
                'success': False,
                'error': f'Agente con ID {agent_id} no encontrado'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_training_session(self, agent_ids: List[str], training_config: Dict[str, Any]) -> Dict[str, Any]:
        """Crea una sesión de entrenamiento"""
        try:
            session_data = {
                'agent_ids': agent_ids,
                'config': training_config,
                'status': 'created',
                'created_at': timezone.now().isoformat(),
                'progress': 0,
                'results': []
            }
            
            return {
                'success': True,
                'session_id': f"session_{int(time.time())}",
                'session_data': session_data
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


# Instancia global
_agent_training_service = None


def get_agent_training_service() -> AgentTrainingService:
    """Obtiene la instancia global del servicio de entrenamiento"""
    global _agent_training_service
    
    if _agent_training_service is None:
        _agent_training_service = AgentTrainingService()
    
    return _agent_training_service


def test_agent_training() -> Dict[str, Any]:
    """Prueba el sistema de entrenamiento de agentes"""
    try:
        training_service = get_agent_training_service()
        
        # Datos de prueba
        test_training_data = [
            {
                'input': '¿Cómo puedo resetear mi contraseña?',
                'expected_output': 'Para resetear tu contraseña, ve a Configuración > Seguridad > Cambiar contraseña. Te enviaremos un enlace por email.',
                'category': 'account',
                'difficulty': 'easy'
            },
            {
                'input': 'Mi factura tiene un error, ¿qué hago?',
                'expected_output': 'Entiendo tu preocupación. Por favor, comparte el número de factura y el error específico para ayudarte a resolverlo.',
                'category': 'billing',
                'difficulty': 'medium'
            }
        ]
        
        # Buscar un agente disponible para entrenar
        agents = DynamicAgent.objects.filter(training_enabled=True)[:1]
        
        if not agents:
            return {
                'success': False,
                'error': 'No hay agentes disponibles para entrenar'
            }
        
        agent = agents[0]
        
        # Ejecutar entrenamiento de prueba
        result = training_service.train_agent(str(agent.id), test_training_data)
        
        return {
            'success': result['success'],
            'agent_name': agent.name,
            'training_result': result,
            'test_data_count': len(test_training_data)
        }
        
    except Exception as e:
        logger.error(f"Error en prueba de entrenamiento: {e}")
        return {
            'success': False,
            'error': str(e)
        }
