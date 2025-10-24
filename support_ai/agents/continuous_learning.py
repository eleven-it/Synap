import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from django.db.models import Q, Count, Avg
from django.utils import timezone
from ..models import (
    ContinuousLearning, SupportTicket, Conversation, 
    KnowledgeBase, BusinessInsight, AIAgent
)
from ..llm_integration import llm_client

logger = logging.getLogger(__name__)

class ContinuousLearningAgent:
    """Agente para aprendizaje continuo y mejora autónoma"""
    
    def __init__(self):
        self.llm_client = llm_client
    
    def analyze_conversation_learning(self, conversation_id: str) -> Dict[str, Any]:
        """
        Analiza una conversación para extraer aprendizajes
        """
        try:
            # Obtener conversación
            conversation = Conversation.objects.filter(
                ai_agent_used__isnull=False
            ).first()  # Simular conversación específica
            
            if not conversation:
                return {'error': 'No conversation found'}
            
            # Analizar la conversación
            analysis = {
                'conversation_id': conversation_id,
                'agent_used': conversation.ai_agent_used,
                'confidence_before': conversation.ai_confidence,
                'user_satisfaction': self._analyze_user_satisfaction(conversation),
                'response_quality': self._analyze_response_quality(conversation),
                'improvement_opportunities': [],
                'learning_points': []
            }
            
            # Identificar oportunidades de mejora
            if conversation.ai_confidence < 0.7:
                analysis['improvement_opportunities'].append({
                    'type': 'low_confidence',
                    'description': 'Respuesta con baja confianza',
                    'suggestion': 'Mejorar prompt o entrenamiento del agente'
                })
            
            # Extraer puntos de aprendizaje
            learning_points = self._extract_learning_points(conversation)
            analysis['learning_points'] = learning_points
            
            # Guardar datos de aprendizaje
            self._save_learning_data(conversation_id, analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing conversation learning: {e}")
            return {'error': str(e)}
    
    def _analyze_user_satisfaction(self, conversation) -> float:
        """Analiza la satisfacción del usuario"""
        try:
            # Analizar sentimiento de la respuesta del usuario
            if conversation.message_type == 'user':
                sentiment = self.llm_client.analyze_sentiment(conversation.content)
                return sentiment.get('positive', 0.5)
            
            return 0.5  # Valor por defecto
            
        except Exception as e:
            logger.error(f"Error analyzing user satisfaction: {e}")
            return 0.5
    
    def _analyze_response_quality(self, conversation) -> Dict[str, Any]:
        """Analiza la calidad de la respuesta de la IA"""
        try:
            quality_metrics = {
                'relevance': 0.0,
                'completeness': 0.0,
                'clarity': 0.0,
                'helpfulness': 0.0
            }
            
            # Analizar relevancia
            if conversation.content:
                relevance_prompt = f"""
                Evalúa la relevancia de esta respuesta de IA:
                Respuesta: {conversation.content}
                
                Responde con un número entre 0.0 y 1.0.
                """
                
                response = self.llm_client.generate_response([
                    {"role": "system", "content": "Eres un evaluador de calidad de respuestas de IA."},
                    {"role": "user", "content": relevance_prompt}
                ], temperature=0.1)
                
                try:
                    quality_metrics['relevance'] = float(response['content'].strip())
                except:
                    quality_metrics['relevance'] = 0.5
            
            # Analizar completitud
            word_count = len(conversation.content.split()) if conversation.content else 0
            quality_metrics['completeness'] = min(1.0, word_count / 50)  # Normalizar por longitud
            
            # Analizar claridad
            clarity_prompt = f"""
            Evalúa la claridad de esta respuesta:
            {conversation.content}
            
            Responde con un número entre 0.0 y 1.0.
            """
            
            response = self.llm_client.generate_response([
                {"role": "system", "content": "Eres un evaluador de claridad."},
                {"role": "user", "content": clarity_prompt}
            ], temperature=0.1)
            
            try:
                quality_metrics['clarity'] = float(response['content'].strip())
            except:
                quality_metrics['clarity'] = 0.5
            
            # Calcular helpfulness general
            quality_metrics['helpfulness'] = (
                quality_metrics['relevance'] * 0.4 +
                quality_metrics['completeness'] * 0.3 +
                quality_metrics['clarity'] * 0.3
            )
            
            return quality_metrics
            
        except Exception as e:
            logger.error(f"Error analyzing response quality: {e}")
            return {'relevance': 0.5, 'completeness': 0.5, 'clarity': 0.5, 'helpfulness': 0.5}
    
    def _extract_learning_points(self, conversation) -> List[Dict[str, Any]]:
        """Extrae puntos de aprendizaje de la conversación"""
        try:
            learning_points = []
            
            # Analizar si la respuesta fue efectiva
            if conversation.ai_confidence < 0.6:
                learning_points.append({
                    'type': 'confidence_improvement',
                    'description': 'Respuesta con baja confianza',
                    'action': 'Revisar prompt del agente',
                    'priority': 'high'
                })
            
            # Analizar patrones en la conversación
            if conversation.content:
                # Buscar palabras clave que indiquen problemas
                problem_keywords = ['no entiendo', 'no funciona', 'error', 'problema', 'ayuda']
                content_lower = conversation.content.lower()
                
                for keyword in problem_keywords:
                    if keyword in content_lower:
                        learning_points.append({
                            'type': 'user_confusion',
                            'description': f'Usuario confundido con "{keyword}"',
                            'action': 'Mejorar claridad de respuestas',
                            'priority': 'medium'
                        })
                        break
            
            return learning_points
            
        except Exception as e:
            logger.error(f"Error extracting learning points: {e}")
            return []
    
    def _save_learning_data(self, conversation_id: str, analysis: Dict[str, Any]):
        """Guarda datos de aprendizaje"""
        try:
            learning_data = {
                'conversation_analysis': analysis,
                'timestamp': timezone.now().isoformat(),
                'agent_performance': {
                    'confidence': analysis.get('confidence_before', 0.0),
                    'satisfaction': analysis.get('user_satisfaction', 0.5),
                    'quality': analysis.get('response_quality', {})
                }
            }
            
            ContinuousLearning.objects.create(
                source_type='conversation',
                source_id=conversation_id,
                learning_data=learning_data,
                agent_used=analysis.get('agent_used', 'unknown'),
                confidence_before=analysis.get('confidence_before', 0.0),
                confidence_after=analysis.get('confidence_before', 0.0),  # Sin mejora inmediata
                improvement_score=0.0,
                is_processed=True
            )
            
        except Exception as e:
            logger.error(f"Error saving learning data: {e}")
    
    def identify_knowledge_gaps(self) -> List[Dict[str, Any]]:
        """
        Identifica brechas en la base de conocimientos
        """
        try:
            gaps = []
            
            # Analizar tickets sin resolución por IA
            unresolved_tickets = SupportTicket.objects.filter(
                ai_resolved=False,
                status__in=['open', 'in_progress']
            ).order_by('-created_at')[:50]
            
            # Agrupar por tema
            topic_groups = {}
            for ticket in unresolved_tickets:
                intent = self.llm_client.classify_intent(f"{ticket.subject} {ticket.description}")
                topic = intent.get('intent', 'general')
                
                if topic not in topic_groups:
                    topic_groups[topic] = []
                topic_groups[topic].append(ticket)
            
            # Identificar brechas
            for topic, tickets in topic_groups.items():
                if len(tickets) >= 3:  # Mínimo 3 tickets para considerar brecha
                    # Verificar si existe documentación
                    existing_articles = KnowledgeBase.objects.filter(
                        category=topic,
                        is_active=True
                    ).count()
                    
                    if existing_articles == 0:
                        gaps.append({
                            'topic': topic,
                            'ticket_count': len(tickets),
                            'priority': 'high' if len(tickets) > 5 else 'medium',
                            'sample_tickets': [t.subject for t in tickets[:3]],
                            'suggested_article_title': f"Guía de {topic.replace('_', ' ').title()}",
                            'estimated_impact': 'high'
                        })
            
            return gaps
            
        except Exception as e:
            logger.error(f"Error identifying knowledge gaps: {e}")
            return []
    
    def auto_generate_knowledge_articles(self) -> List[Dict[str, Any]]:
        """
        Genera automáticamente artículos de conocimiento
        """
        try:
            generated_articles = []
            
            # Identificar brechas
            gaps = self.identify_knowledge_gaps()
            
            for gap in gaps[:3]:  # Generar máximo 3 artículos por vez
                try:
                    # Generar contenido del artículo
                    topic = gap['topic']
                    sample_tickets = gap['sample_tickets']
                    
                    prompt = f"""
                    Genera un artículo de conocimiento sobre: {topic}
                    
                    Basado en estos tickets de ejemplo:
                    {sample_tickets}
                    
                    Genera un artículo completo con:
                    1. Introducción clara
                    2. Pasos detallados
                    3. Soluciones comunes
                    4. Tips útiles
                    5. Conclusión
                    """
                    
                    response = self.llm_client.generate_response([
                        {"role": "system", "content": "Eres un experto en crear artículos de conocimiento técnico."},
                        {"role": "user", "content": prompt}
                    ], temperature=0.7)
                    
                    # Crear el artículo
                    article = KnowledgeBase.objects.create(
                        title=gap['suggested_article_title'],
                        content=response['content'],
                        category=topic,
                        ai_generated=True,
                        tags=self._extract_tags_from_content(response['content'])
                    )
                    
                    generated_articles.append({
                        'article_id': article.id,
                        'title': article.title,
                        'topic': topic,
                        'estimated_impact': gap['estimated_impact'],
                        'tickets_covered': gap['ticket_count']
                    })
                    
                    logger.info(f"Auto-generated knowledge article: {article.id}")
                    
                except Exception as e:
                    logger.error(f"Error generating article for {gap['topic']}: {e}")
                    continue
            
            return generated_articles
            
        except Exception as e:
            logger.error(f"Error auto-generating knowledge articles: {e}")
            return []
    
    def _extract_tags_from_content(self, content: str) -> List[str]:
        """Extrae tags del contenido del artículo"""
        try:
            prompt = f"""
            Extrae 5-10 tags relevantes del siguiente contenido:
            {content[:500]}
            
            Responde solo con una lista separada por comas.
            """
            
            response = self.llm_client.generate_response([
                {"role": "system", "content": "Eres un experto en extraer tags relevantes."},
                {"role": "user", "content": prompt}
            ], temperature=0.1)
            
            tags = [tag.strip() for tag in response['content'].split(',')]
            return tags[:10]
            
        except Exception as e:
            logger.error(f"Error extracting tags: {e}")
            return []
    
    def analyze_agent_performance(self, agent_type: str = None) -> Dict[str, Any]:
        """
        Analiza el rendimiento de los agentes IA
        """
        try:
            # Obtener conversaciones recientes
            recent_conversations = Conversation.objects.filter(
                ai_agent_used__isnull=False,
                created_at__gte=timezone.now() - timedelta(days=7)
            )
            
            if agent_type:
                recent_conversations = recent_conversations.filter(ai_agent_used=agent_type)
            
            # Calcular métricas
            total_conversations = recent_conversations.count()
            avg_confidence = recent_conversations.aggregate(Avg('ai_confidence'))['ai_confidence__avg'] or 0.0
            
            # Analizar satisfacción del usuario
            satisfaction_scores = []
            for conv in recent_conversations:
                if conv.message_type == 'user':
                    sentiment = self.llm_client.analyze_sentiment(conv.content)
                    satisfaction = sentiment.get('positive', 0.5)
                    satisfaction_scores.append(satisfaction)
            
            avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0.5
            
            # Identificar áreas de mejora
            improvement_areas = []
            
            if avg_confidence < 0.7:
                improvement_areas.append({
                    'area': 'confidence',
                    'current_score': avg_confidence,
                    'target_score': 0.8,
                    'suggestion': 'Mejorar prompts y entrenamiento'
                })
            
            if avg_satisfaction < 0.6:
                improvement_areas.append({
                    'area': 'user_satisfaction',
                    'current_score': avg_satisfaction,
                    'target_score': 0.7,
                    'suggestion': 'Revisar calidad de respuestas'
                })
            
            return {
                'agent_type': agent_type or 'all',
                'total_conversations': total_conversations,
                'avg_confidence': avg_confidence,
                'avg_satisfaction': avg_satisfaction,
                'improvement_areas': improvement_areas,
                'performance_trend': self._calculate_performance_trend(agent_type)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing agent performance: {e}")
            return {}
    
    def _calculate_performance_trend(self, agent_type: str = None) -> str:
        """Calcula la tendencia de rendimiento"""
        try:
            # Comparar rendimiento de esta semana vs semana anterior
            this_week = Conversation.objects.filter(
                ai_agent_used__isnull=False,
                created_at__gte=timezone.now() - timedelta(days=7)
            )
            
            last_week = Conversation.objects.filter(
                ai_agent_used__isnull=False,
                created_at__gte=timezone.now() - timedelta(days=14),
                created_at__lt=timezone.now() - timedelta(days=7)
            )
            
            if agent_type:
                this_week = this_week.filter(ai_agent_used=agent_type)
                last_week = last_week.filter(ai_agent_used=agent_type)
            
            this_week_avg = this_week.aggregate(Avg('ai_confidence'))['ai_confidence__avg'] or 0.0
            last_week_avg = last_week.aggregate(Avg('ai_confidence'))['ai_confidence__avg'] or 0.0
            
            if this_week_avg > last_week_avg + 0.05:
                return 'improving'
            elif this_week_avg < last_week_avg - 0.05:
                return 'declining'
            else:
                return 'stable'
                
        except Exception as e:
            logger.error(f"Error calculating performance trend: {e}")
            return 'stable'
    
    def generate_business_insights(self) -> List[Dict[str, Any]]:
        """
        Genera insights de negocio basados en datos de soporte
        """
        try:
            insights = []
            
            # Analizar patrones de frustración
            frustration_insight = self._analyze_frustration_patterns()
            if frustration_insight:
                insights.append(frustration_insight)
            
            # Analizar solicitudes de funcionalidades
            feature_insight = self._analyze_feature_requests()
            if feature_insight:
                insights.append(feature_insight)
            
            # Analizar tendencias de uso
            usage_insight = self._analyze_usage_trends()
            if usage_insight:
                insights.append(usage_insight)
            
            # Guardar insights
            for insight in insights:
                BusinessInsight.objects.create(
                    insight_type=insight['type'],
                    title=insight['title'],
                    description=insight['description'],
                    data_evidence=insight['evidence'],
                    impact_score=insight['impact_score'],
                    priority=insight['priority']
                )
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating business insights: {e}")
            return []
    
    def _analyze_frustration_patterns(self) -> Optional[Dict[str, Any]]:
        """Analiza patrones de frustración"""
        try:
            # Obtener tickets con sentimiento negativo
            recent_tickets = SupportTicket.objects.filter(
                created_at__gte=timezone.now() - timedelta(days=30)
            )[:100]  # Analizar últimos 100 tickets
            
            frustration_topics = {}
            
            for ticket in recent_tickets:
                sentiment = self.llm_client.analyze_sentiment(ticket.description)
                
                if sentiment.get('negative', 0) > 0.6:
                    intent = self.llm_client.classify_intent(f"{ticket.subject} {ticket.description}")
                    topic = intent.get('intent', 'general')
                    
                    if topic not in frustration_topics:
                        frustration_topics[topic] = 0
                    frustration_topics[topic] += 1
            
            if frustration_topics:
                most_frustrating = max(frustration_topics.items(), key=lambda x: x[1])
                
                return {
                    'type': 'frustration_pattern',
                    'title': f'Patrón de Frustración: {most_frustrating[0]}',
                    'description': f'Los usuarios muestran alta frustración con {most_frustrating[0]}',
                    'evidence': {
                        'topic': most_frustrating[0],
                        'frustration_count': most_frustrating[1],
                        'total_tickets': len(recent_tickets)
                    },
                    'impact_score': 0.8,
                    'priority': 'high'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error analyzing frustration patterns: {e}")
            return None
    
    def _analyze_feature_requests(self) -> Optional[Dict[str, Any]]:
        """Analiza solicitudes de funcionalidades"""
        try:
            # Buscar tickets que sugieren nuevas funcionalidades
            feature_keywords = ['necesito', 'quisiera', 'sería útil', 'falta', 'agregar', 'nueva funcionalidad']
            
            recent_tickets = SupportTicket.objects.filter(
                created_at__gte=timezone.now() - timedelta(days=30)
            )
            
            feature_requests = []
            
            for ticket in recent_tickets:
                content_lower = f"{ticket.subject} {ticket.description}".lower()
                
                for keyword in feature_keywords:
                    if keyword in content_lower:
                        feature_requests.append({
                            'ticket_id': ticket.id,
                            'content': ticket.description,
                            'date': ticket.created_at
                        })
                        break
            
            if feature_requests:
                # Analizar patrones en las solicitudes
                common_themes = self._identify_common_themes([req['content'] for req in feature_requests])
                
                return {
                    'type': 'feature_request',
                    'title': 'Solicitudes de Nuevas Funcionalidades',
                    'description': f'Se identificaron {len(feature_requests)} solicitudes de funcionalidades',
                    'evidence': {
                        'request_count': len(feature_requests),
                        'common_themes': common_themes,
                        'sample_requests': feature_requests[:3]
                    },
                    'impact_score': 0.7,
                    'priority': 'medium'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error analyzing feature requests: {e}")
            return None
    
    def _analyze_usage_trends(self) -> Optional[Dict[str, Any]]:
        """Analiza tendencias de uso"""
        try:
            # Analizar tendencias de tickets por categoría
            recent_tickets = SupportTicket.objects.filter(
                created_at__gte=timezone.now() - timedelta(days=30)
            )
            
            category_counts = {}
            
            for ticket in recent_tickets:
                intent = self.llm_client.classify_intent(f"{ticket.subject} {ticket.description}")
                category = intent.get('intent', 'general')
                
                if category not in category_counts:
                    category_counts[category] = 0
                category_counts[category] += 1
            
            if category_counts:
                most_common = max(category_counts.items(), key=lambda x: x[1])
                least_common = min(category_counts.items(), key=lambda x: x[1])
                
                return {
                    'type': 'usage_trend',
                    'title': 'Tendencias de Uso del Sistema',
                    'description': f'Categoría más consultada: {most_common[0]} ({most_common[1]} tickets)',
                    'evidence': {
                        'most_common_category': most_common[0],
                        'most_common_count': most_common[1],
                        'least_common_category': least_common[0],
                        'least_common_count': least_common[1],
                        'total_tickets': len(recent_tickets)
                    },
                    'impact_score': 0.6,
                    'priority': 'medium'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error analyzing usage trends: {e}")
            return None
    
    def _identify_common_themes(self, texts: List[str]) -> List[str]:
        """Identifica temas comunes en una lista de textos"""
        try:
            # Usar LLM para identificar temas comunes
            combined_text = "\n".join(texts[:10])  # Usar máximo 10 textos
            
            prompt = f"""
            Identifica los 3 temas más comunes en estos textos:
            
            {combined_text}
            
            Responde solo con una lista separada por comas.
            """
            
            response = self.llm_client.generate_response([
                {"role": "system", "content": "Eres un experto en identificar temas comunes."},
                {"role": "user", "content": prompt}
            ], temperature=0.3)
            
            themes = [theme.strip() for theme in response['content'].split(',')]
            return themes[:3]
            
        except Exception as e:
            logger.error(f"Error identifying common themes: {e}")
            return []

# Instancia global
continuous_learning_agent = ContinuousLearningAgent() 