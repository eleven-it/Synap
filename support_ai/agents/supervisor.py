"""
Agente Supervisor - Coordina y enruta mensajes a agentes especializados usando LLMs reales
"""
import time
import logging
import json
from typing import Dict, List, Any, Optional
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from .facturacion import FacturacionAgent
from .configuracion import ConfiguracionAgent
from .ventas import VentasAgent
from .inventario import InventarioAgent
from .multimodal import MultimodalAgent
from .voz import VozAgent
from .knowledge_base import knowledge_base_agent
from .onboarding import onboarding_agent
from .proactive import proactive_agent
from .continuous_learning import continuous_learning_agent
from .coaching import coaching_agent
from ..llm_integration import llm_client

logger = logging.getLogger(__name__)


class SupervisorAgent:
    """
    Agente supervisor que coordina y enruta mensajes a agentes especializados.
    Evalúa la confianza de las respuestas y decide cuándo escalar a humanos.
    """
    
    def __init__(self):
        self.agents = {
            'facturacion': FacturacionAgent(),
            'configuracion': ConfiguracionAgent(),
            'ventas': VentasAgent(),
            'inventario': InventarioAgent(),
            'multimodal': MultimodalAgent(),
            'voz': VozAgent(),
        }
        
        # Palabras clave para enrutamiento
        self.routing_keywords = {
            'facturacion': [
                'factura', 'facturación', 'comprobante', 'afip', 'iva', 'impuesto',
                'fiscal', 'monotributo', 'responsable inscripto', 'cuit', 'cae',
                'caea', 'fecha de vencimiento', 'pago', 'cobro', 'deuda'
            ],
            'configuracion': [
                'configurar', 'configuración', 'ajustes', 'parámetros', 'setup',
                'instalación', 'config', 'preferencias', 'opciones', 'menú',
                'perfil', 'usuario', 'contraseña', 'acceso', 'permisos'
            ],
            'ventas': [
                'venta', 'vender', 'cliente', 'prospecto', 'cotización', 'presupuesto',
                'pedido', 'orden', 'carrito', 'checkout', 'pago', 'descuento',
                'promoción', 'oferta', 'precio', 'producto', 'servicio'
            ],
            'inventario': [
                'stock', 'inventario', 'producto', 'mercadería', 'código', 'barcode',
                'categoría', 'proveedor', 'entrada', 'salida', 'movimiento',
                'ajuste', 'faltante', 'sobrante', 'valorización'
            ]
        }
        
        # Umbrales de confianza
        self.confidence_threshold = 0.7
        self.escalation_threshold = 0.3
        
        # Contador de conversaciones por ticket
        self.conversation_counters = {}
    
    def process_message(self, ticket, message: str, attachments: List = None) -> Dict[str, Any]:
        """
        Procesa un mensaje y determina la mejor respuesta.
        
        Args:
            ticket: Ticket de soporte asociado
            message: Mensaje del usuario
            attachments: Lista de archivos adjuntos
            
        Returns:
            Dict con la respuesta y metadatos
        """
        start_time = time.time()
        
        try:
            # Verificar si es una consulta de onboarding
            if self._is_onboarding_request(message):
                return self._handle_onboarding_request(ticket, message)
            
            # Verificar si es una consulta de base de conocimientos
            if self._is_knowledge_request(message):
                return self._handle_knowledge_request(ticket, message)
            
            # Verificar si es una solicitud de coaching
            if self._is_coaching_request(message):
                return self._handle_coaching_request(ticket, message)
            
            # Verificar si es una solicitud de análisis proactivo
            if self._is_proactive_request(message):
                return self._handle_proactive_request(ticket, message)
            
            # Determinar el agente más apropiado
            agent_type = self._route_message(message, attachments)
            
            # Procesar con el agente seleccionado
            if agent_type in self.agents:
                agent = self.agents[agent_type]
                response = agent.process(message, ticket, attachments)
            else:
                # Respuesta genérica si no se puede enrutar
                response = self._generate_generic_response(message)
            
            # Evaluar confianza y escalamiento
            confidence = response.get('confidence', 0.5)
            should_escalate = self._should_escalate(ticket, confidence, message)
            
            # Actualizar contador de conversaciones
            if ticket:
                ticket_id = str(ticket.id)
                self.conversation_counters[ticket_id] = self.conversation_counters.get(ticket_id, 0) + 1
            
            processing_time = time.time() - start_time
            
            result = {
                'message': response['message'],
                'agent_used': agent_type,
                'confidence': confidence,
                'processing_time': processing_time,
                'should_escalate': should_escalate,
                'escalation_reason': response.get('escalation_reason', ''),
                'suggestions': response.get('suggestions', []),
                'metadata': response.get('metadata', {})
            }
            
            # Si debe escalar, actualizar el ticket
            if should_escalate and ticket:
                self._escalate_ticket(ticket, response.get('escalation_reason', 'Baja confianza en respuesta'))
            
            logger.info(f"Supervisor processed message in {processing_time:.2f}s, confidence: {confidence:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Error in supervisor processing: {str(e)}")
            return {
                'message': _("Lo siento, he tenido un problema procesando tu mensaje. Un agente humano te contactará pronto."),
                'agent_used': 'supervisor',
                'confidence': 0.0,
                'processing_time': time.time() - start_time,
                'should_escalate': True,
                'escalation_reason': f'Error en procesamiento: {str(e)}',
                'suggestions': [],
                'metadata': {}
            }
    
    def _route_message(self, message: str, attachments: List = None) -> str:
        """
        Determina el agente más apropiado para procesar el mensaje usando LLM.
        
        Args:
            message: Mensaje del usuario
            attachments: Archivos adjuntos
            
        Returns:
            Tipo de agente a usar
        """
        # Si hay archivos adjuntos, usar agente multimodal
        if attachments:
            return 'multimodal'
        
        try:
            # Usar LLM para clasificar la intención
            intent_result = llm_client.classify_intent(message)
            intent = intent_result.get('intent', 'configuracion')
            confidence = intent_result.get('confidence', 0.5)
            
            # Mapear intención a agente
            intent_to_agent = {
                'facturacion': 'facturacion',
                'configuracion': 'configuracion', 
                'ventas': 'ventas',
                'inventario': 'inventario',
                'soporte_general': 'configuracion',
                'escalacion': 'configuracion',
                'consulta': 'configuracion'
            }
            
            agent_type = intent_to_agent.get(intent, 'configuracion')
            
            # Si la confianza del LLM es baja, usar palabras clave como fallback
            if confidence < 0.6:
                return self._route_with_keywords(message)
            
            return agent_type
            
        except Exception as e:
            logger.error(f"Error in LLM routing: {e}")
            # Fallback a palabras clave
            return self._route_with_keywords(message)
    
    def _route_with_keywords(self, message: str) -> str:
        """Enrutamiento basado en palabras clave como fallback"""
        message_lower = message.lower()
        
        # Contar coincidencias de palabras clave por agente
        agent_scores = {}
        
        for agent_type, keywords in self.routing_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in message_lower:
                    score += 1
            
            if score > 0:
                agent_scores[agent_type] = score
        
        # Si hay coincidencias claras, usar el agente con más coincidencias
        if agent_scores:
            best_agent = max(agent_scores.items(), key=lambda x: x[1])[0]
            return best_agent
        
        # Si no hay coincidencias claras, usar configuración como fallback
        return 'configuracion'
    
    def _should_escalate(self, ticket, confidence: float, message: str) -> bool:
        """
        Determina si el ticket debe escalarse a un agente humano.
        
        Args:
            ticket: Ticket de soporte
            confidence: Nivel de confianza de la respuesta
            message: Mensaje original del usuario
            
        Returns:
            True si debe escalar, False en caso contrario
        """
        if not ticket:
            return False
        
        ticket_id = str(ticket.id)
        conversation_count = self.conversation_counters.get(ticket_id, 0)
        
        # Escalar si la confianza es muy baja
        if confidence < self.escalation_threshold:
            return True
        
        # Escalar si hay muchas conversaciones sin resolución
        if conversation_count > 5:
            return True
        
        # Escalar si el mensaje contiene palabras de frustración
        frustration_keywords = [
            'frustrado', 'molesto', 'enojado', 'cansado', 'urgente', 'crítico',
            'problema grave', 'no funciona', 'error', 'falla', 'bug'
        ]
        
        message_lower = message.lower()
        for keyword in frustration_keywords:
            if keyword in message_lower:
                return True
        
        return False
    
    def _escalate_ticket(self, ticket, reason: str):
        """
        Escala un ticket a un agente humano.
        
        Args:
            ticket: Ticket a escalar
            reason: Razón de escalamiento
        """
        try:
            ticket.status = 'waiting_agent'
            ticket.escalation_reason = reason
            ticket.save()
            
            logger.info(f"Ticket {ticket.ticket_number} escalated: {reason}")
            
        except Exception as e:
            logger.error(f"Error escalating ticket: {str(e)}")
    
    def _generate_generic_response(self, message: str) -> Dict[str, Any]:
        """
        Genera una respuesta genérica cuando no se puede enrutar a un agente específico.
        
        Args:
            message: Mensaje del usuario
            
        Returns:
            Respuesta genérica
        """
        return {
            'message': _(
                "Entiendo tu consulta. Te ayudo a conectarte con el área especializada. "
                "¿Podrías proporcionarme más detalles sobre tu problema específico?"
            ),
            'confidence': 0.4,
            'suggestions': [
                _("¿Es un problema de facturación?"),
                _("¿Necesitas ayuda con la configuración?"),
                _("¿Tienes dudas sobre ventas?"),
                _("¿Es algo relacionado con inventario?")
            ],
            'metadata': {
                'response_type': 'generic',
                'requires_clarification': True
            }
        }
    
    def get_agent_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado de todos los agentes.
        
        Returns:
            Dict con el estado de cada agente
        """
        status = {}
        
        for agent_type, agent in self.agents.items():
            try:
                agent_status = agent.get_status()
                status[agent_type] = agent_status
            except Exception as e:
                logger.error(f"Error getting status for {agent_type}: {str(e)}")
                status[agent_type] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return status
    
    def train_agent(self, agent_type: str, training_data: List[Dict]) -> bool:
        """
        Entrena un agente específico con nuevos datos.
        
        Args:
            agent_type: Tipo de agente a entrenar
            training_data: Datos de entrenamiento
            
        Returns:
            True si el entrenamiento fue exitoso
        """
        try:
            if agent_type in self.agents:
                agent = self.agents[agent_type]
                return agent.train(training_data)
            else:
                logger.error(f"Unknown agent type: {agent_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error training agent {agent_type}: {str(e)}")
            return False
    
    def update_routing_keywords(self, agent_type: str, keywords: List[str]):
        """
        Actualiza las palabras clave de enrutamiento para un agente.
        
        Args:
            agent_type: Tipo de agente
            keywords: Nueva lista de palabras clave
        """
        if agent_type in self.routing_keywords:
            self.routing_keywords[agent_type] = keywords
            logger.info(f"Updated routing keywords for {agent_type}")
        else:
            logger.error(f"Unknown agent type for keyword update: {agent_type}")
    
    def get_conversation_summary(self, ticket) -> str:
        """
        Genera un resumen de la conversación para agentes humanos.
        
        Args:
            ticket: Ticket de soporte
            
        Returns:
            Resumen de la conversación
        """
        try:
            conversations = ticket.conversations.all().order_by('created_at')
            
            summary_parts = [
                f"Ticket: {ticket.ticket_number}",
                f"Cliente: {ticket.customer.get_full_name() or ticket.customer.username}",
                f"Problema inicial: {ticket.description}",
                f"Estado actual: {ticket.get_status_display()}",
                f"Confianza IA: {ticket.ai_confidence:.2f}",
                "\nConversación:"
            ]
            
            for conv in conversations:
                timestamp = conv.created_at.strftime("%H:%M")
                if conv.message_type == 'user':
                    summary_parts.append(f"[{timestamp}] Cliente: {conv.content}")
                elif conv.message_type == 'ai':
                    summary_parts.append(f"[{timestamp}] IA ({conv.ai_agent_used}): {conv.content}")
                elif conv.message_type == 'agent':
                    summary_parts.append(f"[{timestamp}] Agente: {conv.content}")
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            logger.error(f"Error generating conversation summary: {str(e)}")
            return f"Error generando resumen: {str(e)}"
    
    def _is_onboarding_request(self, message: str) -> bool:
        """Verifica si el mensaje es una solicitud de onboarding"""
        onboarding_keywords = [
            'onboarding', 'tutorial', 'guía', 'ayuda', 'cómo empezar',
            'primeros pasos', 'configuración inicial', 'bienvenida',
            'capacitación', 'entrenamiento', 'aprender'
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in onboarding_keywords)
    
    def _is_knowledge_request(self, message: str) -> bool:
        """Verifica si el mensaje es una solicitud de conocimiento"""
        knowledge_keywords = [
            'buscar', 'encontrar', 'artículo', 'documentación', 'ayuda',
            'cómo', 'guía', 'manual', 'tutorial', 'información',
            'base de conocimientos', 'kb', 'faq'
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in knowledge_keywords)
    
    def _handle_onboarding_request(self, ticket, message: str) -> Dict[str, Any]:
        """Maneja solicitudes de onboarding"""
        try:
            # Determinar tipo de usuario
            user_type = 'new_customer'  # Por defecto
            if ticket and ticket.user:
                # Aquí se podría determinar el tipo basado en el perfil del usuario
                user_type = 'new_customer'
            
            # Obtener contenido de onboarding
            content = onboarding_agent.get_personalized_content(
                user_type=user_type,
                experience_level='beginner',
                step=1
            )
            
            if content:
                return {
                    'message': f"¡Te ayudo con el onboarding! {content['content']}",
                    'agent_used': 'onboarding',
                    'confidence': 0.9,
                    'onboarding_data': content,
                    'suggestions': [
                        'Completar configuración inicial',
                        'Revisar tutoriales básicos',
                        'Configurar preferencias'
                    ]
                }
            else:
                return {
                    'message': "Te ayudo a comenzar con Synap. ¿Qué te gustaría aprender primero?",
                    'agent_used': 'onboarding',
                    'confidence': 0.8,
                    'suggestions': [
                        'Configuración básica',
                        'Crear primera factura',
                        'Configurar empresa'
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error handling onboarding request: {e}")
            return {
                'message': "Te ayudo con el onboarding. ¿En qué puedo asistirte?",
                'agent_used': 'onboarding',
                'confidence': 0.7
            }
    
    def _handle_knowledge_request(self, ticket, message: str) -> Dict[str, Any]:
        """Maneja solicitudes de base de conocimientos"""
        try:
            # Buscar en la base de conocimientos
            search_results = knowledge_base_agent.search_knowledge(message)
            
            if search_results:
                best_match = search_results[0]
                return {
                    'message': f"Encontré información relevante: **{best_match['title']}**\n\n{best_match['content']}",
                    'agent_used': 'knowledge_base',
                    'confidence': best_match['relevance_score'],
                    'knowledge_results': search_results[:3],
                    'suggestions': [
                        'Ver artículo completo',
                        'Buscar más información',
                        'Contactar soporte'
                    ]
                }
            else:
                # Si no encuentra resultados, sugerir crear artículo
                return {
                    'message': "No encontré información específica sobre tu consulta. ¿Te gustaría que busque en otra categoría o que cree un artículo sobre este tema?",
                    'agent_used': 'knowledge_base',
                    'confidence': 0.6,
                    'suggestions': [
                        'Buscar en otra categoría',
                        'Solicitar nuevo artículo',
                        'Contactar soporte directo'
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error handling knowledge request: {e}")
            return {
                'message': "Estoy buscando información relevante para tu consulta...",
                'agent_used': 'knowledge_base',
                'confidence': 0.5
            }
    
    def _is_coaching_request(self, message: str) -> bool:
        """Verifica si el mensaje es una solicitud de coaching"""
        coaching_keywords = [
            'coaching', 'ayuda agente', 'sugerencias', 'feedback',
            'mejorar', 'consejos', 'recomendaciones', 'asistencia agente'
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in coaching_keywords)
    
    def _is_proactive_request(self, message: str) -> bool:
        """Verifica si el mensaje es una solicitud de análisis proactivo"""
        proactive_keywords = [
            'análisis', 'patrones', 'tendencias', 'predicción',
            'proactivo', 'preventivo', 'insights', 'métricas'
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in proactive_keywords)
    
    def _handle_coaching_request(self, ticket, message: str) -> Dict[str, Any]:
        """Maneja solicitudes de coaching"""
        try:
            if not ticket:
                return {
                    'message': "Para proporcionar coaching, necesito un ticket activo.",
                    'agent_used': 'coaching',
                    'confidence': 0.6
                }
            
            # Obtener coaching en tiempo real
            coaching_data = coaching_agent.provide_real_time_coaching(
                agent_id=ticket.assigned_agent.id if ticket.assigned_agent else 1,
                ticket_id=ticket.id
            )
            
            if 'error' in coaching_data:
                return {
                    'message': "No pude generar coaching en este momento. ¿Puedes ser más específico?",
                    'agent_used': 'coaching',
                    'confidence': 0.5
                }
            
            # Generar respuesta con sugerencias
            suggestions = coaching_data.get('coaching_suggestions', [])
            if suggestions:
                suggestion_text = "\n".join([
                    f"• **{s.get('title', '')}**: {s.get('description', '')}"
                    for s in suggestions[:3]
                ])
                
                return {
                    'message': f"**Coaching en Tiempo Real:**\n\n{suggestion_text}",
                    'agent_used': 'coaching',
                    'confidence': 0.8,
                    'coaching_data': coaching_data
                }
            else:
                return {
                    'message': "No tengo sugerencias específicas de coaching en este momento.",
                    'agent_used': 'coaching',
                    'confidence': 0.6
                }
                
        except Exception as e:
            logger.error(f"Error handling coaching request: {e}")
            return {
                'message': "Error al procesar solicitud de coaching.",
                'agent_used': 'coaching',
                'confidence': 0.4
            }
    
    def _handle_proactive_request(self, ticket, message: str) -> Dict[str, Any]:
        """Maneja solicitudes de análisis proactivo"""
        try:
            if not ticket or not ticket.customer:
                return {
                    'message': "Para análisis proactivo, necesito información del cliente.",
                    'agent_used': 'proactive',
                    'confidence': 0.5
                }
            
            # Analizar patrones del usuario
            patterns = proactive_agent.analyze_user_patterns(ticket.customer.id)
            
            if not patterns:
                return {
                    'message': "No encontré patrones específicos para análisis proactivo.",
                    'agent_used': 'proactive',
                    'confidence': 0.5
                }
            
            # Generar respuesta con insights
            potential_issues = patterns.get('potential_issues', [])
            recommendations = patterns.get('recommendations', [])
            
            response_parts = ["**Análisis Proactivo:**"]
            
            if potential_issues:
                response_parts.append("\n**Problemas Potenciales:**")
                for issue in potential_issues[:2]:
                    response_parts.append(f"• {issue.get('description', '')}")
            
            if recommendations:
                response_parts.append("\n**Recomendaciones:**")
                for rec in recommendations[:2]:
                    response_parts.append(f"• {rec.get('title', '')}: {rec.get('description', '')}")
            
            return {
                'message': "\n".join(response_parts),
                'agent_used': 'proactive',
                'confidence': 0.7,
                'analysis_data': patterns
            }
                
        except Exception as e:
            logger.error(f"Error handling proactive request: {e}")
            return {
                'message': "Error al procesar análisis proactivo.",
                'agent_used': 'proactive',
                'confidence': 0.4
            } 