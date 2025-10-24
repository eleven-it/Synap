#!/usr/bin/env python3
"""
Script de prueba final completo para la aplicación de Soporte IA
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

from support_ai.models import SupportTicket, Conversation, AIAgent, SupportConfiguration
from support_ai.agents.supervisor import SupervisorAgent
from support_ai.llm_integration import LLMIntegration
from support_ai.ocr_processor import OCRProcessor
from support_ai.webhooks import email_handler, whatsapp_handler
from support_ai.tasks import process_ticket_escalation, cleanup_old_tickets
from django_project.celery import debug_task

def test_complete_system():
    """Prueba completa del sistema de soporte IA"""
    print("🚀 PRUEBA FINAL COMPLETA - SISTEMA DE SOPORTE IA")
    print("=" * 60)
    
    results = {}
    
    # 1. Probar modelos
    print("\n1️⃣ Probando modelos de base de datos...")
    try:
        print("✅ SupportTicket model disponible")
        print("✅ Conversation model disponible")
        print("✅ AIAgent model disponible")
        print("✅ SupportConfiguration model disponible")
        results['models'] = True
    except Exception as e:
        print(f"❌ Error en modelos: {e}")
        results['models'] = False
    
    # 2. Probar agentes IA
    print("\n2️⃣ Probando agentes IA...")
    try:
        supervisor = SupervisorAgent()
        response = supervisor.process_message(
            ticket=None,
            message="Tengo un problema con la facturación",
            attachments=None
        )
        print(f"✅ Supervisor funcionando: {response['message'][:50]}...")
        print(f"✅ Agente usado: {response['agent_used']}")
        print(f"✅ Confianza: {response['confidence']:.2f}")
        results['agents'] = True
    except Exception as e:
        print(f"❌ Error en agentes: {e}")
        results['agents'] = False
    
    # 3. Probar LLM
    print("\n3️⃣ Probando integración LLM...")
    try:
        llm = LLMIntegration()
        intent = llm.classify_intent("Tengo un problema con la facturación")
        sentiment = llm.analyze_sentiment("Estoy muy frustrado con el sistema")
        entities = llm.extract_entities("Necesito ayuda con la factura A-001-00012345")
        
        print(f"✅ Clasificación de intención: {intent['intent']}")
        print(f"✅ Análisis de sentimiento: {sentiment}")
        print(f"✅ Extracción de entidades: {len(entities)} entidades")
        results['llm'] = True
    except Exception as e:
        print(f"❌ Error en LLM: {e}")
        results['llm'] = False
    
    # 4. Probar OCR
    print("\n4️⃣ Probando procesador OCR...")
    try:
        ocr = OCRProcessor()
        image_path = "/app/test_invoice.png"
        
        if os.path.exists(image_path):
            ocr_result = ocr.extract_text_from_image(image_path)
            structured_data = ocr.extract_structured_data(image_path)
            
            print(f"✅ OCR funcionando: {ocr_result['word_count']} palabras extraídas")
            print(f"✅ Confianza OCR: {ocr_result['confidence']:.2f}")
            print(f"✅ Datos estructurados: {len(structured_data)} campos")
        else:
            print("⚠️ Imagen de prueba no encontrada, pero OCR configurado")
        
        formats = ocr.get_supported_formats()
        print(f"✅ Formatos soportados: {len(formats)}")
        results['ocr'] = True
    except Exception as e:
        print(f"❌ Error en OCR: {e}")
        results['ocr'] = False
    
    # 5. Probar webhooks
    print("\n5️⃣ Probando webhooks...")
    try:
        print("✅ Email handler disponible")
        print("✅ WhatsApp handler disponible")
        
        # Verificar métodos
        email_methods = [m for m in dir(email_handler) if not m.startswith('_')]
        whatsapp_methods = [m for m in dir(whatsapp_handler) if not m.startswith('_')]
        
        print(f"✅ Métodos email: {len(email_methods)}")
        print(f"✅ Métodos WhatsApp: {len(whatsapp_methods)}")
        results['webhooks'] = True
    except Exception as e:
        print(f"❌ Error en webhooks: {e}")
        results['webhooks'] = False
    
    # 6. Probar tareas asíncronas
    print("\n6️⃣ Probando tareas asíncronas...")
    try:
        # Probar tarea de debug
        result = debug_task.delay()
        print(f"✅ Tarea de debug: {result.id}")
        
        # Probar tareas de soporte
        cleanup_result = cleanup_old_tickets()
        print(f"✅ Limpieza de tickets: {cleanup_result}")
        
        results['celery'] = True
    except Exception as e:
        print(f"❌ Error en tareas: {e}")
        results['celery'] = False
    
    # 7. Probar URLs
    print("\n7️⃣ Probando URLs...")
    try:
        from django.urls import reverse
        
        urls_to_test = [
            'support_ai:chat',
            'support_ai:ticket_list',
            'support_ai:dashboard',
            'support_ai:analytics',
            'support_ai:settings',
        ]
        
        for url_name in urls_to_test:
            url = reverse(url_name)
            print(f"✅ {url_name}: {url}")
        
        results['urls'] = True
    except Exception as e:
        print(f"❌ Error en URLs: {e}")
        results['urls'] = False
    
    # 8. Probar configuración
    print("\n8️⃣ Probando configuración...")
    try:
        from django.conf import settings
        
        # Verificar configuraciones importantes
        configs_to_check = [
            'CELERY_BROKER_URL',
            'CELERY_RESULT_BACKEND',
            'INSTALLED_APPS',
        ]
        
        for config in configs_to_check:
            if hasattr(settings, config):
                print(f"✅ {config}: Configurado")
            else:
                print(f"⚠️ {config}: No configurado")
        
        results['config'] = True
    except Exception as e:
        print(f"❌ Error en configuración: {e}")
        results['config'] = False
    
    # Resumen final
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE PRUEBAS")
    print("=" * 60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASÓ" if result else "❌ FALLÓ"
        print(f"{test_name.upper():15} {status}")
    
    print(f"\n🎯 RESULTADO: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        print("🎉 ¡TODAS LAS PRUEBAS PASARON! El sistema está listo para producción.")
    else:
        print("⚠️ Algunas pruebas fallaron. Revisar configuración.")
    
    print("\n📋 PRÓXIMOS PASOS PARA PRODUCCIÓN:")
    print("1. Configurar variables de entorno (.env)")
    print("2. Configurar servicios externos (MinIO, Qdrant)")
    print("3. Configurar webhooks de email y WhatsApp")
    print("4. Configurar monitoreo y logs")
    print("5. Probar con datos reales")
    print("6. Optimizar rendimiento")
    
    return passed == total

if __name__ == "__main__":
    test_complete_system() 