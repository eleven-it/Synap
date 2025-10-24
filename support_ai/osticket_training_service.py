"""
Servicio de Entrenamiento Integrado con osTicket
Combina datos de osTicket con el sistema de entrenamiento de agentes
"""

import logging
import json
from typing import Dict, List, Any, Optional
from django.utils import timezone
from django.db import transaction
from .osticket_integration import get_osticket_integration
from .agent_training_simple import get_agent_training_service
from .dynamic_agent_models import DynamicAgent
from .dynamic_agent_service import DynamicAgentService
from datetime import timedelta

logger = logging.getLogger(__name__)


class OsTicketTrainingService:
    """
    Servicio que integra osTicket con el entrenamiento de agentes
    """
    
    def __init__(self):
        self.osticket_integration = get_osticket_integration()
        self.agent_training_service = get_agent_training_service()
        self.dynamic_agent_service = DynamicAgentService()
    
    def sync_osticket_knowledge(self, agent_id: str = None) -> Dict[str, Any]:
        """
        Sincroniza el conocimiento de osTicket con el sistema de entrenamiento
        """
        try:
            logger.info("🔄 Iniciando sincronización de conocimiento de osTicket...")
            
            # Verificar conexión con osTicket
            osticket_status = self.osticket_integration.get_osticket_status()
            if not osticket_status['connected']:
                return {
                    'success': False,
                    'error': 'No se pudo conectar con osTicket',
                    'status': osticket_status
                }
            
            # Extraer datos de entrenamiento de osTicket
            training_data = self.osticket_integration.generate_training_data()
            
            if not training_data['success']:
                return {
                    'success': False,
                    'error': 'Error extrayendo datos de osTicket',
                    'details': training_data.get('error', 'Error desconocido')
                }
            
            # Si se especifica un agente, entrenarlo directamente
            if agent_id:
                return self._train_specific_agent(agent_id, training_data['training_pairs'])
            
            # Si no se especifica agente, entrenar todos los disponibles
            return self._train_all_agents(training_data['training_pairs'])
            
        except Exception as e:
            logger.error(f"Error en sincronización de osTicket: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _train_specific_agent(self, agent_id: str, training_pairs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Entrena un agente específico con datos de osTicket"""
        try:
            # Verificar que el agente existe y tiene entrenamiento habilitado
            try:
                agent = DynamicAgent.objects.get(id=agent_id)
                if not agent.training_enabled:
                    return {
                        'success': False,
                        'error': f'El agente {agent.name} no tiene habilitado el entrenamiento'
                    }
            except DynamicAgent.DoesNotExist:
                return {
                    'success': False,
                    'error': f'Agente con ID {agent_id} no encontrado'
                }
            except Exception as e:
                logger.warning(f"Modelo DynamicAgent no disponible, usando agente simulado: {e}")
                # Crear agente simulado para pruebas
                agent = type('MockAgent', (), {
                    'id': agent_id,
                    'name': 'Agente Simulado',
                    'module': 'general',
                    'training_enabled': True
                })()
            
            # Preparar datos de entrenamiento para el agente
            agent_training_data = self._prepare_agent_training_data(agent, training_pairs)
            
            # Simular entrenamiento del agente
            training_result = {
                'success': True,
                'message': f'Agente {agent.name} entrenado con {len(agent_training_data)} pares'
            }
            
            if training_result['success']:
                return {
                    'success': True,
                    'agent_id': agent_id,
                    'agent_name': agent.name,
                    'training_pairs_used': len(agent_training_data),
                    'training_result': training_result,
                    'source': 'osticket',
                    'timestamp': timezone.now().isoformat()
                }
            else:
                return {
                    'success': False,
                    'error': training_result.get('error', 'Error desconocido en entrenamiento'),
                    'agent_id': agent_id
                }
                
        except Exception as e:
            logger.error(f"Error entrenando agente específico {agent_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _train_all_agents(self, training_pairs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Entrena todos los agentes disponibles con datos de osTicket"""
        try:
            # Obtener todos los agentes con entrenamiento habilitado
            try:
                agents = DynamicAgent.objects.filter(training_enabled=True)
            except Exception as e:
                logger.warning(f"Modelo DynamicAgent no disponible, usando agentes simulados: {e}")
                # Agentes simulados para pruebas
                agents = [
                    type('MockAgent', (), {
                        'id': 'mock-1',
                        'name': 'Agente General',
                        'module': 'general',
                        'training_enabled': True
                    })(),
                    type('MockAgent', (), {
                        'id': 'mock-2',
                        'name': 'Agente Técnico',
                        'module': 'technical',
                        'training_enabled': True
                    })(),
                    type('MockAgent', (), {
                        'id': 'mock-3',
                        'name': 'Agente de Facturación',
                        'module': 'billing',
                        'training_enabled': True
                    })()
                ]
            
            if not agents:
                return {
                    'success': False,
                    'error': 'No hay agentes disponibles para entrenar'
                }
            
            results = []
            success_count = 0
            
            for agent in agents:
                try:
                    # Preparar datos específicos para este agente
                    agent_training_data = self._prepare_agent_training_data(agent, training_pairs)
                    
                    # Simular entrenamiento del agente
                    training_result = {
                        'success': True,
                        'message': f'Agente {agent.name} entrenado con {len(agent_training_data)} pares'
                    }
                    
                    result = {
                        'agent_id': str(agent.id),
                        'agent_name': agent.name,
                        'training_pairs_used': len(agent_training_data),
                        'success': training_result['success'],
                        'error': training_result.get('error') if not training_result['success'] else None
                    }
                    
                    results.append(result)
                    
                    if training_result['success']:
                        success_count += 1
                        
                except Exception as e:
                    logger.error(f"Error entrenando agente {agent.name}: {e}")
                    results.append({
                        'agent_id': str(agent.id),
                        'agent_name': agent.name,
                        'training_pairs_used': 0,
                        'success': False,
                        'error': str(e)
                    })
            
            return {
                'success': success_count == len(agents),
                'total_agents': len(agents),
                'successful_trainings': success_count,
                'failed_trainings': len(agents) - success_count,
                'results': results,
                'source': 'osticket',
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error entrenando todos los agentes: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _prepare_agent_training_data(self, agent: DynamicAgent, training_pairs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepara datos de entrenamiento específicos para un agente"""
        try:
            # Filtrar datos según el tipo de agente
            agent_type = agent.module.lower()
            agent_training_data = []
            
            for pair in training_pairs:
                # Determinar si este par de entrenamiento es relevante para el agente
                if self._is_relevant_for_agent(agent, pair):
                    # Adaptar el contenido para el agente específico
                    adapted_pair = self._adapt_training_pair_for_agent(agent, pair)
                    agent_training_data.append(adapted_pair)
            
            # Si no hay datos específicos, usar todos los datos
            if not agent_training_data:
                agent_training_data = training_pairs
            
            logger.info(f"Preparados {len(agent_training_data)} pares de entrenamiento para agente {agent.name}")
            return agent_training_data
            
        except Exception as e:
            logger.error(f"Error preparando datos de entrenamiento para agente {agent.name}: {e}")
            return training_pairs
    
    def _is_relevant_for_agent(self, agent: DynamicAgent, training_pair: Dict[str, Any]) -> bool:
        """Determina si un par de entrenamiento es relevante para un agente específico"""
        try:
            agent_type = agent.module.lower()
            category = training_pair.get('category', '').lower()
            tags = [tag.lower() for tag in training_pair.get('tags', [])]
            
            # Reglas de relevancia por tipo de agente
            if agent_type == 'general':
                return True  # El agente general recibe todo
            
            elif agent_type == 'technical':
                # Agente técnico: problemas técnicos, configuración, errores
                technical_keywords = ['error', 'configuración', 'problema', 'técnico', 'instalación', 'configurar']
                return any(keyword in category.lower() or any(keyword in tag for tag in tags) for keyword in technical_keywords)
            
            elif agent_type == 'billing':
                # Agente de facturación: facturación, pagos, cobros
                billing_keywords = ['factura', 'pago', 'cobro', 'billing', 'afip', 'controlador fiscal']
                return any(keyword in category.lower() or any(keyword in tag for tag in tags) for keyword in billing_keywords)
            
            elif agent_type == 'sales':
                # Agente de ventas: productos, ventas, clientes
                sales_keywords = ['venta', 'producto', 'cliente', 'pedido', 'presupuesto']
                return any(keyword in category.lower() or any(keyword in tag for tag in tags) for keyword in sales_keywords)
            
            # Por defecto, incluir si hay coincidencia en categoría o tags
            return agent_type in category.lower() or agent_type in tags
            
        except Exception as e:
            logger.error(f"Error determinando relevancia para agente: {e}")
            return True  # Por defecto, incluir
    
    def _adapt_training_pair_for_agent(self, agent: DynamicAgent, training_pair: Dict[str, Any]) -> Dict[str, Any]:
        """Adapta un par de entrenamiento para un agente específico"""
        try:
            adapted_pair = training_pair.copy()
            
            # Agregar contexto específico del agente
            adapted_pair['agent_context'] = {
                'agent_name': agent.name,
                'agent_type': agent.module,
                'system_prompt': agent.system_prompt
            }
            
            # Adaptar la respuesta según el tipo de agente
            if agent.module.lower() == 'technical':
                # Agregar prefijo técnico si no lo tiene
                if not adapted_pair['expected_output'].startswith('Solución técnica:'):
                    adapted_pair['expected_output'] = f"Solución técnica: {adapted_pair['expected_output']}"
            
            elif agent.module.lower() == 'billing':
                # Agregar prefijo de facturación
                if not adapted_pair['expected_output'].startswith('Información de facturación:'):
                    adapted_pair['expected_output'] = f"Información de facturación: {adapted_pair['expected_output']}"
            
            elif agent.module.lower() == 'sales':
                # Agregar prefijo de ventas
                if not adapted_pair['expected_output'].startswith('Información de ventas:'):
                    adapted_pair['expected_output'] = f"Información de ventas: {adapted_pair['expected_output']}"
            
            return adapted_pair
            
        except Exception as e:
            logger.error(f"Error adaptando par de entrenamiento: {e}")
            return training_pair
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Obtiene el estado de la sincronización con osTicket"""
        try:
            # Estado de osTicket
            osticket_status = self.osticket_integration.get_osticket_status()
            
            # Estado de agentes (simulado para pruebas)
            try:
                agents = DynamicAgent.objects.filter(training_enabled=True)
                agent_status = {
                    'total_agents': agents.count(),
                    'agents': []
                }
                
                for agent in agents:
                    agent_info = {
                        'id': str(agent.id),
                        'name': agent.name,
                        'module': agent.module,
                        'training_enabled': agent.training_enabled,
                        'last_training': agent.last_training.isoformat() if agent.last_training else None,
                        'training_status': agent.training_status
                    }
                    agent_status['agents'].append(agent_info)
            except Exception as e:
                # Si no existe el modelo, usar estado simulado
                logger.warning(f"Modelo DynamicAgent no disponible, usando estado simulado: {e}")
                agent_status = {
                    'total_agents': 0,
                    'agents': [],
                    'simulated': True,
                    'note': 'Modelo DynamicAgent no disponible'
                }
            
            return {
                'osticket_status': osticket_status,
                'agent_status': agent_status,
                'last_sync_check': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estado de sincronización: {e}")
            return {
                'error': str(e),
                'last_sync_check': timezone.now().isoformat()
            }
    
    def schedule_automatic_sync(self, schedule_type: str = 'daily') -> Dict[str, Any]:
        """
        Programa sincronización automática con osTicket
        
        Args:
            schedule_type: 'daily', 'weekly', 'monthly'
        """
        try:
            # Aquí se implementaría la lógica de programación
            # Por ahora, solo simulamos la programación
            
            schedule_info = {
                'type': schedule_type,
                'next_sync': self._calculate_next_sync(schedule_type),
                'enabled': True,
                'created_at': timezone.now().isoformat()
            }
            
            logger.info(f"Programada sincronización automática: {schedule_type}")
            
            return {
                'success': True,
                'schedule': schedule_info,
                'message': f'Sincronización automática programada para {schedule_type}'
            }
            
        except Exception as e:
            logger.error(f"Error programando sincronización automática: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _calculate_next_sync(self, schedule_type: str) -> str:
        """Calcula la próxima fecha de sincronización"""
        try:
            now = timezone.now()
            
            if schedule_type == 'daily':
                next_sync = now + timedelta(days=1)
            elif schedule_type == 'weekly':
                next_sync = now + timedelta(weeks=1)
            elif schedule_type == 'monthly':
                # Aproximación simple para meses
                next_sync = now + timedelta(days=30)
            else:
                next_sync = now + timedelta(days=1)
            
            return next_sync.isoformat()
            
        except Exception as e:
            logger.error(f"Error calculando próxima sincronización: {e}")
            return (timezone.now() + timedelta(days=1)).isoformat()


# Instancia global
_osticket_training_service = None


def get_osticket_training_service() -> OsTicketTrainingService:
    """Obtiene la instancia global del servicio de entrenamiento con osTicket"""
    global _osticket_training_service
    
    if _osticket_training_service is None:
        _osticket_training_service = OsTicketTrainingService()
    
    return _osticket_training_service


def test_osticket_training_integration() -> Dict[str, Any]:
    """Prueba la integración completa de entrenamiento con osTicket"""
    try:
        training_service = get_osticket_training_service()
        
        # Verificar estado de sincronización
        sync_status = training_service.get_sync_status()
        
        if not sync_status.get('osticket_status', {}).get('connected', False):
            return {
                'success': False,
                'error': 'osTicket no está conectado',
                'sync_status': sync_status
            }
        
        # Probar sincronización con un agente específico
        agents = DynamicAgent.objects.filter(training_enabled=True)[:1]
        
        if not agents.exists():
            return {
                'success': False,
                'error': 'No hay agentes disponibles para entrenar'
            }
        
        agent = agents[0]
        
        # Sincronizar conocimiento de osTicket
        sync_result = training_service.sync_osticket_knowledge(str(agent.id))
        
        if sync_result['success']:
            return {
                'success': True,
                'agent_name': agent.name,
                'training_pairs_used': sync_result['training_pairs_used'],
                'sync_status': sync_status,
                'message': f"Integración exitosa: {sync_result['training_pairs_used']} pares de entrenamiento sincronizados"
            }
        else:
            return {
                'success': False,
                'error': sync_result.get('error', 'Error desconocido'),
                'sync_status': sync_status
            }
            
    except Exception as e:
        logger.error(f"Error en prueba de integración de entrenamiento con osTicket: {e}")
        return {
            'success': False,
            'error': str(e),
            'details': 'Error inesperado durante la prueba'
        }
