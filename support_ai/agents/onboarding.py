import logging
from typing import Dict, List, Optional, Any
from django.db.models import Q
from ..models import OnboardingFlow, CustomerProfile, SupportTicket, Conversation
from ..llm_integration import llm_client

logger = logging.getLogger(__name__)

class OnboardingAgent:
    """Agente para onboarding inteligente de clientes y agentes"""
    
    def __init__(self):
        self.llm_client = llm_client
    
    def get_onboarding_flow(self, user_type: str, experience_level: str = None) -> Optional[OnboardingFlow]:
        """
        Obtiene el flujo de onboarding apropiado para el usuario
        """
        try:
            # Buscar flujo específico
            flow = OnboardingFlow.objects.filter(
                user_type=user_type,
                is_active=True
            ).first()
            
            if not flow:
                # Crear flujo dinámico basado en el tipo de usuario
                flow = self._create_dynamic_flow(user_type, experience_level)
            
            return flow
            
        except Exception as e:
            logger.error(f"Error getting onboarding flow: {e}")
            return None
    
    def _create_dynamic_flow(self, user_type: str, experience_level: str) -> OnboardingFlow:
        """Crea un flujo de onboarding dinámico"""
        try:
            if user_type == 'new_customer':
                steps = [
                    {
                        'step': 1,
                        'title': 'Bienvenido a Synap',
                        'content': 'Te guiaremos a través de las funcionalidades principales',
                        'type': 'welcome',
                        'duration': 30
                    },
                    {
                        'step': 2,
                        'title': 'Configuración Inicial',
                        'content': 'Configura tu empresa y preferencias básicas',
                        'type': 'setup',
                        'duration': 120
                    },
                    {
                        'step': 3,
                        'title': 'Primeros Pasos',
                        'content': 'Aprende a crear tu primera factura',
                        'type': 'tutorial',
                        'duration': 180
                    },
                    {
                        'step': 4,
                        'title': 'Soporte Disponible',
                        'content': 'Conoce las diferentes formas de obtener ayuda',
                        'type': 'support',
                        'duration': 60
                    }
                ]
            elif user_type == 'advanced_customer':
                steps = [
                    {
                        'step': 1,
                        'title': 'Funcionalidades Avanzadas',
                        'content': 'Descubre características avanzadas de Synap',
                        'type': 'advanced',
                        'duration': 90
                    },
                    {
                        'step': 2,
                        'title': 'Integraciones',
                        'content': 'Configura integraciones con otros sistemas',
                        'type': 'integration',
                        'duration': 150
                    },
                    {
                        'step': 3,
                        'title': 'Automatizaciones',
                        'content': 'Configura flujos de trabajo automatizados',
                        'type': 'automation',
                        'duration': 200
                    }
                ]
            elif user_type == 'new_agent':
                steps = [
                    {
                        'step': 1,
                        'title': 'Bienvenido al Equipo',
                        'content': 'Conoce tu rol y responsabilidades',
                        'type': 'welcome',
                        'duration': 45
                    },
                    {
                        'step': 2,
                        'title': 'Herramientas de Soporte',
                        'content': 'Aprende a usar las herramientas de IA',
                        'type': 'tools',
                        'duration': 180
                    },
                    {
                        'step': 3,
                        'title': 'Procedimientos',
                        'content': 'Conoce los procedimientos estándar',
                        'type': 'procedures',
                        'duration': 120
                    },
                    {
                        'step': 4,
                        'title': 'Primer Ticket',
                        'content': 'Resuelve tu primer ticket con asistencia',
                        'type': 'practice',
                        'duration': 300
                    }
                ]
            else:  # experienced_agent
                steps = [
                    {
                        'step': 1,
                        'title': 'Nuevas Funcionalidades',
                        'content': 'Conoce las últimas actualizaciones',
                        'type': 'updates',
                        'duration': 60
                    },
                    {
                        'step': 2,
                        'title': 'Mejores Prácticas',
                        'content': 'Optimiza tu flujo de trabajo',
                        'type': 'best_practices',
                        'duration': 90
                    }
                ]
            
            # Crear el flujo
            flow = OnboardingFlow.objects.create(
                name=f"Onboarding {user_type.replace('_', ' ').title()}",
                description=f"Flujo de onboarding para {user_type}",
                user_type=user_type,
                steps=steps
            )
            
            return flow
            
        except Exception as e:
            logger.error(f"Error creating dynamic flow: {e}")
            return None
    
    def get_personalized_content(self, user_type: str, experience_level: str, step: int) -> Dict[str, Any]:
        """
        Genera contenido personalizado para cada paso del onboarding
        """
        try:
            # Obtener flujo
            flow = self.get_onboarding_flow(user_type, experience_level)
            if not flow or step > len(flow.steps):
                return {}
            
            current_step = flow.steps[step - 1]
            
            # Personalizar contenido basado en experiencia
            if experience_level == 'beginner':
                content_style = 'explicativo y detallado'
                examples = 'más ejemplos y capturas de pantalla'
            elif experience_level == 'intermediate':
                content_style = 'balanceado entre explicación y práctica'
                examples = 'ejemplos moderados'
            else:  # advanced/expert
                content_style = 'conciso y técnico'
                examples = 'ejemplos avanzados'
            
            # Generar contenido personalizado con LLM
            prompt = f"""
            Genera contenido personalizado para onboarding.
            
            Tipo de usuario: {user_type}
            Nivel de experiencia: {experience_level}
            Paso: {current_step['title']}
            Contenido base: {current_step['content']}
            Estilo: {content_style}
            Ejemplos: {examples}
            
            Genera:
            1. Título atractivo
            2. Explicación clara
            3. Pasos específicos
            4. Tips útiles
            5. Próximo paso sugerido
            """
            
            response = self.llm_client.generate_response([
                {"role": "system", "content": "Eres un experto en onboarding y capacitación."},
                {"role": "user", "content": prompt}
            ], temperature=0.7)
            
            return {
                'step': step,
                'title': current_step['title'],
                'content': response['content'],
                'type': current_step['type'],
                'duration': current_step['duration'],
                'total_steps': len(flow.steps),
                'progress': (step / len(flow.steps)) * 100
            }
            
        except Exception as e:
            logger.error(f"Error getting personalized content: {e}")
            return {}
    
    def track_onboarding_progress(self, user_id: int, step: int, completion_rate: float):
        """
        Rastrea el progreso del onboarding
        """
        try:
            # Actualizar perfil del usuario
            profile, created = CustomerProfile.objects.get_or_create(
                user_id=user_id,
                defaults={'experience_level': 'beginner'}
            )
            
            # Si completó el onboarding
            if completion_rate >= 100:
                profile.onboarding_completed = True
                profile.save()
                
                logger.info(f"User {user_id} completed onboarding")
            
        except Exception as e:
            logger.error(f"Error tracking onboarding progress: {e}")
    
    def provide_agent_assistance(self, agent_id: int, ticket_id: int) -> Dict[str, Any]:
        """
        Proporciona asistencia a agentes nuevos durante tickets
        """
        try:
            # Obtener información del ticket
            ticket = SupportTicket.objects.get(id=ticket_id)
            
            # Analizar el ticket
            intent = self.llm_client.classify_intent(f"{ticket.subject} {ticket.description}")
            sentiment = self.llm_client.analyze_sentiment(ticket.description)
            
            # Generar sugerencias
            suggestions = self._generate_agent_suggestions(ticket, intent, sentiment)
            
            # Crear resumen del contexto
            context_summary = self._create_context_summary(ticket)
            
            return {
                'suggestions': suggestions,
                'context_summary': context_summary,
                'intent': intent,
                'sentiment': sentiment,
                'priority': self._calculate_priority(sentiment, intent),
                'recommended_actions': self._get_recommended_actions(intent, sentiment)
            }
            
        except Exception as e:
            logger.error(f"Error providing agent assistance: {e}")
            return {}
    
    def _generate_agent_suggestions(self, ticket: SupportTicket, intent: Dict, sentiment: Dict) -> List[str]:
        """Genera sugerencias para el agente"""
        try:
            suggestions = []
            
            # Sugerencias basadas en la intención
            if intent.get('intent') == 'facturacion':
                suggestions.append("Verificar datos fiscales del cliente")
                suggestions.append("Revisar configuración de impuestos")
            elif intent.get('intent') == 'configuracion':
                suggestions.append("Guía paso a paso de configuración")
                suggestions.append("Verificar permisos del usuario")
            
            # Sugerencias basadas en el sentimiento
            if sentiment.get('negative', 0) > 0.6:
                suggestions.append("Mostrar empatía y comprensión")
                suggestions.append("Ofrecer solución rápida")
            
            # Sugerencias generales
            suggestions.append("Usar lenguaje claro y profesional")
            suggestions.append("Confirmar la resolución con el cliente")
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")
            return []
    
    def _create_context_summary(self, ticket: SupportTicket) -> str:
        """Crea un resumen del contexto del ticket"""
        try:
            # Obtener conversaciones previas
            conversations = Conversation.objects.filter(ticket=ticket).order_by('created_at')
            
            if conversations.count() <= 1:
                return "Nuevo ticket sin conversación previa"
            
            # Crear resumen con LLM
            conversation_text = "\n".join([
                f"{conv.message_type}: {conv.content}" 
                for conv in conversations[:5]  # Últimas 5 conversaciones
            ])
            
            prompt = f"""
            Crea un resumen conciso del contexto de este ticket:
            
            Asunto: {ticket.subject}
            Descripción: {ticket.description}
            Conversaciones:
            {conversation_text}
            
            Responde con un resumen de 2-3 oraciones.
            """
            
            response = self.llm_client.generate_response([
                {"role": "system", "content": "Eres un experto en resumir contextos de soporte."},
                {"role": "user", "content": prompt}
            ], temperature=0.3)
            
            return response['content']
            
        except Exception as e:
            logger.error(f"Error creating context summary: {e}")
            return "Error al generar resumen"
    
    def _calculate_priority(self, sentiment: Dict, intent: Dict) -> str:
        """Calcula la prioridad del ticket"""
        negative_score = sentiment.get('negative', 0)
        
        if negative_score > 0.8:
            return 'high'
        elif negative_score > 0.5:
            return 'medium'
        else:
            return 'low'
    
    def _get_recommended_actions(self, intent: Dict, sentiment: Dict) -> List[str]:
        """Obtiene acciones recomendadas"""
        actions = []
        
        # Acciones basadas en la intención
        intent_type = intent.get('intent', 'general')
        if intent_type == 'facturacion':
            actions.extend(['Verificar datos', 'Revisar configuración', 'Generar factura'])
        elif intent_type == 'configuracion':
            actions.extend(['Mostrar guía', 'Configurar parámetros', 'Verificar permisos'])
        
        # Acciones basadas en sentimiento
        if sentiment.get('negative', 0) > 0.6:
            actions.append('Escalar a supervisor')
        
        return actions

# Instancia global
onboarding_agent = OnboardingAgent() 