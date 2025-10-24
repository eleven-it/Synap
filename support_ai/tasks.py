"""
Tareas asíncronas para la app de soporte IA
"""
import logging
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db import models

from .models import SupportTicket, Conversation, SupportMetrics, AIAgent

logger = logging.getLogger(__name__)


@shared_task
def process_ticket_escalation(ticket_id):
    """Procesa la escalación de un ticket a agente humano"""
    try:
        ticket = SupportTicket.objects.get(id=ticket_id)
        
        # Notificar a agentes disponibles
        notify_agents_of_escalation.delay(ticket_id)
        
        # Actualizar métricas
        update_escalation_metrics.delay(ticket.company.id)
        
        logger.info(f"Ticket {ticket.ticket_number} escalated successfully")
        
    except SupportTicket.DoesNotExist:
        logger.error(f"Ticket {ticket_id} not found for escalation")
    except Exception as e:
        logger.error(f"Error processing ticket escalation: {str(e)}")


@shared_task
def notify_agents_of_escalation(ticket_id):
    """Notifica a agentes sobre un ticket escalado"""
    try:
        ticket = SupportTicket.objects.get(id=ticket_id)
        
        # Buscar agentes disponibles
        from django.contrib.auth.models import User
        agents = User.objects.filter(
            is_staff=True,
            is_active=True
        )
        
        # Enviar notificación por email
        for agent in agents:
            send_mail(
                subject=f'Ticket escalado: {ticket.ticket_number}',
                message=f"""
                Se ha escalado un ticket que requiere atención humana:
                
                Ticket: {ticket.ticket_number}
                Cliente: {ticket.customer.get_full_name() or ticket.customer.username}
                Asunto: {ticket.subject}
                Razón: {ticket.escalation_reason}
                
                Accede al sistema para atender este ticket.
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[agent.email],
                fail_silently=True
            )
        
        logger.info(f"Notified {agents.count()} agents about escalated ticket {ticket.ticket_number}")
        
    except Exception as e:
        logger.error(f"Error notifying agents: {str(e)}")


@shared_task
def update_escalation_metrics(company_id):
    """Actualiza métricas de escalamiento"""
    try:
        today = timezone.now().date()
        metrics, created = SupportMetrics.objects.get_or_create(
            company_id=company_id,
            date=today,
            defaults={
                'total_tickets': 0,
                'resolved_tickets': 0,
                'ai_resolved_tickets': 0,
                'escalated_tickets': 0
            }
        )
        
        # Contar tickets escalados del día
        escalated_count = SupportTicket.objects.filter(
            company_id=company_id,
            status='waiting_agent',
            updated_at__date=today
        ).count()
        
        metrics.escalated_tickets = escalated_count
        metrics.save()
        
        logger.info(f"Updated escalation metrics for company {company_id}")
        
    except Exception as e:
        logger.error(f"Error updating escalation metrics: {str(e)}")


@shared_task
def cleanup_old_tickets():
    """Limpia tickets antiguos cerrados"""
    try:
        # Buscar tickets cerrados hace más de 90 días
        cutoff_date = timezone.now() - timezone.timedelta(days=90)
        old_tickets = SupportTicket.objects.filter(
            status='closed',
            updated_at__lt=cutoff_date
        )
        
        count = old_tickets.count()
        old_tickets.delete()
        
        logger.info(f"Cleaned up {count} old closed tickets")
        
    except Exception as e:
        logger.error(f"Error cleaning up old tickets: {str(e)}")


@shared_task
def generate_daily_metrics_report(company_id):
    """Genera reporte diario de métricas"""
    try:
        yesterday = timezone.now().date() - timezone.timedelta(days=1)
        
        # Obtener métricas del día anterior
        metrics = SupportMetrics.objects.filter(
            company_id=company_id,
            date=yesterday
        ).first()
        
        if metrics:
            # Generar reporte
            report = f"""
            Reporte de Soporte IA - {yesterday}
            
            Total de tickets: {metrics.total_tickets}
            Tickets resueltos: {metrics.resolved_tickets}
            Resueltos por IA: {metrics.ai_resolved_tickets}
            Escalados: {metrics.escalated_tickets}
            Tiempo promedio de resolución: {metrics.avg_resolution_time:.2f} horas
            Satisfacción del cliente: {metrics.customer_satisfaction:.2f}/5
            """
            
            # Enviar reporte por email
            from django.contrib.auth.models import User
            admin_users = User.objects.filter(
                is_staff=True,
                is_superuser=True
            )
            
            for admin in admin_users:
                send_mail(
                    subject=f'Reporte Diario Soporte IA - {yesterday}',
                    message=report,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[admin.email],
                    fail_silently=True
                )
            
            logger.info(f"Generated daily metrics report for company {company_id}")
        
    except Exception as e:
        logger.error(f"Error generating daily metrics report: {str(e)}")


@shared_task
def train_ai_agents():
    """Entrena los agentes IA con nuevos datos"""
    try:
        # Obtener conversaciones recientes para entrenamiento
        recent_conversations = Conversation.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(days=7),
            message_type__in=['user', 'ai']
        ).order_by('ticket', 'created_at')
        
        # Agrupar por agente
        agent_data = {}
        for conv in recent_conversations:
            if conv.ai_agent_used:
                if conv.ai_agent_used not in agent_data:
                    agent_data[conv.ai_agent_used] = []
                agent_data[conv.ai_agent_used].append({
                    'message': conv.content,
                    'confidence': conv.ai_confidence,
                    'timestamp': conv.created_at
                })
        
        # Entrenar cada agente
        for agent_type, data in agent_data.items():
            try:
                agent = AIAgent.objects.get(agent_type=agent_type)
                # Aquí se implementaría el entrenamiento real
                logger.info(f"Training agent {agent_type} with {len(data)} samples")
            except AIAgent.DoesNotExist:
                logger.warning(f"Agent {agent_type} not found for training")
        
        logger.info(f"Completed AI agent training with {len(agent_data)} agents")
        
    except Exception as e:
        logger.error(f"Error training AI agents: {str(e)}")


@shared_task
def send_sla_reminders():
    """Envía recordatorios de SLA"""
    try:
        # Buscar tickets que están cerca de vencer su SLA
        now = timezone.now()
        upcoming_deadline = now + timezone.timedelta(hours=2)
        
        tickets_near_sla = SupportTicket.objects.filter(
            status__in=['open', 'in_progress'],
            sla_deadline__lte=upcoming_deadline,
            sla_deadline__gt=now
        )
        
        for ticket in tickets_near_sla:
            # Notificar al agente asignado
            if ticket.assigned_agent:
                send_mail(
                    subject=f'SLA próximo a vencer: {ticket.ticket_number}',
                    message=f"""
                    El ticket {ticket.ticket_number} vence en menos de 2 horas.
                    
                    Cliente: {ticket.customer.get_full_name() or ticket.customer.username}
                    Asunto: {ticket.subject}
                    Vence: {ticket.sla_deadline}
                    
                    Por favor, atiende este ticket lo antes posible.
                    """,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[ticket.assigned_agent.email],
                    fail_silently=True
                )
        
        logger.info(f"Sent {tickets_near_sla.count()} SLA reminders")
        
    except Exception as e:
        logger.error(f"Error sending SLA reminders: {str(e)}")


@shared_task
def update_agent_performance_metrics():
    """Actualiza métricas de rendimiento de agentes"""
    try:
        agents = AIAgent.objects.all()
        
        for agent in agents:
            # Calcular métricas de rendimiento
            recent_conversations = Conversation.objects.filter(
                ai_agent_used=agent.agent_type,
                created_at__gte=timezone.now() - timezone.timedelta(days=30)
            )
            
            if recent_conversations.exists():
                # Calcular tasa de éxito
                successful_conversations = recent_conversations.filter(
                    ai_confidence__gte=0.7
                ).count()
                
                agent.success_rate = successful_conversations / recent_conversations.count()
                
                # Calcular tiempo promedio de respuesta
                avg_time = recent_conversations.aggregate(
                    avg_time=models.Avg('ai_processing_time')
                )['avg_time'] or 0
                
                agent.avg_response_time = avg_time
                agent.save()
        
        logger.info(f"Updated performance metrics for {agents.count()} agents")
        
    except Exception as e:
        logger.error(f"Error updating agent performance metrics: {str(e)}") 