import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from django.utils import timezone
from django.conf import settings
from .osticket_chat_integration import get_osticket_chat_integration
from .osticket_integration import get_osticket_integration
from .dynamic_agent_models import DynamicAgent
from .dynamic_agent_service import DynamicAgentService
from .ai_clients import ai_orchestrator
from .crew_ai_simple import get_crew_ai_simple
import re

logger = logging.getLogger(__name__)

class ChatMultiAgentSystem:
    def __init__(self):
        self.osticket_chat = get_osticket_chat_integration()
        self.osticket_integration = get_osticket_integration()
        self.dynamic_agent_service = DynamicAgentService()
        self.ai_orchestrator = ai_orchestrator
        self.crew_ai_simple = get_crew_ai_simple()
        
        # Configuración del sistema
        self.max_conversation_turns = 5
        self.confidence_threshold = 0.7
        self.escalation_keywords = [
            'urgente', 'crítico', 'error', 'falla', 'no funciona', 'bloqueado',
            'problema', 'ayuda', 'consulta', 'duda', 'soporte', 'asistencia'
        ]
    
    def process_message(self, user_message: str, user_id: str, user_email: str,
                       conversation_history: List[Dict[str, Any]] = None,
                       session_id: str = None) -> Dict[str, Any]:
        try:
            if conversation_history is None:
                conversation_history = []
            
            # 1. Analizar el mensaje del usuario
            message_analysis = self._analyze_user_message(user_message, conversation_history)
            
            # 2. Determinar si necesitamos crear un ticket
            ticket_decision = self._should_create_ticket(user_message, conversation_history, message_analysis)
            
            # 3. Procesar con el sistema de agentes
            agent_response = self._get_agent_response(user_message, message_analysis, conversation_history)
            
            # 4. Si se debe crear ticket, crearlo
            ticket_info = None
            if ticket_decision['should_create']:
                ticket_result = self._create_ticket_if_needed(
                    user_message, user_id, user_email, conversation_history, agent_response
                )
                if ticket_result['success']:
                    ticket_info = ticket_result
                    agent_response['ticket_created'] = True
                    agent_response['ticket_number'] = ticket_result['ticket_number']
                    agent_response['ticket_id'] = ticket_result['ticket_id']
            
            # 5. Preparar respuesta final
            final_response = self._prepare_final_response(
                agent_response, ticket_info, message_analysis, conversation_history
            )
            
            # 6. Actualizar historial de conversación
            updated_history = self._update_conversation_history(
                conversation_history, user_message, final_response, ticket_info
            )
            
            return {
                'success': True,
                'response': final_response,
                'ticket_created': ticket_info is not None,
                'ticket_info': ticket_info,
                'conversation_history': updated_history,
                'message_analysis': message_analysis,
                'session_id': session_id or self._generate_session_id()
            }
            
        except Exception as e:
            logger.error(f'Error procesando mensaje: {e}')
            return {
                'success': False,
                'error': str(e),
                'response': {
                    'content': 'Lo siento, hubo un error procesando tu mensaje. Por favor, inténtalo de nuevo.',
                    'type': 'error'
                }
            }
    
    def _analyze_user_message(self, message: str, conversation_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        analysis = {
            'urgency_level': self._determine_urgency(message),
            'complexity_level': self._determine_complexity(message),
            'department': self._determine_department(message),
            'requires_human': False,
            'confidence_score': 0.0,
            'keywords': self._extract_keywords(message),
            'sentiment': self._analyze_sentiment(message),
            'conversation_length': len(conversation_history)
        }
        
        if self.ai_orchestrator:
            try:
                sentiment_result = self.ai_orchestrator.analyze_sentiment(message)
                if sentiment_result.get('success'):
                    analysis['sentiment'] = sentiment_result.get('sentiment', 'neutral')
                    analysis['sentiment_score'] = sentiment_result.get('score', 0.0)
            except Exception as e:
                logger.warning(f'Error en análisis avanzado: {e}')
        
        analysis['requires_human'] = self._requires_human_intervention(analysis)
        return analysis
    
    def _should_create_ticket(self, message: str, conversation_history: List[Dict[str, Any]], 
                             analysis: Dict[str, Any]) -> Dict[str, Any]:
        decision = {
            'should_create': False,
            'reason': '',
            'priority': 'normal',
            'confidence': 0.0
        }
        
        factors = {
            'urgency': 0.0,
            'complexity': 0.0,
            'conversation_length': 0.0,
            'sentiment': 0.0,
            'keywords': 0.0
        }
        
        # Urgencia
        if analysis['urgency_level'] == 'high':
            factors['urgency'] = 0.8
        elif analysis['urgency_level'] == 'medium':
            factors['urgency'] = 0.5
        else:
            factors['urgency'] = 0.2
        
        # Complejidad
        if analysis['complexity_level'] == 'high':
            factors['complexity'] = 0.7
        elif analysis['complexity_level'] == 'medium':
            factors['complexity'] = 0.4
        else:
            factors['complexity'] = 0.2
        
        # Longitud de conversación
        if len(conversation_history) >= self.max_conversation_turns:
            factors['conversation_length'] = 0.6
        elif len(conversation_history) >= 3:
            factors['conversation_length'] = 0.4
        else:
            factors['conversation_length'] = 0.1
        
        # Sentimiento
        if analysis['sentiment'] == 'negative':
            factors['sentiment'] = 0.6
        elif analysis['sentiment'] == 'urgent':
            factors['sentiment'] = 0.8
        else:
            factors['sentiment'] = 0.2
        
        # Palabras clave de escalación
        escalation_count = sum(1 for keyword in self.escalation_keywords if keyword in message.lower())
        if escalation_count > 0:
            factors['keywords'] = min(0.8, escalation_count * 0.3)
        
        total_score = sum(factors.values()) / len(factors)
        decision['confidence'] = total_score
        
        if total_score >= 0.6:
            decision['should_create'] = True
            decision['reason'] = 'Alta urgencia, complejidad o escalación detectada'
            decision['priority'] = 'high' if total_score >= 0.8 else 'medium'
        elif total_score >= 0.4:
            decision['should_create'] = True
            decision['reason'] = 'Conversación prolongada o complejidad media'
            decision['priority'] = 'medium'
        else:
            decision['should_create'] = False
            decision['reason'] = 'Consulta simple que puede resolverse por chat'
        
        return decision
    
    def _get_agent_response(self, message: str, analysis: Dict[str, Any], 
                           conversation_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            if self.ai_orchestrator:
                try:
                    response = self.ai_orchestrator.generate_support_response(message)
                    if response.get('success'):
                        return {
                            'content': response.get('content', 'Respuesta no disponible'),
                            'type': 'ai_response',
                            'agent_used': response.get('agent_name', 'AI General'),
                            'confidence': response.get('confidence', 0.7)
                        }
                except Exception as e:
                    logger.warning(f'Error con AI Orchestrator: {e}')
            
            if self.crew_ai_simple and self.crew_ai_simple.is_available():
                try:
                    response = self.crew_ai_simple.process_message(message)
                    if response.get('success'):
                        return {
                            'content': response.get('response', 'Respuesta no disponible'),
                            'type': 'crew_ai_response',
                            'agent_used': response.get('agent_name', 'CrewAI'),
                            'confidence': response.get('confidence', 0.6)
                        }
                except Exception as e:
                    logger.warning(f'Error con CrewAI: {e}')
            
            return {
                'content': 'Entiendo tu consulta. Déjame analizarla y te proporcionaré la mejor respuesta posible.',
                'type': 'default_response',
                'agent_used': 'Sistema General',
                'confidence': 0.5
            }
            
        except Exception as e:
            logger.error(f'Error obteniendo respuesta de agente: {e}')
            return {
                'content': 'Lo siento, estoy teniendo dificultades para procesar tu consulta. Te sugiero crear un ticket para que nuestro equipo te ayude.',
                'type': 'error_response',
                'agent_used': 'Sistema',
                'confidence': 0.0
            }
    
    def _create_ticket_if_needed(self, user_message: str, user_id: str, user_email: str,
                                conversation_history: List[Dict[str, Any]], 
                                agent_response: Dict[str, Any]) -> Dict[str, Any]:
        try:
            ticket_result = self.osticket_chat.create_ticket_from_chat(
                user_message=user_message,
                user_id=user_id,
                user_email=user_email,
                conversation_context=conversation_history,
                agent_id=agent_response.get('agent_used', 'Sistema')
            )
            
            if ticket_result['success']:
                self.osticket_chat.add_response_to_ticket(
                    ticket_id=ticket_result['ticket_id'],
                    response_message=agent_response['content']
                )
                
                logger.info(f'✅ Ticket creado exitosamente: {ticket_result["ticket_number"]}')
                return ticket_result
            else:
                logger.error(f'❌ Error creando ticket: {ticket_result.get("error")}')
                return ticket_result
                
        except Exception as e:
            logger.error(f'Error creando ticket: {e}')
            return {
                'success': False,
                'error': str(e)
            }
    
    def _prepare_final_response(self, agent_response: Dict[str, Any], ticket_info: Dict[str, Any],
                               analysis: Dict[str, Any], conversation_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        response = agent_response.copy()
        
        if ticket_info and ticket_info.get('success'):
            ticket_number = ticket_info.get('ticket_number', 'N/A')
            department = ticket_info.get('department', 'Soporte')
            
            response['content'] += f'\n\n📋 **Ticket Creado**\n'
            response['content'] += f'• **Número**: {ticket_number}\n'
            response['content'] += f'• **Departamento**: {department}\n'
            response['content'] += f'• **Estado**: Abierto\n\n'
            response['content'] += 'Nuestro equipo revisará tu consulta y te responderá lo antes posible. '
            response['content'] += 'Puedes hacer seguimiento de tu ticket en el sistema de soporte.'
            
            response['ticket_created'] = True
            response['ticket_number'] = ticket_number
            response['ticket_id'] = ticket_info.get('ticket_id')
        
        if len(conversation_history) >= 3:
            response['content'] += '\n\n💡 **Sugerencia**: Si tienes más consultas, considera crear un ticket para un seguimiento más detallado.'
        
        return response
    
    def _update_conversation_history(self, history: List[Dict[str, Any]], user_message: str,
                                   response: Dict[str, Any], ticket_info: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        updated_history = history.copy()
        
        updated_history.append({
            'role': 'user',
            'content': user_message,
            'timestamp': timezone.now().isoformat(),
            'type': 'message'
        })
        
        updated_history.append({
            'role': 'assistant',
            'content': response['content'],
            'timestamp': timezone.now().isoformat(),
            'type': 'response',
            'agent_used': response.get('agent_used', 'Sistema'),
            'confidence': response.get('confidence', 0.0)
        })
        
        if ticket_info and ticket_info.get('success'):
            updated_history.append({
                'role': 'system',
                'content': f'Ticket creado: {ticket_info.get("ticket_number", "N/A")}',
                'timestamp': timezone.now().isoformat(),
                'type': 'ticket_creation',
                'ticket_info': ticket_info
            })
        
        max_history = 20
        if len(updated_history) > max_history:
            updated_history = updated_history[-max_history:]
        
        return updated_history
    
    # Métodos auxiliares
    def _determine_urgency(self, message: str) -> str:
        message_lower = message.lower()
        high_urgency = ['urgente', 'crítico', 'error', 'falla', 'no funciona', 'bloqueado', 'emergencia']
        medium_urgency = ['problema', 'ayuda', 'consulta', 'duda', 'soporte']
        
        if any(keyword in message_lower for keyword in high_urgency):
            return 'high'
        elif any(keyword in message_lower for keyword in medium_urgency):
            return 'medium'
        else:
            return 'low'
    
    def _determine_complexity(self, message: str) -> str:
        message_lower = message.lower()
        complex_keywords = ['configuración', 'instalación', 'error', 'problema', 'falla', 'sistema']
        simple_keywords = ['consulta', 'duda', 'información', 'ayuda']
        
        complex_count = sum(1 for keyword in complex_keywords if keyword in message_lower)
        simple_count = sum(1 for keyword in simple_keywords if keyword in message_lower)
        
        if complex_count > simple_count:
            return 'high'
        elif complex_count == simple_count:
            return 'medium'
        else:
            return 'low'
    
    def _determine_department(self, message: str) -> str:
        message_lower = message.lower()
        dept_keywords = {
            'technical': ['configuración', 'instalación', 'error', 'sistema', 'software'],
            'billing': ['factura', 'pago', 'cobro', 'precio', 'tarifa'],
            'sales': ['producto', 'venta', 'cotización', 'precio', 'características']
        }
        
        for dept, keywords in dept_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                return dept
        
        return 'general'
    
    def _extract_keywords(self, message: str) -> List[str]:
        clean_message = re.sub(r'[^\w\s]', '', message.lower())
        words = clean_message.split()
        common_words = ['el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'le', 'da', 'su', 'por', 'son', 'con', 'para', 'al', 'del', 'los', 'una', 'como', 'pero', 'sus', 'me', 'hasta', 'hay', 'donde', 'han', 'quien', 'están', 'estado', 'desde', 'todo', 'nos', 'durante', 'todos', 'uno', 'les', 'ni', 'contra', 'otros', 'ese', 'eso', 'ante', 'ellos', 'e', 'esto', 'mí', 'antes', 'algunos', 'qué', 'unos', 'yo', 'otro', 'otras', 'otra', 'él', 'tanto', 'esa', 'estos', 'mucho', 'quienes', 'nada', 'muchos', 'cual', 'poco', 'ella', 'estar', 'estas', 'algunas', 'algo', 'nosotros']
        keywords = [word for word in words if word not in common_words and len(word) > 3]
        return keywords[:10]
    
    def _analyze_sentiment(self, message: str) -> str:
        message_lower = message.lower()
        positive_words = ['gracias', 'excelente', 'bueno', 'perfecto', 'genial', 'ayuda']
        negative_words = ['problema', 'error', 'falla', 'no funciona', 'molesto', 'frustrado', 'enojado']
        urgent_words = ['urgente', 'crítico', 'emergencia', 'ayuda', 'socorro']
        
        positive_count = sum(1 for word in positive_words if word in message_lower)
        negative_count = sum(1 for word in negative_words if word in message_lower)
        urgent_count = sum(1 for word in urgent_words if word in message_lower)
        
        if urgent_count > 0:
            return 'urgent'
        elif negative_count > positive_count:
            return 'negative'
        elif positive_count > negative_count:
            return 'positive'
        else:
            return 'neutral'
    
    def _requires_human_intervention(self, analysis: Dict[str, Any]) -> bool:
        if analysis.get('urgency_level') == 'high':
            return True
        if analysis.get('sentiment') in ['negative', 'urgent']:
            return True
        if analysis.get('complexity_level') == 'high':
            return True
        if analysis.get('conversation_length', 0) >= self.max_conversation_turns:
            return True
        return False
    
    def _generate_session_id(self) -> str:
        import uuid
        return str(uuid.uuid4())

# Instancia global
_chat_multiagent_system = None

def get_chat_multiagent_system() -> ChatMultiAgentSystem:
    global _chat_multiagent_system
    if _chat_multiagent_system is None:
        _chat_multiagent_system = ChatMultiAgentSystem()
    return _chat_multiagent_system

def test_chat_multiagent_system() -> Dict[str, Any]:
    try:
        chat_system = get_chat_multiagent_system()
        
        test_messages = [
            'Hola, ¿cómo estás?',
            'Tengo un problema con la configuración del sistema',
            'El error persiste y es urgente',
            'Necesito ayuda inmediata'
        ]
        
        conversation_history = []
        user_id = 'test_user_123'
        user_email = 'test@example.com'
        
        results = []
        
        for i, message in enumerate(test_messages):
            result = chat_system.process_message(
                message, user_id, user_email, conversation_history
            )
            
            if result['success']:
                results.append({
                    'message': message,
                    'response': result['response']['content'][:100] + '...',
                    'ticket_created': result.get('ticket_created', False),
                    'ticket_number': result.get('ticket_info', {}).get('ticket_number')
                })
                
                conversation_history = result.get('conversation_history', [])
            else:
                results.append({
                    'message': message,
                    'error': result.get('error', 'Error desconocido')
                })
        
        return {
            'success': True,
            'results': results,
            'total_messages': len(test_messages),
            'tickets_created': sum(1 for r in results if r.get('ticket_created')),
            'message': 'Sistema de chat multiagente probado exitosamente'
        }
        
    except Exception as e:
        logger.error(f'Error probando sistema de chat multiagente: {e}')
        return {
            'success': False,
            'error': str(e),
            'details': 'Error inesperado durante la prueba'
        }
