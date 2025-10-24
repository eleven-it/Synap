"""
Sistema de Analytics Avanzado para el Dashboard de IA
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from django.core.cache import cache
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone

from .models import SupportTicket, Conversation, CustomerSatisfaction
from .ai_metrics import ai_metrics

logger = logging.getLogger(__name__)


class AIAnalytics:
    """
    Sistema de analytics avanzado para métricas de IA y soporte
    """
    
    def __init__(self):
        self.cache_prefix = "ai_analytics"
    
    def get_comprehensive_metrics(self, days: int = 30) -> Dict[str, Any]:
        """
        Obtiene métricas comprehensivas del sistema
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Métricas de tickets
        tickets_metrics = self._get_tickets_metrics(start_date, end_date)
        
        # Métricas de IA
        ai_metrics_data = self._get_ai_metrics(start_date, end_date)
        
        # Métricas de satisfacción
        satisfaction_metrics = self._get_satisfaction_metrics(start_date, end_date)
        
        # Métricas de rendimiento
        performance_metrics = self._get_performance_metrics(start_date, end_date)
        
        return {
            'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            'tickets': tickets_metrics,
            'ai': ai_metrics_data,
            'satisfaction': satisfaction_metrics,
            'performance': performance_metrics,
            'summary': self._generate_summary(tickets_metrics, ai_metrics_data, satisfaction_metrics)
        }
    
    def _get_tickets_metrics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Métricas de tickets"""
        tickets = SupportTicket.objects.filter(
            created_at__range=(start_date, end_date)
        )
        
        # Estadísticas básicas
        total_tickets = tickets.count()
        open_tickets = tickets.filter(status='open').count()
        resolved_tickets = tickets.filter(status='resolved').count()
        in_progress_tickets = tickets.filter(status='in_progress').count()
        
        # Tiempo promedio de resolución
        resolved_tickets_with_time = tickets.filter(
            status='resolved',
            resolved_at__isnull=False
        )
        
        avg_resolution_time = None
        if resolved_tickets_with_time.exists():
            resolution_times = []
            for ticket in resolved_tickets_with_time:
                if ticket.resolved_at and ticket.created_at:
                    resolution_time = (ticket.resolved_at - ticket.created_at).total_seconds() / 3600  # horas
                    resolution_times.append(resolution_time)
            
            if resolution_times:
                avg_resolution_time = sum(resolution_times) / len(resolution_times)
        
        # Distribución por prioridad
        priority_distribution = dict(
            tickets.values('priority').annotate(count=Count('id')).values_list('priority', 'count')
        )
        
        # Distribución por categoría
        category_distribution = dict(
            tickets.values('category').annotate(count=Count('id')).values_list('category', 'count')
        )
        
        # Tendencia diaria
        daily_trend = []
        current_date = start_date
        while current_date <= end_date:
            next_date = current_date + timedelta(days=1)
            daily_count = tickets.filter(
                created_at__gte=current_date,
                created_at__lt=next_date
            ).count()
            
            daily_trend.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'count': daily_count
            })
            
            current_date = next_date
        
        return {
            'total': total_tickets,
            'open': open_tickets,
            'resolved': resolved_tickets,
            'in_progress': in_progress_tickets,
            'avg_resolution_time_hours': avg_resolution_time,
            'priority_distribution': priority_distribution,
            'category_distribution': category_distribution,
            'daily_trend': daily_trend,
            'resolution_rate': (resolved_tickets / total_tickets * 100) if total_tickets > 0 else 0
        }
    
    def _get_ai_metrics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Métricas de IA"""
        # Obtener métricas de IA del sistema de métricas
        try:
            # Métricas diarias acumuladas
            total_requests = 0
            total_cost = 0.0
            total_successful_requests = 0
            total_failed_requests = 0
            avg_response_time = 0.0
            
            current_date = start_date
            while current_date <= end_date:
                daily_metrics = ai_metrics.get_daily_metrics(current_date.strftime('%Y-%m-%d'))
                
                total_requests += daily_metrics.get('total_requests', 0)
                total_cost += daily_metrics.get('total_cost', 0.0)
                total_successful_requests += daily_metrics.get('total_successful_requests', 0)
                total_failed_requests += daily_metrics.get('total_failed_requests', 0)
                
                if daily_metrics.get('avg_response_time'):
                    avg_response_time += daily_metrics.get('avg_response_time', 0.0)
                
                current_date += timedelta(days=1)
            
            # Calcular promedio de tiempo de respuesta
            days_count = (end_date - start_date).days + 1
            avg_response_time = avg_response_time / days_count if days_count > 0 else 0
            
            # Distribución por proveedor
            provider_distribution = {}
            current_date = start_date
            while current_date <= end_date:
                daily_metrics = ai_metrics.get_daily_metrics(current_date.strftime('%Y-%m-%d'))
                providers = daily_metrics.get('providers', {})
                
                for provider, data in providers.items():
                    if provider not in provider_distribution:
                        provider_distribution[provider] = {
                            'requests': 0,
                            'cost': 0.0
                        }
                    provider_distribution[provider]['requests'] += data.get('requests', 0)
                    provider_distribution[provider]['cost'] += data.get('cost', 0.0)
                
                current_date += timedelta(days=1)
            
            # Distribución por modelo
            model_distribution = {}
            current_date = start_date
            while current_date <= end_date:
                daily_metrics = ai_metrics.get_daily_metrics(current_date.strftime('%Y-%m-%d'))
                models = daily_metrics.get('models', {})
                
                for model, data in models.items():
                    if model not in model_distribution:
                        model_distribution[model] = {
                            'requests': 0,
                            'cost': 0.0
                        }
                    model_distribution[model]['requests'] += data.get('requests', 0)
                    model_distribution[model]['cost'] += data.get('cost', 0.0)
                
                current_date += timedelta(days=1)
            
            return {
                'total_requests': total_requests,
                'total_cost': total_cost,
                'successful_requests': total_successful_requests,
                'failed_requests': total_failed_requests,
                'success_rate': (total_successful_requests / total_requests * 100) if total_requests > 0 else 0,
                'avg_response_time': avg_response_time,
                'provider_distribution': provider_distribution,
                'model_distribution': model_distribution,
                'cost_per_request': (total_cost / total_requests) if total_requests > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo métricas de IA: {str(e)}")
            return {
                'total_requests': 0,
                'total_cost': 0.0,
                'successful_requests': 0,
                'failed_requests': 0,
                'success_rate': 0.0,
                'avg_response_time': 0.0,
                'provider_distribution': {},
                'model_distribution': {},
                'cost_per_request': 0.0
            }
    
    def _get_satisfaction_metrics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Métricas de satisfacción del cliente"""
        ratings = CustomerSatisfaction.objects.filter(
            created_at__range=(start_date, end_date)
        )
        
        total_ratings = ratings.count()
        
        if total_ratings == 0:
            return {
                'total_ratings': 0,
                'avg_overall_rating': 0.0,
                'avg_response_time_rating': 0.0,
                'avg_solution_quality_rating': 0.0,
                'avg_agent_helpfulness_rating': 0.0,
                'rating_distribution': {},
                'sentiment_distribution': {}
            }
        
        # Promedios
        avg_overall = ratings.aggregate(Avg('overall_rating'))['overall_rating__avg'] or 0.0
        avg_response_time = ratings.aggregate(Avg('response_time_rating'))['response_time_rating__avg'] or 0.0
        avg_solution_quality = ratings.aggregate(Avg('solution_quality_rating'))['solution_quality_rating__avg'] or 0.0
        avg_agent_helpfulness = ratings.aggregate(Avg('agent_helpfulness_rating'))['agent_helpfulness_rating__avg'] or 0.0
        
        # Distribución de ratings
        rating_distribution = dict(
            ratings.values('overall_rating').annotate(count=Count('id')).values_list('overall_rating', 'count')
        )
        
        # Distribución de sentimientos
        sentiment_distribution = dict(
            ratings.values('sentiment_label').annotate(count=Count('id')).values_list('sentiment_label', 'count')
        )
        
        return {
            'total_ratings': total_ratings,
            'avg_overall_rating': avg_overall,
            'avg_response_time_rating': avg_response_time,
            'avg_solution_quality_rating': avg_solution_quality,
            'avg_agent_helpfulness_rating': avg_agent_helpfulness,
            'rating_distribution': rating_distribution,
            'sentiment_distribution': sentiment_distribution
        }
    
    def _get_performance_metrics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Métricas de rendimiento del sistema"""
        # Obtener métricas de rendimiento de las últimas 24 horas
        try:
            performance_metrics = ai_metrics.get_performance_metrics(hours=24)
            
            # Calcular métricas adicionales
            tickets_per_hour = SupportTicket.objects.filter(
                created_at__gte=timezone.now() - timedelta(hours=24)
            ).count() / 24
            
            # Tiempo promedio de primera respuesta
            recent_tickets = SupportTicket.objects.filter(
                created_at__gte=timezone.now() - timedelta(days=7)
            )
            
            avg_first_response_time = None
            response_times = []
            
            for ticket in recent_tickets:
                first_response = ticket.conversations.filter(
                    message_type__in=['agent', 'ai']
                ).order_by('created_at').first()
                
                if first_response:
                    response_time = (first_response.created_at - ticket.created_at).total_seconds() / 3600
                    response_times.append(response_time)
            
            if response_times:
                avg_first_response_time = sum(response_times) / len(response_times)
            
            return {
                'ai_performance': performance_metrics,
                'tickets_per_hour': tickets_per_hour,
                'avg_first_response_time_hours': avg_first_response_time,
                'peak_hour': performance_metrics.get('peak_hour'),
                'peak_requests': performance_metrics.get('peak_requests', 0)
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo métricas de rendimiento: {str(e)}")
            return {
                'ai_performance': {},
                'tickets_per_hour': 0,
                'avg_first_response_time_hours': None,
                'peak_hour': None,
                'peak_requests': 0
            }
    
    def _generate_summary(self, tickets_metrics: Dict, ai_metrics: Dict, satisfaction_metrics: Dict) -> Dict[str, Any]:
        """Genera un resumen ejecutivo de las métricas"""
        return {
            'key_insights': [
                f"Se procesaron {tickets_metrics.get('total', 0)} tickets en el período",
                f"La IA procesó {ai_metrics.get('total_requests', 0)} solicitudes con {ai_metrics.get('success_rate', 0):.1f}% de éxito",
                f"El costo promedio por solicitud de IA fue ${ai_metrics.get('cost_per_request', 0):.6f}",
                f"La satisfacción promedio del cliente fue {satisfaction_metrics.get('avg_overall_rating', 0):.1f}/5",
                f"El tiempo promedio de resolución fue {tickets_metrics.get('avg_resolution_time_hours', 0):.1f} horas"
            ],
            'recommendations': self._generate_recommendations(tickets_metrics, ai_metrics, satisfaction_metrics),
            'trends': self._identify_trends(tickets_metrics, ai_metrics)
        }
    
    def _generate_recommendations(self, tickets_metrics: Dict, ai_metrics: Dict, satisfaction_metrics: Dict) -> List[str]:
        """Genera recomendaciones basadas en las métricas"""
        recommendations = []
        
        # Recomendaciones basadas en tickets
        resolution_rate = tickets_metrics.get('resolution_rate', 0)
        if resolution_rate < 80:
            recommendations.append("Considerar aumentar recursos para mejorar la tasa de resolución de tickets")
        
        avg_resolution_time = tickets_metrics.get('avg_resolution_time_hours', 0)
        if avg_resolution_time > 24:
            recommendations.append("Optimizar procesos para reducir el tiempo promedio de resolución")
        
        # Recomendaciones basadas en IA
        success_rate = ai_metrics.get('success_rate', 0)
        if success_rate < 90:
            recommendations.append("Revisar configuración de IA para mejorar la tasa de éxito")
        
        cost_per_request = ai_metrics.get('cost_per_request', 0)
        if cost_per_request > 0.001:
            recommendations.append("Considerar modelos más económicos para reducir costos de IA")
        
        # Recomendaciones basadas en satisfacción
        avg_rating = satisfaction_metrics.get('avg_overall_rating', 0)
        if avg_rating < 4.0:
            recommendations.append("Implementar mejoras en la calidad del servicio para aumentar satisfacción")
        
        if not recommendations:
            recommendations.append("El sistema está funcionando bien. Mantener el rendimiento actual")
        
        return recommendations
    
    def _identify_trends(self, tickets_metrics: Dict, ai_metrics: Dict) -> List[str]:
        """Identifica tendencias en los datos"""
        trends = []
        
        # Analizar tendencia de tickets
        daily_trend = tickets_metrics.get('daily_trend', [])
        if len(daily_trend) >= 7:
            recent_avg = sum(day['count'] for day in daily_trend[-7:]) / 7
            older_avg = sum(day['count'] for day in daily_trend[-14:-7]) / 7
            
            if recent_avg > older_avg * 1.2:
                trends.append("Aumento en el volumen de tickets (últimos 7 días)")
            elif recent_avg < older_avg * 0.8:
                trends.append("Disminución en el volumen de tickets (últimos 7 días)")
        
        # Analizar tendencia de IA
        total_requests = ai_metrics.get('total_requests', 0)
        if total_requests > 1000:
            trends.append("Alto uso de IA - considerar optimización de costos")
        
        return trends
    
    def get_realtime_dashboard_data(self) -> Dict[str, Any]:
        """Obtiene datos en tiempo real para el dashboard"""
        now = timezone.now()
        last_hour = now - timedelta(hours=1)
        last_24h = now - timedelta(hours=24)
        
        # Tickets en tiempo real
        tickets_last_hour = SupportTicket.objects.filter(
            created_at__gte=last_hour
        ).count()
        
        tickets_last_24h = SupportTicket.objects.filter(
            created_at__gte=last_24h
        ).count()
        
        # Conversaciones en tiempo real
        conversations_last_hour = Conversation.objects.filter(
            created_at__gte=last_hour
        ).count()
        
        # Métricas de IA en tiempo real
        try:
            hourly_metrics = ai_metrics.get_hourly_metrics(
                now.strftime('%Y-%m-%d'), 
                now.hour
            )
        except:
            hourly_metrics = {
                'total_requests': 0,
                'total_cost': 0.0,
                'avg_response_time': 0.0
            }
        
        return {
            'timestamp': now.isoformat(),
            'tickets': {
                'last_hour': tickets_last_hour,
                'last_24h': tickets_last_24h,
                'open_now': SupportTicket.objects.filter(status='open').count()
            },
            'conversations': {
                'last_hour': conversations_last_hour,
                'total_today': Conversation.objects.filter(
                    created_at__date=now.date()
                ).count()
            },
            'ai': {
                'requests_last_hour': hourly_metrics.get('total_requests', 0),
                'cost_last_hour': hourly_metrics.get('total_cost', 0.0),
                'avg_response_time': hourly_metrics.get('avg_response_time', 0.0)
            }
        }


# Instancia global
ai_analytics = AIAnalytics() 