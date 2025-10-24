import logging
from typing import Dict, List, Optional, Any
from django.db.models import Q
from ..models import KnowledgeBase, SupportTicket, Conversation
from ..llm_integration import llm_client

logger = logging.getLogger(__name__)

class KnowledgeBaseAgent:
    """Agente para gestión de base de conocimientos dinámica"""
    
    def __init__(self):
        self.llm_client = llm_client
    
    def search_knowledge(self, query: str, category: str = None) -> List[Dict[str, Any]]:
        """
        Busca en la base de conocimientos usando IA
        """
        try:
            # Búsqueda semántica con LLM
            search_results = []
            
            # Buscar por texto directo
            base_query = KnowledgeBase.objects.filter(is_active=True)
            
            if category:
                base_query = base_query.filter(category=category)
            
            # Búsqueda por título y contenido
            text_results = base_query.filter(
                Q(title__icontains=query) | 
                Q(content__icontains=query) |
                Q(tags__contains=[query])
            ).order_by('-usage_count', '-last_updated')
            
            for kb in text_results[:5]:
                search_results.append({
                    'id': kb.id,
                    'title': kb.title,
                    'content': kb.content[:200] + "..." if len(kb.content) > 200 else kb.content,
                    'category': kb.category,
                    'relevance_score': self._calculate_relevance(query, kb),
                    'usage_count': kb.usage_count
                })
            
            # Búsqueda semántica con LLM
            semantic_results = self._semantic_search(query, category)
            search_results.extend(semantic_results)
            
            # Ordenar por relevancia
            search_results.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            return search_results[:10]
            
        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return []
    
    def _semantic_search(self, query: str, category: str = None) -> List[Dict[str, Any]]:
        """Búsqueda semántica usando LLM"""
        try:
            # Usar LLM para entender la intención de la consulta
            intent_analysis = self.llm_client.classify_intent(query)
            
            # Buscar artículos relacionados
            base_query = KnowledgeBase.objects.filter(is_active=True)
            
            if category:
                base_query = base_query.filter(category=category)
            
            # Filtrar por categoría basada en la intención
            intent_category = intent_analysis.get('intent', 'general')
            if intent_category != 'general':
                base_query = base_query.filter(category=intent_category)
            
            results = []
            for kb in base_query.order_by('-usage_count')[:5]:
                relevance = self._calculate_semantic_relevance(query, kb.content)
                if relevance > 0.3:  # Umbral mínimo de relevancia
                    results.append({
                        'id': kb.id,
                        'title': kb.title,
                        'content': kb.content[:200] + "..." if len(kb.content) > 200 else kb.content,
                        'category': kb.category,
                        'relevance_score': relevance,
                        'usage_count': kb.usage_count
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []
    
    def _calculate_relevance(self, query: str, kb: KnowledgeBase) -> float:
        """Calcula relevancia basada en coincidencias de texto"""
        query_lower = query.lower()
        title_score = 2.0 if query_lower in kb.title.lower() else 0.0
        content_score = 1.0 if query_lower in kb.content.lower() else 0.0
        tag_score = 0.5 if any(tag.lower() in query_lower for tag in kb.tags) else 0.0
        
        return title_score + content_score + tag_score + (kb.usage_count * 0.01)
    
    def _calculate_semantic_relevance(self, query: str, content: str) -> float:
        """Calcula relevancia semántica usando LLM"""
        try:
            # Usar LLM para evaluar similitud semántica
            prompt = f"""
            Evalúa la relevancia entre la consulta y el contenido.
            Consulta: {query}
            Contenido: {content[:500]}
            
            Responde solo con un número entre 0.0 y 1.0, donde:
            0.0 = No relevante
            1.0 = Muy relevante
            """
            
            response = self.llm_client.generate_response([
                {"role": "system", "content": "Eres un evaluador de relevancia semántica."},
                {"role": "user", "content": prompt}
            ], temperature=0.1)
            
            try:
                return float(response['content'].strip())
            except:
                return 0.5
                
        except Exception as e:
            logger.error(f"Error calculating semantic relevance: {e}")
            return 0.5
    
    def suggest_knowledge_article(self, ticket: SupportTicket) -> Optional[Dict[str, Any]]:
        """
        Sugiere artículos de conocimiento basado en un ticket
        """
        try:
            # Analizar el ticket para sugerir artículos
            ticket_content = f"{ticket.subject} {ticket.description}"
            
            # Buscar artículos relevantes
            suggestions = self.search_knowledge(ticket_content)
            
            if suggestions:
                best_match = suggestions[0]
                
                # Incrementar contador de uso
                kb = KnowledgeBase.objects.get(id=best_match['id'])
                kb.usage_count += 1
                kb.save()
                
                return best_match
            
            return None
            
        except Exception as e:
            logger.error(f"Error suggesting knowledge article: {e}")
            return None
    
    def auto_generate_article(self, topic: str, content: str, category: str) -> Optional[KnowledgeBase]:
        """
        Genera automáticamente un artículo de conocimiento
        """
        try:
            # Usar LLM para generar contenido estructurado
            prompt = f"""
            Genera un artículo de conocimiento sobre: {topic}
            
            Contenido base: {content}
            Categoría: {category}
            
            Genera un título claro y contenido estructurado con:
            - Introducción
            - Pasos o explicación
            - Conclusión
            - Tags relevantes
            """
            
            response = self.llm_client.generate_response([
                {"role": "system", "content": "Eres un experto en crear artículos de conocimiento técnico."},
                {"role": "user", "content": prompt}
            ], temperature=0.7)
            
            # Extraer título y contenido
            generated_content = response['content']
            
            # Crear el artículo
            article = KnowledgeBase.objects.create(
                title=topic,
                content=generated_content,
                category=category,
                ai_generated=True,
                tags=self._extract_tags(generated_content)
            )
            
            logger.info(f"Auto-generated knowledge article: {article.id}")
            return article
            
        except Exception as e:
            logger.error(f"Error auto-generating article: {e}")
            return None
    
    def _extract_tags(self, content: str) -> List[str]:
        """Extrae tags relevantes del contenido"""
        try:
            prompt = f"""
            Extrae 5-10 tags relevantes del siguiente contenido.
            Responde solo con una lista separada por comas.
            
            Contenido: {content[:500]}
            """
            
            response = self.llm_client.generate_response([
                {"role": "system", "content": "Eres un experto en extraer tags relevantes."},
                {"role": "user", "content": prompt}
            ], temperature=0.1)
            
            tags = [tag.strip() for tag in response['content'].split(',')]
            return tags[:10]  # Máximo 10 tags
            
        except Exception as e:
            logger.error(f"Error extracting tags: {e}")
            return []
    
    def identify_knowledge_gaps(self, tickets: List[SupportTicket]) -> List[Dict[str, Any]]:
        """
        Identifica brechas en la base de conocimientos
        """
        try:
            gaps = []
            
            # Agrupar tickets por tema
            topics = {}
            for ticket in tickets:
                intent = self.llm_client.classify_intent(f"{ticket.subject} {ticket.description}")
                topic = intent.get('intent', 'general')
                
                if topic not in topics:
                    topics[topic] = []
                topics[topic].append(ticket)
            
            # Analizar cada tema
            for topic, topic_tickets in topics.items():
                if len(topic_tickets) >= 3:  # Mínimo 3 tickets para considerar brecha
                    # Verificar si existe artículo sobre este tema
                    existing_articles = KnowledgeBase.objects.filter(
                        category=topic,
                        is_active=True
                    ).count()
                    
                    if existing_articles == 0:
                        # Crear sugerencia de artículo
                        sample_ticket = topic_tickets[0]
                        gaps.append({
                            'topic': topic,
                            'ticket_count': len(topic_tickets),
                            'sample_ticket': sample_ticket.subject,
                            'priority': 'high' if len(topic_tickets) > 5 else 'medium',
                            'suggested_title': f"Guía de {topic.replace('_', ' ').title()}",
                            'suggested_content': sample_ticket.description
                        })
            
            return gaps
            
        except Exception as e:
            logger.error(f"Error identifying knowledge gaps: {e}")
            return []
    
    def update_article_relevance(self, article_id: int, feedback: str):
        """
        Actualiza la relevancia de un artículo basado en feedback
        """
        try:
            article = KnowledgeBase.objects.get(id=article_id)
            
            # Analizar feedback con LLM
            sentiment = self.llm_client.analyze_sentiment(feedback)
            
            # Si el feedback es negativo, marcar para revisión
            if sentiment.get('negative', 0) > 0.6:
                article.is_active = False
                article.save()
                
                logger.info(f"Article {article_id} deactivated due to negative feedback")
            
        except Exception as e:
            logger.error(f"Error updating article relevance: {e}")

# Instancia global
knowledge_base_agent = KnowledgeBaseAgent() 