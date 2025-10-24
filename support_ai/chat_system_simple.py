"""
Sistema de Chat Multiagente Simplificado
Usa el nuevo adaptador de Ollama con requests
"""

import logging
import json
from typing import Dict, List, Any, Optional
from django.utils import timezone
from .osticket_chat_integration import get_osticket_chat_integration
from .ollama_adapter_requests import get_ollama_adapter_requests
import re

logger = logging.getLogger(__name__)


class ChatSystemSimple:
    """
    Sistema de chat simplificado que integra con osTicket y Ollama
    """
    
    def __init__(self):
        self.osticket_chat = get_osticket_chat_integration()
        self.ollama = get_ollama_adapter_requests()
        
        # Configuración del sistema
        self.max_conversation_turns = 5
        self.escalation_keywords = [
            'urgente', 'crítico', 'error', 'falla', 'no funciona', 'bloqueado',
            'problema', 'ayuda', 'consulta', 'duda', 'soporte', 'asistencia'
        ]
    
    def process_message(
        self, 
        user_message: str, 
        user_id: str, 
        user_email: str,
        conversation_history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Procesa un mensaje del usuario
        """
        try:
            if conversation_history is None:
                conversation_history = []
            
            # 1. Analizar el mensaje
            analysis = self._analyze_message(user_message, conversation_history)
            
            # 2. Determinar si crear ticket
            should_create_ticket = self._should_create_ticket(user_message, conversation_history, analysis)
            
            # 3. Generar respuesta con Ollama
            ollama_response = self._get_ollama_response(user_message, analysis)
            
            # 4. Crear ticket si es necesario
            ticket_info = None
            if should_create_ticket:
                ticket_result = self._create_ticket(
                    user_message, user_id, user_email, conversation_history, ollama_response
                )
                if ticket_result['success']:
                    ticket_info = ticket_result
                    ollama_response['ticket_created'] = True
                    ollama_response['ticket_number'] = ticket_result['ticket_number']
            
            # 5. Preparar respuesta final
            final_response = self._prepare_final_response(ollama_response, ticket_info, analysis)
            
            # 6. Actualizar historial
            updated_history = self._update_history(conversation_history, user_message, final_response, ticket_info)
            
            return {
                'success': True,
                'response': final_response,
                'ticket_created': ticket_info is not None,
                'ticket_info': ticket_info,
                'conversation_history': updated_history,
                'analysis': analysis
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
    
    def _analyze_message(self, message: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analiza el mensaje del usuario"""
        message_lower = message.lower()
        
        analysis = {
            'urgency': 'low',
            'complexity': 'low',
            'sentiment': 'neutral',
            'keywords': [],
            'conversation_length': len(history)
        }
        
        # Urgencia
        high_urgency = ['urgente', 'crítico', 'error', 'falla', 'no funciona', 'bloqueado', 'emergencia']
        medium_urgency = ['problema', 'ayuda', 'consulta', 'duda', 'soporte']
        
        if any(keyword in message_lower for keyword in high_urgency):
            analysis['urgency'] = 'high'
        elif any(keyword in message_lower for keyword in medium_urgency):
            analysis['urgency'] = 'medium'
        
        # Complejidad
        complex_keywords = ['configuración', 'instalación', 'error', 'problema', 'falla', 'sistema']
        if any(keyword in message_lower for keyword in complex_keywords):
            analysis['complexity'] = 'high'
        
        # Sentimiento
        negative_words = ['problema', 'error', 'falla', 'no funciona', 'molesto', 'frustrado']
        if any(keyword in message_lower for keyword in negative_words):
            analysis['sentiment'] = 'negative'
        
        # Palabras clave
        clean_message = re.sub(r'[^\w\s]', '', message_lower)
        words = clean_message.split()
        common_words = ['el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'no']
        analysis['keywords'] = [word for word in words if word not in common_words and len(word) > 3][:5]
        
        return analysis
    
    def _should_create_ticket(self, message: str, history: List[Dict[str, Any]], analysis: Dict[str, Any]) -> bool:
        """Determina si se debe crear un ticket"""
        # Alta urgencia
        if analysis['urgency'] == 'high':
            return True
        
        # Sentimiento negativo
        if analysis['sentiment'] == 'negative':
            return True
        
        # Alta complejidad
        if analysis['complexity'] == 'high':
            return True
        
        # Conversación muy larga
        if len(history) >= self.max_conversation_turns:
            return True
        
        # Palabras clave de escalación
        if any(keyword in message.lower() for keyword in self.escalation_keywords):
            return True
        
        return False
    
    def _get_ollama_response(self, message: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Obtiene respuesta de Ollama"""
        try:
            # Crear prompt contextual
            system_prompt = self._create_system_prompt(analysis)
            
            context = {
                'system_prompt': system_prompt,
                'temperature': 0.7,
                'max_tokens': 300
            }
            
            result = self.ollama.generate_response(message, context)
            
            if result['success']:
                return {
                    'content': result['response'],
                    'type': 'ollama_response',
                    'model': result['model'],
                    'processing_time': result['processing_time']
                }
            else:
                # Fallback
                return {
                    'content': 'Entiendo tu consulta. Déjame analizarla y te proporcionaré la mejor respuesta posible.',
                    'type': 'fallback_response',
                    'model': 'fallback',
                    'processing_time': 0
                }
                
        except Exception as e:
            logger.error(f'Error con Ollama: {e}')
            return {
                'content': 'Lo siento, estoy teniendo dificultades para procesar tu consulta. Te sugiero crear un ticket para que nuestro equipo te ayude.',
                'type': 'error_response',
                'model': 'error',
                'processing_time': 0
            }
    
    def _create_system_prompt(self, analysis: Dict[str, Any]) -> str:
        """Crea un prompt del sistema basado en el análisis"""
        prompt = "Eres un asistente de soporte técnico amigable y profesional. "
        
        if analysis['urgency'] == 'high':
            prompt += "El usuario tiene una consulta URGENTE. Responde de manera clara y directa. "
        
        if analysis['complexity'] == 'high':
            prompt += "La consulta es COMPLEJA. Proporciona explicaciones detalladas y paso a paso. "
        
        if analysis['sentiment'] == 'negative':
            prompt += "El usuario está FRUSTRADO. Sé empático y comprensivo. "
        
        prompt += "Responde siempre en español de manera clara, amigable y profesional. "
        prompt += "Si no puedes resolver completamente el problema, sugiere crear un ticket para seguimiento."
        
        return prompt
    
    def _create_ticket(self, user_message: str, user_id: str, user_email: str,
                       conversation_history: List[Dict[str, Any]], response: Dict[str, Any]) -> Dict[str, Any]:
        """Crea un ticket en osTicket"""
        try:
            ticket_result = self.osticket_chat.create_ticket_from_chat(
                user_message=user_message,
                user_id=user_id,
                user_email=user_email,
                conversation_context=conversation_history,
                agent_id=response.get('model', 'Ollama')
            )
            
            if ticket_result['success']:
                # Agregar respuesta del agente al ticket
                self.osticket_chat.add_response_to_ticket(
                    ticket_id=ticket_result['ticket_id'],
                    response_message=response['content']
                )
                
                logger.info(f'✅ Ticket creado: {ticket_result["ticket_number"]}')
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
    
    def _prepare_final_response(self, response: Dict[str, Any], ticket_info: Dict[str, Any], 
                               analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Prepara la respuesta final"""
        final_response = response.copy()
        
        if ticket_info and ticket_info.get('success'):
            ticket_number = ticket_info.get('ticket_number', 'N/A')
            department = ticket_info.get('department', 'Soporte')
            
            final_response['content'] += f'\n\n📋 **Ticket Creado**\n'
            final_response['content'] += f'• **Número**: {ticket_number}\n'
            final_response['content'] += f'• **Departamento**: {department}\n'
            final_response['content'] += f'• **Estado**: Abierto\n\n'
            final_response['content'] += 'Nuestro equipo revisará tu consulta y te responderá lo antes posible. '
            final_response['content'] += 'Puedes hacer seguimiento de tu ticket en el sistema de soporte.'
            
            final_response['ticket_created'] = True
            final_response['ticket_number'] = ticket_number
        
        return final_response
    
    def _update_history(self, history: List[Dict[str, Any]], user_message: str,
                       response: Dict[str, Any], ticket_info: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Actualiza el historial de conversación"""
        updated_history = history.copy()
        
        # Mensaje del usuario
        updated_history.append({
            'role': 'user',
            'content': user_message,
            'timestamp': timezone.now().isoformat()
        })
        
        # Respuesta del sistema
        updated_history.append({
            'role': 'assistant',
            'content': response['content'],
            'timestamp': timezone.now().isoformat(),
            'model': response.get('model', 'Sistema')
        })
        
        # Información del ticket si se creó
        if ticket_info and ticket_info.get('success'):
            updated_history.append({
                'role': 'system',
                'content': f'Ticket creado: {ticket_info.get("ticket_number", "N/A")}',
                'timestamp': timezone.now().isoformat()
            })
        
        # Mantener solo los últimos 20 mensajes
        if len(updated_history) > 20:
            updated_history = updated_history[-20:]
        
        return updated_history


# Instancia global
_chat_system_simple = None


def get_chat_system_simple() -> ChatSystemSimple:
    """Obtiene la instancia global del sistema de chat simplificado"""
    global _chat_system_simple
    
    if _chat_system_simple is None:
        _chat_system_simple = ChatSystemSimple()
    
    return _chat_system_simple


def test_chat_system_simple() -> Dict[str, Any]:
    """Prueba el sistema de chat simplificado"""
    try:
        chat_system = get_chat_system_simple()
        
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
            print(f'\n📝 Procesando mensaje {i+1}: {message[:50]}...')
            
            result = chat_system.process_message(
                message, user_id, user_email, conversation_history
            )
            
            if result['success']:
                response_content = result['response']['content'][:100] + '...'
                ticket_created = result.get('ticket_created', False)
                ticket_number = result.get('ticket_info', {}).get('ticket_number')
                
                results.append({
                    'message': message,
                    'response': response_content,
                    'ticket_created': ticket_created,
                    'ticket_number': ticket_number
                })
                
                print(f'   ✅ Respuesta: {response_content}')
                if ticket_created:
                    print(f'   🎫 Ticket creado: {ticket_number}')
                else:
                    print(f'   💬 Resuelto por chat')
                
                conversation_history = result.get('conversation_history', [])
            else:
                print(f'   ❌ Error: {result.get("error", "Error desconocido")}')
                results.append({
                    'message': message,
                    'error': result.get('error', 'Error desconocido')
                })
        
        return {
            'success': True,
            'results': results,
            'total_messages': len(test_messages),
            'tickets_created': sum(1 for r in results if r.get('ticket_created')),
            'message': 'Sistema de chat simplificado probado exitosamente'
        }
        
    except Exception as e:
        logger.error(f'Error probando sistema de chat: {e}')
        return {
            'success': False,
            'error': str(e)
        }
