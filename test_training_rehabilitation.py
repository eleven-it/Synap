#!/usr/bin/env python3
"""
Script de prueba para verificar la rehabilitación del entrenamiento de agentes
y procesamiento de YouTube
"""

import os
import sys
import django
from pathlib import Path

# Configurar Django
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eleven_support.settings')
django.setup()

from support_ai.agent_training_simple import test_agent_training, get_agent_training_service
from support_ai.youtube_training_service import test_youtube_processing, get_youtube_training_service
from support_ai.dynamic_agent_models import DynamicAgent
from support_ai.crew_ai_simple import test_crew_ai_simple
from support_ai.ollama_adapter import test_ollama_connection


def main():
    print("🧪 PRUEBA DE REHABILITACIÓN DE ENTRENAMIENTO")
    print("=" * 60)
    
    # 1. Verificar Ollama
    print("\n1️⃣ Verificando Ollama...")
    ollama_result = test_ollama_connection()
    
    if ollama_result['success']:
        print(f"✅ Ollama conectado correctamente")
        print(f"   Modelo: {ollama_result['model']}")
        print(f"   Tiempo de respuesta: {ollama_result.get('processing_time', 'N/A')}s")
    else:
        print(f"❌ Error con Ollama: {ollama_result['error']}")
        return False
    
    # 2. Verificar CrewAI Simplificado
    print("\n2️⃣ Verificando CrewAI Simplificado...")
    crewai_result = test_crew_ai_simple()
    
    if crewai_result['success']:
        print(f"✅ CrewAI funcionando correctamente")
        print(f"   Pruebas exitosas: {crewai_result['successful_tests']}/{crewai_result['total_tests']}")
    else:
        print(f"❌ Error con CrewAI: {crewai_result['error']}")
        return False
    
    # 3. Verificar Agentes Dinámicos
    print("\n3️⃣ Verificando Agentes Dinámicos...")
    try:
        agents = DynamicAgent.objects.all()
        print(f"✅ {agents.count()} agentes dinámicos encontrados")
        
        if agents.exists():
            for agent in agents[:3]:  # Mostrar primeros 3
                print(f"   - {agent.name} ({agent.module}) - Entrenamiento: {'✅' if agent.training_enabled else '❌'}")
        else:
            print("⚠️ No hay agentes dinámicos configurados")
            
    except Exception as e:
        print(f"❌ Error verificando agentes: {e}")
        return False
    
    # 4. Probar Entrenamiento de Agentes
    print("\n4️⃣ Probando Entrenamiento de Agentes...")
    training_result = test_agent_training()
    
    if training_result['success']:
        print(f"✅ Entrenamiento de agentes funcionando")
        print(f"   Agente: {training_result['agent_name']}")
        print(f"   Datos de prueba: {training_result['test_data_count']}")
    else:
        print(f"⚠️ Entrenamiento de agentes: {training_result['error']}")
        # No fallar aquí, puede que no haya agentes configurados
    
    # 5. Probar Procesamiento de YouTube
    print("\n5️⃣ Probando Procesamiento de YouTube...")
    youtube_result = test_youtube_processing()
    
    if youtube_result['success']:
        print(f"✅ Procesamiento de YouTube funcionando")
        print(f"   yt-dlp disponible: {youtube_result['status']['yt_dlp_available']}")
        print(f"   Ruta yt-dlp: {youtube_result['status']['yt_dlp_path']}")
    else:
        print(f"⚠️ Procesamiento de YouTube: {youtube_result['error']}")
        # No fallar aquí, puede que yt-dlp no esté disponible
    
    # 6. Prueba de Integración Completa
    print("\n6️⃣ Prueba de Integración Completa...")
    try:
        # Crear datos de entrenamiento de ejemplo
        training_data = [
            {
                'input': '¿Cómo puedo resetear mi contraseña?',
                'expected_output': 'Para resetear tu contraseña, ve a Configuración > Seguridad > Cambiar contraseña. Te enviaremos un enlace por email.',
                'category': 'account',
                'difficulty': 'easy'
            },
            {
                'input': 'Mi factura tiene un error, ¿qué hago?',
                'expected_output': 'Entiendo tu preocupación. Por favor, comparte el número de factura y el error específico para ayudarte a resolverlo.',
                'category': 'billing',
                'difficulty': 'medium'
            },
            {
                'input': 'Necesito ayuda técnica con el sistema',
                'expected_output': 'Te ayudo con el problema técnico. Por favor, describe el error específico que estás experimentando.',
                'category': 'technical',
                'difficulty': 'medium'
            }
        ]
        
        # Buscar un agente para entrenar
        agents = DynamicAgent.objects.filter(training_enabled=True)[:1]
        
        if agents.exists():
            agent = agents[0]
            training_service = get_agent_training_service()
            
            # Entrenar el agente
            result = training_service.train_agent(str(agent.id), training_data)
            
            if result['success']:
                print(f"✅ Integración completa exitosa")
                print(f"   Agente entrenado: {result['agent_name']}")
                print(f"   Datos procesados: {result['training_data_count']}")
                print(f"   Tiempo de entrenamiento: {result['training_result'].get('training_time', 'N/A')}s")
            else:
                print(f"⚠️ Entrenamiento falló: {result.get('error', 'Error desconocido')}")
        else:
            print("⚠️ No hay agentes disponibles para entrenar")
            
    except Exception as e:
        print(f"❌ Error en integración: {e}")
        return False
    
    # 7. Resumen Final
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE REHABILITACIÓN")
    print("=" * 60)
    
    summary = {
        'ollama': ollama_result['success'],
        'crewai': crewai_result['success'],
        'agents': agents.count() > 0,
        'training': training_result['success'],
        'youtube': youtube_result['success']
    }
    
    total_checks = len(summary)
    successful_checks = sum(summary.values())
    
    print(f"✅ Ollama: {'Funcionando' if summary['ollama'] else 'Error'}")
    print(f"✅ CrewAI: {'Funcionando' if summary['crewai'] else 'Error'}")
    print(f"✅ Agentes: {'Disponibles' if summary['agents'] else 'No disponibles'}")
    print(f"✅ Entrenamiento: {'Funcionando' if summary['training'] else 'Error'}")
    print(f"✅ YouTube: {'Funcionando' if summary['youtube'] else 'Error'}")
    
    print(f"\n🎯 Resultado: {successful_checks}/{total_checks} componentes rehabilitados")
    
    if successful_checks >= 3:  # Al menos Ollama, CrewAI y Agentes
        print("🎉 ¡REHABILITACIÓN EXITOSA!")
        print("   El sistema está listo para usar")
        return True
    else:
        print("⚠️ Rehabilitación parcial")
        print("   Algunos componentes necesitan atención")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
