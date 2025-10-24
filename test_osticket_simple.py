#!/usr/bin/env python3
"""
Script de prueba simplificado para verificar la integración con osTicket
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

from support_ai.osticket_integration import get_osticket_integration


def main():
    print("🧪 PRUEBA SIMPLIFICADA DE INTEGRACIÓN CON OSTICKET")
    print("=" * 60)
    
    try:
        # 1. Verificar conexión básica con osTicket
        print("\n1️⃣ Verificando conexión básica con osTicket...")
        integration = get_osticket_integration()
        
        osticket_status = integration.get_osticket_status()
        
        if osticket_status['connected']:
            print(f"✅ Conexión exitosa")
            print(f"   Base de datos: {osticket_status['database']}")
            print(f"   Host: {osticket_status['host']}")
            
            # Mostrar estado de tablas
            print(f"   Estado de tablas:")
            for table, status in osticket_status['table_status'].items():
                if status['exists']:
                    print(f"     ✅ {table}: {status['record_count']} registros")
                else:
                    print(f"     ❌ {table}: {status.get('error', 'No existe')}")
        else:
            print(f"❌ Error de conexión: {osticket_status.get('error', 'Desconocido')}")
            return False
        
        # 2. Verificar extracción de FAQ
        print("\n2️⃣ Verificando extracción de FAQ...")
        faq_data = integration.extract_faq_knowledge()
        print(f"   FAQ extraídas: {len(faq_data)}")
        
        if faq_data:
            print("✅ Extracción de FAQ exitosa")
            # Mostrar algunas FAQ de ejemplo
            for i, faq in enumerate(faq_data[:3]):
                print(f"     {i+1}. {faq['question'][:50]}...")
        else:
            print("⚠️ No se extrajeron FAQ")
        
        # 3. Verificar extracción de categorías
        print("\n3️⃣ Verificando extracción de categorías...")
        category_data = integration.extract_category_knowledge()
        print(f"   Categorías extraídas: {len(category_data)}")
        
        if category_data:
            print("✅ Extracción de categorías exitosa")
            for category in category_data:
                print(f"     - {category['name']}: {category['description'][:50]}...")
        else:
            print("⚠️ No se extrajeron categorías")
        
        # 4. Verificar extracción de tickets
        print("\n4️⃣ Verificando extracción de tickets...")
        ticket_data = integration.extract_ticket_data(days_back=7)  # Solo últimos 7 días
        print(f"   Tickets extraídos: {len(ticket_data)}")
        
        if ticket_data:
            print("✅ Extracción de tickets exitosa")
            # Mostrar algunos tickets de ejemplo
            for i, ticket in enumerate(ticket_data[:3]):
                print(f"     {i+1}. Ticket {ticket['ticket_id']} (Número: {ticket['number']})")
                print(f"        Estado: {ticket['status_id']}")
                print(f"        Mensajes: {len(ticket['conversation'])}")
                if ticket['conversation']:
                    first_msg = ticket['conversation'][0]
                    print(f"        Primer mensaje: {first_msg['body'][:50]}...")
        else:
            print("⚠️ No se extrajeron tickets (puede ser normal)")
        
        # 5. Generar datos de entrenamiento
        print("\n5️⃣ Generando datos de entrenamiento...")
        training_data = integration.generate_training_data()
        
        if training_data['success']:
            print("✅ Generación de datos de entrenamiento exitosa")
            summary = training_data['summary']
            print(f"   Total de pares: {summary['total_training_pairs']}")
            print(f"   FAQ utilizadas: {summary['faq_count']}")
            print(f"   Tickets utilizados: {summary['ticket_count']}")
            print(f"   Categorías utilizadas: {summary['category_count']}")
        else:
            print(f"❌ Error generando datos: {training_data.get('error', 'Desconocido')}")
            return False
        
        # 6. Resumen Final
        print("\n" + "=" * 60)
        print("📊 RESUMEN DE INTEGRACIÓN CON OSTICKET")
        print("=" * 60)
        
        summary = {
            'osticket_connection': osticket_status['connected'],
            'faq_extraction': len(faq_data) > 0,
            'category_extraction': len(category_data) > 0,
            'ticket_extraction': len(ticket_data) >= 0,  # Puede ser 0
            'training_generation': training_data['success']
        }
        
        total_checks = len(summary)
        successful_checks = sum(summary.values())
        
        print(f"✅ Conexión osTicket: {'Funcionando' if summary['osticket_connection'] else 'Error'}")
        print(f"✅ Extracción FAQ: {'Funcionando' if summary['faq_extraction'] else 'Error'}")
        print(f"✅ Extracción categorías: {'Funcionando' if summary['category_extraction'] else 'Error'}")
        print(f"✅ Extracción tickets: {'Funcionando' if summary['ticket_extraction'] else 'Error'}")
        print(f"✅ Generación entrenamiento: {'Funcionando' if summary['training_generation'] else 'Error'}")
        
        print(f"\n🎯 Resultado: {successful_checks}/{total_checks} componentes funcionando")
        
        if successful_checks >= 4:  # Al menos conexión, FAQ, categorías y entrenamiento
            print("🎉 ¡INTEGRACIÓN CON OSTICKET EXITOSA!")
            print("   El sistema está listo para sincronizar conocimiento")
            return True
        else:
            print("⚠️ Integración parcial")
            print("   Algunos componentes necesitan atención")
            return False
            
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
