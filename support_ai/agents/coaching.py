import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from django.utils import timezone
from ..models import (
    AgentCoaching, SupportTicket, Conversation, 
    CustomerProfile, AIAgent
)
from ..llm_integration import llm_client

logger = logging.getLogger(__name__)

class CoachingAgent:
    """Agente para coaching en tiempo real de agentes humanos"""
    
    def __init__(self):
        self.llm_client = llm_client
    
    def provide_real_time_coaching(self, agent_id: int, ticket_id: int, current_message: str = None) -> Dict[str, Any]:
        """
        Proporciona coaching en tiempo real durante una conversación
        """
        try:
            # Obtener información del ticket
            ticket = SupportTicket.objects.get(id=ticket_id)
            
            # Analizar el contexto actual
            context_analysis = self._analyze_conversation_context(ticket)
            
            # Generar sugerencias de coaching
            coaching_suggestions = self._generate_coaching_suggestions(
                agent_id, ticket, context_analysis, current_message
            )
            
            # Analizar tono y empatía
            tone_analysis = self._analyze_agent_tone(current_message) if current_message else {}
            
            # Generar feedback en tiempo real
            real_time_feedback = self._generate_real_time_feedback(
                context_analysis, tone_analysis, coaching_suggestions
            )
            
            return {
                'coaching_suggestions': coaching_suggestions,
                'tone_analysis': tone_analysis,
                'real_time_feedback': real_time_feedback,
                'context_summary': context_analysis.get('summary', ''),
                'priority_alerts': self._check_priority_alerts(ticket, context_analysis)
            }
            
        except Exception as e:
            logger.error(f"Error providing real-time coaching: {e}")
            return {'error': str(e)}
    
    def _analyze_conversation_context(self, ticket) -> Dict[str, Any]:
        """Analiza el contexto de la conversación"""
        try:
            # Obtener conversaciones del ticket
            conversations = Conversation.objects.filter(ticket=ticket).order_by('created_at')
            
            # Analizar sentimiento del cliente
            customer_sentiment = self._analyze_customer_sentiment(conversations)
            
            # Analizar progreso de la conversación
            conversation_progress = self._analyze_conversation_progress(conversations)
            
            # Identificar puntos clave
            key_points = self._identify_key_points(conversations)
            
            # Crear resumen del contexto
            context_summary = self._create_context_summary(ticket, conversations, customer_sentiment)
            
            return {
                'customer_sentiment': customer_sentiment,
                'conversation_progress': conversation_progress,
                'key_points': key_points,
                'summary': context_summary,
                'conversation_length': conversations.count(),
                'last_customer_message': self._get_last_customer_message(conversations)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing conversation context: {e}")
            return {}
    
    def _analyze_customer_sentiment(self, conversations) -> Dict[str, Any]:
        """Analiza el sentimiento del cliente"""
        try:
            customer_messages = [
                conv.content for conv in conversations 
                if conv.message_type == 'user'
            ]
            
            if not customer_messages:
                return {'overall_sentiment': 'neutral', 'trend': 'stable'}
            
            # Analizar sentimiento de todos los mensajes del cliente
            sentiment_scores = []
            for message in customer_messages:
                sentiment = self.llm_client.analyze_sentiment(message)
                sentiment_scores.append(sentiment)
            
            # Calcular sentimiento general
            avg_positive = sum(s.get('positive', 0) for s in sentiment_scores) / len(sentiment_scores)
            avg_negative = sum(s.get('negative', 0) for s in sentiment_scores) / len(sentiment_scores)
            avg_neutral = sum(s.get('neutral', 0) for s in sentiment_scores) / len(sentiment_scores)
            
            # Determinar sentimiento general
            if avg_positive > avg_negative and avg_positive > avg_neutral:
                overall_sentiment = 'positive'
            elif avg_negative > avg_positive and avg_negative > avg_neutral:
                overall_sentiment = 'negative'
            else:
                overall_sentiment = 'neutral'
            
            # Analizar tendencia
            if len(sentiment_scores) >= 2:
                recent_sentiment = sentiment_scores[-1]
                earlier_sentiment = sentiment_scores[0]
                
                recent_score = recent_sentiment.get('positive', 0) - recent_sentiment.get('negative', 0)
                earlier_score = earlier_sentiment.get('positive', 0) - earlier_sentiment.get('negative', 0)
                
                if recent_score > earlier_score + 0.2:
                    trend = 'improving'
                elif recent_score < earlier_score - 0.2:
                    trend = 'declining'
                else:
                    trend = 'stable'
            else:
                trend = 'stable'
            
            return {
                'overall_sentiment': overall_sentiment,
                'trend': trend,
                'positive_score': avg_positive,
                'negative_score': avg_negative,
                'neutral_score': avg_neutral,
                'frustration_level': avg_negative,
                'satisfaction_level': avg_positive
            }
            
        except Exception as e:
            logger.error(f"Error analyzing customer sentiment: {e}")
            return {'overall_sentiment': 'neutral', 'trend': 'stable'}
    
    def _analyze_conversation_progress(self, conversations) -> Dict[str, Any]:
        """Analiza el progreso de la conversación"""
        try:
            total_messages = conversations.count()
            
            if total_messages == 0:
                return {'stage': 'initial', 'progress': 0.0}
            
            # Determinar etapa de la conversación
            if total_messages <= 2:
                stage = 'initial'
                progress = 0.2
            elif total_messages <= 5:
                stage = 'exploration'
                progress = 0.4
            elif total_messages <= 8:
                stage = 'resolution'
                progress = 0.7
            else:
                stage = 'closing'
                progress = 0.9
            
            # Verificar si hay resolución
            has_resolution = any(
                'resuelto' in conv.content.lower() or 
                'solucionado' in conv.content.lower() or
                'gracias' in conv.content.lower()
                for conv in conversations
            )
            
            if has_resolution:
                stage = 'resolved'
                progress = 1.0
            
            return {
                'stage': stage,
                'progress': progress,
                'total_messages': total_messages,
                'has_resolution': has_resolution
            }
            
        except Exception as e:
            logger.error(f"Error analyzing conversation progress: {e}")
            return {'stage': 'initial', 'progress': 0.0}
    
    def _identify_key_points(self, conversations) -> List[Dict[str, Any]]:
        """Identifica puntos clave en la conversación"""
        try:
            key_points = []
            
            for i, conv in enumerate(conversations):
                if conv.message_type == 'user':
                    # Analizar si es un punto clave
                    content_lower = conv.content.lower()
                    
                    # Detectar problemas específicos
                    if any(word in content_lower for word in ['error', 'problema', 'no funciona', 'falla']):
                        key_points.append({
                            'type': 'problem_identified',
                            'message_index': i,
                            'description': 'Cliente identificó un problema específico',
                            'priority': 'high'
                        })
                    
                    # Detectar frustración
                    if any(word in content_lower for word in ['frustrado', 'molesto', 'cansado', 'enojado']):
                        key_points.append({
                            'type': 'frustration_detected',
                            'message_index': i,
                            'description': 'Cliente muestra frustración',
                            'priority': 'high'
                        })
                    
                    # Detectar satisfacción
                    if any(word in content_lower for word in ['gracias', 'perfecto', 'excelente', 'genial']):
                        key_points.append({
                            'type': 'satisfaction_expressed',
                            'message_index': i,
                            'description': 'Cliente expresa satisfacción',
                            'priority': 'medium'
                        })
            
            return key_points
            
        except Exception as e:
            logger.error(f"Error identifying key points: {e}")
            return []
    
    def _create_context_summary(self, ticket, conversations, customer_sentiment) -> str:
        """Crea un resumen del contexto"""
        try:
            # Crear resumen con LLM
            conversation_text = "\n".join([
                f"{conv.message_type}: {conv.content}" 
                for conv in conversations[:10]  # Últimas 10 conversaciones
            ])
            
            prompt = f"""
            Crea un resumen conciso del contexto de este ticket para coaching del agente:
            
            Ticket: {ticket.subject}
            Descripción: {ticket.description}
            Sentimiento del cliente: {customer_sentiment.get('overall_sentiment', 'neutral')}
            
            Conversación:
            {conversation_text}
            
            Responde con un resumen de 2-3 oraciones que incluya:
            - El problema principal
            - El estado emocional del cliente
            - Acciones recomendadas para el agente
            """
            
            response = self.llm_client.generate_response([
                {"role": "system", "content": "Eres un experto en coaching de agentes de soporte."},
                {"role": "user", "content": prompt}
            ], temperature=0.3)
            
            return response['content']
            
        except Exception as e:
            logger.error(f"Error creating context summary: {e}")
            return "Error al generar resumen del contexto"
    
    def _get_last_customer_message(self, conversations) -> Optional[str]:
        """Obtiene el último mensaje del cliente"""
        try:
            customer_messages = [
                conv for conv in conversations 
                if conv.message_type == 'user'
            ]
            
            if customer_messages:
                return customer_messages[-1].content
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting last customer message: {e}")
            return None
    
    def _generate_coaching_suggestions(self, agent_id: int, ticket, context_analysis: Dict[str, Any], current_message: str = None) -> List[Dict[str, Any]]:
        """Genera sugerencias de coaching"""
        try:
            suggestions = []
            
            # Sugerencias basadas en el sentimiento del cliente
            customer_sentiment = context_analysis.get('customer_sentiment', {})
            
            if customer_sentiment.get('overall_sentiment') == 'negative':
                suggestions.append({
                    'type': 'empathy',
                    'title': 'Mostrar Empatía',
                    'description': 'El cliente está frustrado. Muestra comprensión y empatía.',
                    'priority': 'high',
                    'example': 'Entiendo tu frustración. Vamos a resolver esto juntos.'
                })
            
            if customer_sentiment.get('frustration_level', 0) > 0.6:
                suggestions.append({
                    'type': 'urgency',
                    'title': 'Actuar con Urgencia',
                    'description': 'Cliente muy frustrado. Prioriza este ticket.',
                    'priority': 'critical',
                    'example': 'Este es un caso prioritario. Te ayudo inmediatamente.'
                })
            
            # Sugerencias basadas en el progreso de la conversación
            conversation_progress = context_analysis.get('conversation_progress', {})
            
            if conversation_progress.get('stage') == 'initial':
                suggestions.append({
                    'type': 'information_gathering',
                    'title': 'Recopilar Información',
                    'description': 'Estás en la etapa inicial. Haz preguntas específicas.',
                    'priority': 'medium',
                    'example': '¿Podrías darme más detalles sobre el problema?'
                })
            
            elif conversation_progress.get('stage') == 'exploration':
                suggestions.append({
                    'type': 'solution_offering',
                    'title': 'Ofrecer Soluciones',
                    'description': 'Ya tienes información. Ofrece soluciones específicas.',
                    'priority': 'medium',
                    'example': 'Basado en lo que me cuentas, te sugiero...'
                })
            
            # Sugerencias basadas en el tipo de problema
            ticket_intent = self.llm_client.classify_intent(f"{ticket.subject} {ticket.description}")
            intent_type = ticket_intent.get('intent', 'general')
            
            if intent_type == 'facturacion':
                suggestions.append({
                    'type': 'technical_guidance',
                    'title': 'Guía Técnica',
                    'description': 'Problema de facturación. Usa lenguaje técnico apropiado.',
                    'priority': 'medium',
                    'example': 'Vamos a revisar la configuración fiscal...'
                })
            
            elif intent_type == 'configuracion':
                suggestions.append({
                    'type': 'step_by_step',
                    'title': 'Guía Paso a Paso',
                    'description': 'Problema de configuración. Proporciona pasos claros.',
                    'priority': 'medium',
                    'example': 'Te guío paso a paso: 1. Primero...'
                })
            
            # Sugerencias basadas en el mensaje actual
            if current_message:
                tone_analysis = self._analyze_agent_tone(current_message)
                
                if tone_analysis.get('formality_level') == 'too_formal':
                    suggestions.append({
                        'type': 'tone_adjustment',
                        'title': 'Ajustar Tono',
                        'description': 'Tu tono es muy formal. Sé más amigable.',
                        'priority': 'low',
                        'example': '¡Hola! Te ayudo con eso...'
                    })
                
                elif tone_analysis.get('empathy_level') == 'low':
                    suggestions.append({
                        'type': 'empathy_boost',
                        'title': 'Aumentar Empatía',
                        'description': 'Añade más empatía a tu respuesta.',
                        'priority': 'medium',
                        'example': 'Entiendo cómo te sientes...'
                    })
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error generating coaching suggestions: {e}")
            return []
    
    def _analyze_agent_tone(self, message: str) -> Dict[str, Any]:
        """Analiza el tono del agente"""
        try:
            if not message:
                return {}
            
            # Analizar formalidad
            formal_words = ['usted', 'le', 'su', 'estimado', 'atentamente']
            informal_words = ['tú', 'te', 'tu', 'hola', 'gracias', '¡', '!']
            
            formal_count = sum(1 for word in formal_words if word in message.lower())
            informal_count = sum(1 for word in informal_words if word in message.lower())
            
            if formal_count > informal_count:
                formality_level = 'formal'
            elif informal_count > formal_count:
                formality_level = 'informal'
            else:
                formality_level = 'neutral'
            
            # Analizar empatía
            empathy_words = ['entiendo', 'comprendo', 'sé cómo te sientes', 'lo siento', 'te ayudo']
            empathy_count = sum(1 for word in empathy_words if word in message.lower())
            
            if empathy_count >= 2:
                empathy_level = 'high'
            elif empathy_count >= 1:
                empathy_level = 'medium'
            else:
                empathy_level = 'low'
            
            # Analizar claridad
            sentence_count = len([s for s in message.split('.') if s.strip()])
            avg_sentence_length = len(message.split()) / sentence_count if sentence_count > 0 else 0
            
            if avg_sentence_length <= 15:
                clarity_level = 'high'
            elif avg_sentence_length <= 25:
                clarity_level = 'medium'
            else:
                clarity_level = 'low'
            
            return {
                'formality_level': formality_level,
                'empathy_level': empathy_level,
                'clarity_level': clarity_level,
                'sentence_count': sentence_count,
                'avg_sentence_length': avg_sentence_length
            }
            
        except Exception as e:
            logger.error(f"Error analyzing agent tone: {e}")
            return {}
    
    def _generate_real_time_feedback(self, context_analysis: Dict[str, Any], tone_analysis: Dict[str, Any], suggestions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Genera feedback en tiempo real"""
        try:
            feedback = {
                'positive_points': [],
                'improvement_areas': [],
                'immediate_actions': [],
                'overall_score': 0.0
            }
            
            # Evaluar puntos positivos
            if tone_analysis.get('clarity_level') == 'high':
                feedback['positive_points'].append('Excelente claridad en la comunicación')
            
            if tone_analysis.get('empathy_level') == 'high':
                feedback['positive_points'].append('Muy buena empatía con el cliente')
            
            # Identificar áreas de mejora
            if tone_analysis.get('empathy_level') == 'low':
                feedback['improvement_areas'].append('Aumentar la empatía en las respuestas')
            
            if tone_analysis.get('clarity_level') == 'low':
                feedback['improvement_areas'].append('Simplificar las explicaciones')
            
            # Acciones inmediatas
            high_priority_suggestions = [s for s in suggestions if s.get('priority') == 'high' or s.get('priority') == 'critical']
            
            for suggestion in high_priority_suggestions[:2]:  # Máximo 2 acciones inmediatas
                feedback['immediate_actions'].append({
                    'action': suggestion.get('title', ''),
                    'description': suggestion.get('description', ''),
                    'example': suggestion.get('example', '')
                })
            
            # Calcular score general
            score = 0.0
            
            # Puntos por claridad
            if tone_analysis.get('clarity_level') == 'high':
                score += 0.3
            elif tone_analysis.get('clarity_level') == 'medium':
                score += 0.2
            
            # Puntos por empatía
            if tone_analysis.get('empathy_level') == 'high':
                score += 0.4
            elif tone_analysis.get('empathy_level') == 'medium':
                score += 0.2
            
            # Puntos por progreso de conversación
            progress = context_analysis.get('conversation_progress', {}).get('progress', 0.0)
            score += progress * 0.3
            
            feedback['overall_score'] = min(1.0, score)
            
            return feedback
            
        except Exception as e:
            logger.error(f"Error generating real-time feedback: {e}")
            return {}
    
    def _check_priority_alerts(self, ticket, context_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Verifica alertas de prioridad"""
        try:
            alerts = []
            
            # Alerta por cliente frustrado
            customer_sentiment = context_analysis.get('customer_sentiment', {})
            if customer_sentiment.get('frustration_level', 0) > 0.7:
                alerts.append({
                    'type': 'high_frustration',
                    'title': 'Cliente Muy Frustrado',
                    'description': 'El cliente muestra alta frustración. Requiere atención inmediata.',
                    'severity': 'critical'
                })
            
            # Alerta por conversación larga
            conversation_length = context_analysis.get('conversation_length', 0)
            if conversation_length > 10:
                alerts.append({
                    'type': 'long_conversation',
                    'title': 'Conversación Prolongada',
                    'description': 'La conversación es muy larga. Considera escalar o resumir.',
                    'severity': 'medium'
                })
            
            # Alerta por falta de progreso
            conversation_progress = context_analysis.get('conversation_progress', {})
            if conversation_progress.get('progress', 0.0) < 0.3 and conversation_length > 5:
                alerts.append({
                    'type': 'no_progress',
                    'title': 'Sin Progreso',
                    'description': 'La conversación no muestra progreso. Revisa el enfoque.',
                    'severity': 'high'
                })
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking priority alerts: {e}")
            return []
    
    def save_coaching_session(self, agent_id: int, ticket_id: int, coaching_data: Dict[str, Any]):
        """
        Guarda una sesión de coaching
        """
        try:
            # Crear registro de coaching
            coaching = AgentCoaching.objects.create(
                agent_id=agent_id,
                conversation_id=str(ticket_id),
                feedback_type='real_time',
                feedback_message=coaching_data.get('context_summary', ''),
                suggested_improvement='\n'.join([
                    f"- {s.get('title', '')}: {s.get('description', '')}"
                    for s in coaching_data.get('coaching_suggestions', [])
                ]),
                confidence_score=coaching_data.get('real_time_feedback', {}).get('overall_score', 0.0)
            )
            
            logger.info(f"Saved coaching session: {coaching.id}")
            return coaching
            
        except Exception as e:
            logger.error(f"Error saving coaching session: {e}")
            return None
    
    def get_agent_performance_summary(self, agent_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Obtiene un resumen del rendimiento del agente
        """
        try:
            # Obtener sesiones de coaching recientes
            recent_coaching = AgentCoaching.objects.filter(
                agent_id=agent_id,
                session_date__gte=timezone.now() - timedelta(days=days)
            )
            
            if not recent_coaching:
                return {'error': 'No coaching sessions found'}
            
            # Calcular métricas
            total_sessions = recent_coaching.count()
            avg_confidence = recent_coaching.aggregate(Avg('confidence_score'))['confidence_score__avg'] or 0.0
            
            # Analizar tipos de feedback
            feedback_types = {}
            for coaching in recent_coaching:
                feedback_type = coaching.feedback_type
                if feedback_type not in feedback_types:
                    feedback_types[feedback_type] = 0
                feedback_types[feedback_type] += 1
            
            # Identificar áreas de mejora más comunes
            improvement_areas = self._analyze_improvement_areas(recent_coaching)
            
            # Calcular tendencia
            recent_sessions = recent_coaching.filter(
                session_date__gte=timezone.now() - timedelta(days=7)
            )
            recent_avg = recent_sessions.aggregate(Avg('confidence_score'))['confidence_score__avg'] or 0.0
            
            if recent_avg > avg_confidence + 0.1:
                trend = 'improving'
            elif recent_avg < avg_confidence - 0.1:
                trend = 'declining'
            else:
                trend = 'stable'
            
            return {
                'total_sessions': total_sessions,
                'avg_confidence': avg_confidence,
                'recent_avg_confidence': recent_avg,
                'trend': trend,
                'feedback_types': feedback_types,
                'improvement_areas': improvement_areas,
                'recommendations': self._generate_performance_recommendations(improvement_areas, avg_confidence)
            }
            
        except Exception as e:
            logger.error(f"Error getting agent performance summary: {e}")
            return {'error': str(e)}
    
    def _analyze_improvement_areas(self, coaching_sessions) -> List[Dict[str, Any]]:
        """Analiza áreas de mejora del agente"""
        try:
            improvement_areas = {}
            
            for coaching in coaching_sessions:
                # Analizar el texto de mejora sugerida
                improvements = coaching.suggested_improvement.split('\n')
                
                for improvement in improvements:
                    if improvement.strip():
                        # Categorizar la mejora
                        if 'empatía' in improvement.lower():
                            area = 'empathy'
                        elif 'claridad' in improvement.lower():
                            area = 'clarity'
                        elif 'técnico' in improvement.lower():
                            area = 'technical'
                        elif 'urgencia' in improvement.lower():
                            area = 'urgency'
                        else:
                            area = 'general'
                        
                        if area not in improvement_areas:
                            improvement_areas[area] = 0
                        improvement_areas[area] += 1
            
            # Convertir a lista ordenada
            areas_list = [
                {
                    'area': area,
                    'frequency': count,
                    'priority': 'high' if count > 3 else 'medium' if count > 1 else 'low'
                }
                for area, count in improvement_areas.items()
            ]
            
            return sorted(areas_list, key=lambda x: x['frequency'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error analyzing improvement areas: {e}")
            return []
    
    def _generate_performance_recommendations(self, improvement_areas: List[Dict[str, Any]], avg_confidence: float) -> List[Dict[str, Any]]:
        """Genera recomendaciones de rendimiento"""
        try:
            recommendations = []
            
            # Recomendaciones basadas en áreas de mejora
            for area in improvement_areas[:3]:  # Top 3 áreas
                if area['area'] == 'empathy':
                    recommendations.append({
                        'type': 'training',
                        'title': 'Entrenamiento en Empatía',
                        'description': 'Mejorar habilidades de empatía y comunicación emocional',
                        'priority': area['priority']
                    })
                
                elif area['area'] == 'clarity':
                    recommendations.append({
                        'type': 'communication',
                        'title': 'Mejorar Claridad',
                        'description': 'Practicar comunicación clara y concisa',
                        'priority': area['priority']
                    })
                
                elif area['area'] == 'technical':
                    recommendations.append({
                        'type': 'knowledge',
                        'title': 'Actualizar Conocimientos Técnicos',
                        'description': 'Refrescar conocimientos técnicos del sistema',
                        'priority': area['priority']
                    })
            
            # Recomendaciones basadas en confianza general
            if avg_confidence < 0.6:
                recommendations.append({
                    'type': 'confidence',
                    'title': 'Aumentar Confianza',
                    'description': 'Trabajar en aumentar la confianza en las respuestas',
                    'priority': 'high'
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating performance recommendations: {e}")
            return []

# Instancia global
coaching_agent = CoachingAgent() 