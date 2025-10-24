import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from django.db.models import Q, Count, Avg
from django.utils import timezone
from ..models import (
    ProactiveAlert, SupportTicket, CustomerProfile, 
    SupportMetrics, KnowledgeBase, Conversation
)
from ..llm_integration import llm_client

logger = logging.getLogger(__name__)

class ProactiveAgent:
    """Agente para soporte proactivo y resolución predictiva"""
    
    def __init__(self):
        self.llm_client = llm_client
    
    def analyze_user_patterns(self, user_id: int) -> Dict[str, Any]:
        """
        Analiza patrones de uso del usuario para detectar problemas potenciales
        """
        try:
            # Obtener tickets recientes del usuario
            recent_tickets = SupportTicket.objects.filter(
                customer_id=user_id,
                created_at__gte=timezone.now() - timedelta(days=30)
            ).order_by('-created_at')
            
            # Analizar patrones
            patterns = {
                'ticket_frequency': recent_tickets.count(),
                'common_issues': self._identify_common_issues(recent_tickets),
                'usage_trends': self._analyze_usage_trends(user_id),
                'error_patterns': self._detect_error_patterns(recent_tickets),
                'satisfaction_trend': self._analyze_satisfaction_trend(recent_tickets)
            }
            
            # Detectar problemas potenciales
            potential_issues = self._detect_potential_issues(patterns)
            
            return {
                'patterns': patterns,
                'potential_issues': potential_issues,
                'recommendations': self._generate_recommendations(patterns, potential_issues)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing user patterns: {e}")
            return {}
    
    def _identify_common_issues(self, tickets) -> List[Dict[str, Any]]:
        """Identifica problemas comunes en los tickets"""
        try:
            # Agrupar por tipo de problema
            issue_groups = {}
            
            for ticket in tickets:
                intent = self.llm_client.classify_intent(f"{ticket.subject} {ticket.description}")
                issue_type = intent.get('intent', 'general')
                
                if issue_type not in issue_groups:
                    issue_groups[issue_type] = {
                        'count': 0,
                        'tickets': [],
                        'avg_resolution_time': 0
                    }
                
                issue_groups[issue_type]['count'] += 1
                issue_groups[issue_type]['tickets'].append(ticket)
            
            # Calcular métricas
            common_issues = []
            for issue_type, data in issue_groups.items():
                if data['count'] >= 2:  # Mínimo 2 tickets para considerar común
                    # Crear sugerencia de artículo
                    common_issues.append({
                        'issue_type': issue_type,
                        'frequency': data['count'],
                        'avg_resolution_time': 0,
                        'last_occurrence': data['tickets'][0].created_at
                    })
            
            return sorted(common_issues, key=lambda x: x['frequency'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error identifying common issues: {e}")
            return []
    
    def _analyze_usage_trends(self, user_id: int) -> Dict[str, Any]:
        """Analiza tendencias de uso del usuario"""
        try:
            # Simular análisis de uso
            usage_data = {
                'login_frequency': 'daily',
                'feature_usage': {
                    'facturacion': 0.8,
                    'inventario': 0.6,
                    'ventas': 0.4,
                    'reportes': 0.2
                },
                'last_activity': timezone.now() - timedelta(hours=2),
                'usage_drop_detected': False
            }
            
            return usage_data
            
        except Exception as e:
            logger.error(f"Error analyzing usage trends: {e}")
            return {}
    
    def _detect_error_patterns(self, tickets) -> List[Dict[str, Any]]:
        """Detecta patrones de errores"""
        try:
            error_patterns = []
            
            for ticket in tickets:
                # Analizar sentimiento del ticket
                sentiment = self.llm_client.analyze_sentiment(ticket.description)
                
                if sentiment.get('negative', 0) > 0.7:
                    error_patterns.append({
                        'error_type': 'user_frustration',
                        'frequency': 1,
                        'severity': 'high' if sentiment.get('negative', 0) > 0.8 else 'medium',
                        'last_occurrence': ticket.created_at
                    })
            
            return error_patterns
            
        except Exception as e:
            logger.error(f"Error detecting error patterns: {e}")
            return []
    
    def _analyze_satisfaction_trend(self, tickets) -> Dict[str, Any]:
        """Analiza tendencia de satisfacción"""
        try:
            if not tickets:
                return {'trend': 'neutral', 'score': 0.5}
            
            # Simular análisis de satisfacción
            satisfaction_scores = [0.5] * len(tickets)
            avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores)
            
            return {
                'trend': 'stable',
                'score': avg_satisfaction,
                'recent_score': satisfaction_scores[0] if satisfaction_scores else 0.5
            }
            
        except Exception as e:
            logger.error(f"Error analyzing satisfaction trend: {e}")
            return {'trend': 'neutral', 'score': 0.5}
    
    def _detect_potential_issues(self, patterns: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detecta problemas potenciales basados en patrones"""
        try:
            potential_issues = []
            
            # Detectar alta frecuencia de tickets
            if patterns.get('ticket_frequency', 0) > 5:
                potential_issues.append({
                    'type': 'high_ticket_frequency',
                    'severity': 'medium',
                    'description': 'Usuario con alta frecuencia de tickets',
                    'recommendation': 'Revisar configuración o proporcionar capacitación adicional'
                })
            
            return potential_issues
            
        except Exception as e:
            logger.error(f"Error detecting potential issues: {e}")
            return []
    
    def _generate_recommendations(self, patterns: Dict[str, Any], issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Genera recomendaciones proactivas"""
        try:
            recommendations = []
            
            # Recomendaciones basadas en problemas detectados
            for issue in issues:
                if issue['type'] == 'high_ticket_frequency':
                    recommendations.append({
                        'type': 'training',
                        'title': 'Capacitación Adicional',
                        'description': 'Ofrecer sesión de capacitación personalizada',
                        'priority': 'medium',
                        'estimated_impact': 'high'
                    })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []
    
    def create_proactive_alert(self, user_id: int, alert_type: str, title: str, description: str, severity: str = 'medium'):
        """
        Crea una alerta proactiva
        """
        try:
            alert = ProactiveAlert.objects.create(
                customer_id=user_id,
                alert_type=alert_type,
                title=title,
                description=description,
                severity=severity
            )
            
            logger.info(f"Created proactive alert: {alert.id} for user {user_id}")
            return alert
            
        except Exception as e:
            logger.error(f"Error creating proactive alert: {e}")
            return None
    
    def predict_user_needs(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Predice necesidades futuras del usuario
        """
        try:
            # Analizar patrones históricos
            patterns = self.analyze_user_patterns(user_id)
            
            # Predecir necesidades basadas en patrones
            predictions = []
            
            # Predecir necesidad de capacitación
            if patterns.get('ticket_frequency', 0) > 3:
                predictions.append({
                    'need_type': 'training',
                    'probability': 0.8,
                    'timeline': '1_week',
                    'description': 'Alta probabilidad de necesitar capacitación adicional'
                })
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error predicting user needs: {e}")
            return []
    
    def generate_preventive_content(self, user_id: int) -> Dict[str, Any]:
        """
        Genera contenido preventivo personalizado
        """
        try:
            # Analizar patrones del usuario
            patterns = self.analyze_user_patterns(user_id)
            
            # Generar contenido basado en patrones
            content = {
                'personalized_tips': [],
                'relevant_articles': [],
                'tutorials': [],
                'best_practices': []
            }
            
            return content
            
        except Exception as e:
            logger.error(f"Error generating preventive content: {e}")
            return {}

# Instancia global
proactive_agent = ProactiveAgent() 