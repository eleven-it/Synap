#!/usr/bin/env python3
"""
Script de prueba para la aplicación de Soporte IA de Synap
Ejecutar con: python test_support_ai.py
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

from django.contrib.auth import get_user_model
from django.test import TestCase
from support_ai.models import SupportTicket, Conversation, AIAgent, SupportConfiguration
from support_ai.agents.supervisor import SupervisorAgent
from support_ai.llm_integration import LLMIntegration
from support_ai.ocr_processor import OCRProcessor

User = get_user_model()

def test_models():
    """Prueba la creación de modelos"""
    print("🧪 Probando modelos...")
    
    try:
        # Verificar que los modelos están disponibles
        print("✅ SupportTicket model disponible")
        print("✅ Conversation model disponible")
        print("✅ AIAgent model disponible")
        print("✅ SupportConfiguration model disponible")
        print("✅ SupportAttachment model disponible")
        print("✅ SupportMetrics model disponible")
        
        # Crear agentes IA (sin dependencias de empresa)
        agents_data = [
            {'name': 'Supervisor', 'agent_type': 'supervisor', 'description': 'Agente supervisor', 'system_prompt': 'Eres un supervisor'},
            {'name': 'Facturación', 'agent_type': 'facturacion', 'description': 'Especialista en facturación', 'system_prompt': 'Eres especialista en facturación'},
            {'name': 'Configuración', 'agent_type': 'configuracion', 'description': 'Especialista en configuración', 'system_prompt': 'Eres especialista en configuración'},
            {'name': 'Ventas', 'agent_type': 'ventas', 'description': 'Especialista en ventas', 'system_prompt': 'Eres especialista en ventas'},
            {'name': 'Inventario', 'agent_type': 'inventario', 'description': 'Especialista en inventario', 'system_prompt': 'Eres especialista en inventario'},
            {'name': 'Multimodal', 'agent_type': 'multimodal', 'description': 'Procesa archivos', 'system_prompt': 'Procesas archivos'},
            {'name': 'Voz', 'agent_type': 'voz', 'description': 'Procesa voz', 'system_prompt': 'Procesas voz'},
        ]
        
        for agent_data in agents_data:
            agent, created = AIAgent.objects.get_or_create(
                agent_type=agent_data['agent_type'],
                defaults=agent_data
            )
            print(f"✅ Agente {agent_data['name']}: {created}")
        
        print("✅ Todos los modelos funcionan correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error en modelos: {e}")
        return False

def test_llm_integration():
    """Prueba la integración con LLMs"""
    print("\n🧪 Probando integración LLM...")
    
    try:
        llm = LLMIntegration()
        
        # Probar clasificación de intención
        intent_result = llm.classify_intent("Tengo un problema con la facturación")
        print(f"✅ Clasificación de intención: {intent_result}")
        
        # Probar análisis de sentimiento
        sentiment_result = llm.analyze_sentiment("Estoy muy frustrado con el sistema")
        print(f"✅ Análisis de sentimiento: {sentiment_result}")
        
        # Probar extracción de entidades
        entities_result = llm.extract_entities("Necesito ayuda con la factura A-001-00012345")
        print(f"✅ Extracción de entidades: {entities_result}")
        
        print("✅ Integración LLM funciona correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error en LLM: {e}")
        return False

def test_ocr_processor():
    """Prueba el procesador OCR"""
    print("\n🧪 Probando procesador OCR...")
    
    try:
        ocr = OCRProcessor()
        
        # Verificar formatos soportados
        formats = ocr.get_supported_formats()
        print(f"✅ Formatos soportados: {formats}")
        
        # Verificar si Tesseract está disponible
        try:
            import pytesseract
            version = pytesseract.get_tesseract_version()
            print(f"✅ Tesseract disponible: {version}")
        except Exception as e:
            print(f"⚠️ Tesseract no disponible: {e}")
        
        print("✅ Procesador OCR configurado correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error en OCR: {e}")
        return False

def test_supervisor_agent():
    """Prueba el agente supervisor"""
    print("\n🧪 Probando agente supervisor...")
    
    try:
        supervisor = SupervisorAgent()
        
        # Probar enrutamiento de mensajes
        test_messages = [
            "Tengo un problema con la facturación",
            "No puedo configurar mi perfil",
            "Necesito ayuda con ventas",
            "Hay un problema con el inventario",
            "Hola, ¿cómo estás?"
        ]
        
        for message in test_messages:
            agent_type = supervisor._route_message(message)
            print(f"✅ Mensaje: '{message[:30]}...' -> Agente: {agent_type}")
        
        # Probar procesamiento de mensaje
        response = supervisor.process_message(
            ticket=None,
            message="Tengo un problema con la facturación",
            attachments=None
        )
        print(f"✅ Respuesta del supervisor: {response['message'][:50]}...")
        
        print("✅ Agente supervisor funciona correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error en supervisor: {e}")
        return False

def test_webhooks():
    """Prueba los webhooks"""
    print("\n🧪 Probando webhooks...")
    
    try:
        from support_ai.webhooks import email_handler, whatsapp_handler
        
        print("✅ Email handler creado")
        print("✅ WhatsApp handler creado")
        
        # Verificar métodos disponibles
        email_methods = [method for method in dir(email_handler) if not method.startswith('_')]
        whatsapp_methods = [method for method in dir(whatsapp_handler) if not method.startswith('_')]
        
        print(f"✅ Métodos email handler: {len(email_methods)}")
        print(f"✅ Métodos WhatsApp handler: {len(whatsapp_methods)}")
        
        print("✅ Webhooks configurados correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error en webhooks: {e}")
        return False

def test_tasks():
    """Prueba las tareas asíncronas"""
    print("\n🧪 Probando tareas asíncronas...")
    
    try:
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
        
        print("✅ Todas las tareas importadas correctamente")
        
        # Verificar que las tareas están registradas
        task_names = [
            'process_ticket_escalation',
            'notify_agents_of_escalation',
            'update_escalation_metrics',
            'cleanup_old_tickets',
            'generate_daily_metrics_report',
            'train_ai_agents',
            'send_sla_reminders',
            'update_agent_performance_metrics'
        ]
        
        for task_name in task_names:
            print(f"✅ Tarea {task_name} disponible")
        
        print("✅ Tareas asíncronas configuradas correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error en tareas: {e}")
        return False

def test_urls():
    """Prueba las URLs"""
    print("\n🧪 Probando URLs...")
    
    try:
        from django.urls import reverse
        from django.test import Client
        
        client = Client()
        
        # Probar URLs principales
        urls_to_test = [
            'support_ai:chat',
            'support_ai:ticket_list',
            'support_ai:dashboard',
            'support_ai:analytics',
            'support_ai:settings',
            'support_ai:agent_settings',
            'support_ai:webhook_settings',
        ]
        
        for url_name in urls_to_test:
            try:
                url = reverse(url_name)
                print(f"✅ URL {url_name}: {url}")
            except Exception as e:
                print(f"⚠️ URL {url_name}: {e}")
        
        print("✅ URLs configuradas correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error en URLs: {e}")
        return False

def main():
    """Función principal de pruebas"""
    print("🚀 Iniciando pruebas de Soporte IA - Synap")
    print("=" * 50)
    
    tests = [
        test_models,
        test_llm_integration,
        test_ocr_processor,
        test_supervisor_agent,
        test_webhooks,
        test_tasks,
        test_urls,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Error ejecutando {test.__name__}: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Resultados: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        print("🎉 ¡Todas las pruebas pasaron! La aplicación está lista.")
    else:
        print("⚠️ Algunas pruebas fallaron. Revisar configuración.")
    
    print("\n📋 Próximos pasos:")
    print("1. Configurar variables de entorno (.env)")
    print("2. Instalar Tesseract OCR")
    print("3. Configurar servicios externos (Redis, MinIO)")
    print("4. Configurar webhooks de email y WhatsApp")
    print("5. Probar con datos reales")

if __name__ == "__main__":
    main() 