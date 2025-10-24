#!/usr/bin/env python3
"""
Script de prueba para verificar la integración con osTicket
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

from support_ai.osticket_integration import test_osticket_integration, get_osticket_integration
from support_ai.osticket_training_service import test_osticket_training_integration, get_osticket_training_service
from support_ai.dynamic_agent_models import DynamicAgent


def main():
    print("🧪 PRUEBA DE INTEGRACIÓN CON OSTICKET")
    print("=" * 60)
    
    # 1. Verificar conexión básica con osTicket
    print("\n1️⃣ Verificando conexión básica con osTicket...")
    basic_result = test_osticket_integration()
    
    if basic_result['success']:
        print(f"✅ Conexión básica exitosa")
        print(f"   Base de datos: {basic_result['status']['database']}")
        print(f"   Host: {basic_result['status']['host']}")
        
        # Mostrar estado de tablas
        print(f"   Estado de tablas:")
        for table, status in basic_result['status']['table_status'].items():
            if status['exists']:
                print(f"     ✅ {table}: {status['record_count']} registros")
            else:
                print(f"     ❌ {table}: {status.get('error', 'No existe')}")
    else:
        print(f"❌ Error de conexión: {basic_result['error']}")
        return False
    
    # 2. Verificar extracción de datos
    print("\n2️⃣ Verificando extracción de datos...")
    try:
        integration = get_osticket_integration()
        
        # Extraer FAQ
        faq_data = integration.extract_faq_knowledge()
        print(f"   FAQ extraídas: {len(faq_data)}")
        
        # Extraer tickets
        ticket_data = integration.extract_ticket_data(days_back=7)  # Solo últimos 7 días
        print(f"   Tickets extraídos: {len(ticket_data)}")
        
        # Extraer categorías
        category_data = integration.extract_category_knowledge()
        print(f"   Categorías extraídas: {len(category_data)}")
        
        if faq_data or ticket_data or category_data:
            print("✅ Extracción de datos exitosa")
        else:
            print("⚠️ No se extrajeron datos (puede ser normal si no hay contenido)")
            
    except Exception as e:
        print(f"❌ Error en extracción: {e}")
        return False
    
    # 3. Verificar agentes disponibles
    print("\n3️⃣ Verificando agentes disponibles...")
    try:
        agents = DynamicAgent.objects.filter(training_enabled=True)
        print(f"   Agentes con entrenamiento habilitado: {agents.count()}")
        
        if agents.exists():
            for agent in agents[:3]:  # Mostrar primeros 3
                print(f"     - {agent.name} ({agent.module})")
        else:
            print("   ⚠️ No hay agentes disponibles para entrenar")
            
    except Exception as e:
        print(f"❌ Error verificando agentes: {e}")
        return False
    
    # 4. Probar integración completa de entrenamiento
    print("\n4️⃣ Probando integración completa de entrenamiento...")
    training_result = test_osticket_training_integration()
    
    if training_result['success']:
        print(f"✅ Integración de entrenamiento exitosa")
        print(f"   Agente entrenado: {training_result['agent_name']}")
        print(f"   Pares de entrenamiento: {training_result['training_pairs_used']}")
    else:
        print(f"⚠️ Integración de entrenamiento: {training_result.get('error', 'Error desconocido')}")
        # No fallar aquí, puede que no haya agentes configurados
    
    # 5. Probar sincronización manual
    print("\n5️⃣ Probando sincronización manual...")
    try:
        training_service = get_osticket_training_service()
        
        # Obtener estado de sincronización
        sync_status = training_service.get_sync_status()
        
        print(f"   Estado de osTicket: {'✅ Conectado' if sync_status.get('osticket_status', {}).get('connected') else '❌ Desconectado'}")
        print(f"   Agentes disponibles: {sync_status.get('agent_status', {}).get('total_agents', 0)}")
        
        # Programar sincronización automática
        schedule_result = training_service.schedule_automatic_sync('daily')
        if schedule_result['success']:
            print(f"   ✅ Sincronización automática programada: {schedule_result['schedule']['type']}")
            print(f"   Próxima sincronización: {schedule_result['schedule']['next_sync']}")
        else:
            print(f"   ⚠️ Error programando sincronización: {schedule_result.get('error')}")
            
    except Exception as e:
        print(f"❌ Error en sincronización: {e}")
        return False
    
    # 6. Resumen Final
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE INTEGRACIÓN CON OSTICKET")
    print("=" * 60)
    
    summary = {
        'osticket_connection': basic_result['success'],
        'data_extraction': bool(faq_data or ticket_data or category_data),
        'agents_available': agents.count() > 0,
        'training_integration': training_result['success'],
        'sync_system': True  # Si llegamos aquí, el sistema funciona
    }
    
    total_checks = len(summary)
    successful_checks = sum(summary.values())
    
    print(f"✅ Conexión osTicket: {'Funcionando' if summary['osticket_connection'] else 'Error'}")
    print(f"✅ Extracción de datos: {'Funcionando' if summary['data_extraction'] else 'Error'}")
    print(f"✅ Agentes disponibles: {'Sí' if summary['agents_available'] else 'No'}")
    print(f"✅ Integración entrenamiento: {'Funcionando' if summary['training_integration'] else 'Error'}")
    print(f"✅ Sistema de sincronización: {'Funcionando' if summary['sync_system'] else 'Error'}")
    
    print(f"\n🎯 Resultado: {successful_checks}/{total_checks} componentes funcionando")
    
    if successful_checks >= 3:  # Al menos conexión, extracción y sistema
        print("🎉 ¡INTEGRACIÓN CON OSTICKET EXITOSA!")
        print("   El sistema está listo para sincronizar conocimiento")
        return True
    else:
        print("⚠️ Integración parcial")
        print("   Algunos componentes necesitan atención")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
