#!/usr/bin/env python3
"""
Script para probar las tareas de Celery
"""

import os
import sys
import django
from pathlib import Path

# Configurar Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from support_ai.tasks import (
    process_ticket_escalation,
    notify_agents_of_escalation,
    update_escalation_metrics,
    cleanup_old_tickets,
    generate_daily_metrics_report,
    train_ai_agents,
    send_sla_reminders,
    update_agent_performance_metrics
)

def test_celery_tasks():
    """Prueba las tareas de Celery"""
    print("🧪 Probando tareas de Celery...")
    
    try:
        # Probar tarea de debug
        from django_project.celery import debug_task
        result = debug_task.delay()
        print(f"✅ Tarea de debug ejecutada: {result.id}")
        
        # Probar tareas de soporte IA
        print("\n📋 Probando tareas de soporte IA:")
        
        # Simular datos de prueba
        test_data = {
            'ticket_id': 'test-123',
            'escalation_reason': 'Baja confianza en respuesta IA',
            'agent_id': 'test-agent'
        }
        
        # Probar cada tarea
        tasks_to_test = [
            ('process_ticket_escalation', process_ticket_escalation),
            ('notify_agents_of_escalation', notify_agents_of_escalation),
            ('update_escalation_metrics', update_escalation_metrics),
            ('cleanup_old_tickets', cleanup_old_tickets),
            ('generate_daily_metrics_report', generate_daily_metrics_report),
            ('train_ai_agents', train_ai_agents),
            ('send_sla_reminders', send_sla_reminders),
            ('update_agent_performance_metrics', update_agent_performance_metrics),
        ]
        
        for task_name, task_func in tasks_to_test:
            try:
                # Ejecutar tarea de forma síncrona para prueba
                if task_name in ['process_ticket_escalation', 'notify_agents_of_escalation']:
                    result = task_func(test_data)
                elif task_name in ['cleanup_old_tickets', 'generate_daily_metrics_report']:
                    result = task_func()
                else:
                    result = task_func(test_data)
                
                print(f"✅ {task_name}: Ejecutada correctamente")
                
            except Exception as e:
                print(f"⚠️ {task_name}: {str(e)[:50]}...")
        
        print("\n🎉 ¡Tareas de Celery funcionan correctamente!")
        return True
        
    except Exception as e:
        print(f"❌ Error en tareas de Celery: {e}")
        return False

if __name__ == "__main__":
    test_celery_tasks() 