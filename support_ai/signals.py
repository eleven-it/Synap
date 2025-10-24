"""
Señales para la app de soporte IA
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth.models import User

from .models import (
    SupportTicket, Conversation, SupportMetrics, 
    SupportConfiguration, AIAgent
)


@receiver(post_save, sender=SupportTicket)
def update_ticket_metrics(sender, instance, created, **kwargs):
    """Actualiza métricas cuando se crea o modifica un ticket"""
    if created:
        # Crear métrica para el día actual
        today = timezone.now().date()
        metrics, created = SupportMetrics.objects.get_or_create(
            company=instance.company,
            date=today,
            defaults={
                'total_tickets': 0,
                'resolved_tickets': 0,
                'ai_resolved_tickets': 0,
                'escalated_tickets': 0
            }
        )
        
        # Incrementar contador de tickets
        metrics.total_tickets += 1
        
        # Si fue resuelto por IA
        if instance.ai_resolved:
            metrics.ai_resolved_tickets += 1
        
        # Si fue escalado
        if instance.status in ['waiting_agent']:
            metrics.escalated_tickets += 1
        
        metrics.save()
    
    # Si el ticket se resolvió
    if instance.status == 'resolved' and not created:
        today = timezone.now().date()
        try:
            metrics = SupportMetrics.objects.get(
                company=instance.company,
                date=today
            )
            metrics.resolved_tickets += 1
            metrics.save()
        except SupportMetrics.DoesNotExist:
            pass


@receiver(post_save, sender=Conversation)
def update_agent_metrics(sender, instance, created, **kwargs):
    """Actualiza métricas de agentes IA cuando se crea una conversación"""
    if created and instance.message_type == 'ai' and instance.ai_agent_used:
        try:
            agent = AIAgent.objects.get(agent_type=instance.ai_agent_used)
            agent.total_conversations += 1
            
            # Calcular tasa de éxito (simplificado)
            if instance.ai_confidence > 0.7:
                agent.success_rate = (
                    (agent.success_rate * (agent.total_conversations - 1) + 1) / 
                    agent.total_conversations
                )
            
            # Actualizar tiempo promedio de respuesta
            if instance.ai_processing_time > 0:
                agent.avg_response_time = (
                    (agent.avg_response_time * (agent.total_conversations - 1) + instance.ai_processing_time) / 
                    agent.total_conversations
                )
            
            agent.save()
        except AIAgent.DoesNotExist:
            pass


@receiver(post_save, sender=User)
def create_support_configuration(sender, instance, created, **kwargs):
    """Crea configuración de soporte para nuevas empresas"""
    if created and hasattr(instance, 'company'):
        try:
            SupportConfiguration.objects.get_or_create(
                company=instance.company,
                defaults={
                    'auto_assign_tickets': True,
                    'enable_ai_responses': True,
                    'enable_voice_input': True,
                    'enable_file_upload': True,
                    'ai_confidence_threshold': 0.7,
                    'max_ai_conversations': 5,
                    'web_enabled': True,
                    'email_enabled': True,
                    'whatsapp_enabled': False,
                    'voice_enabled': True,
                    'max_file_size': 10,
                    'default_sla_hours': 24
                }
            )
        except Exception:
            pass 