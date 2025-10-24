#!/usr/bin/env python3
"""
Script para investigar la estructura real de las tablas de osTicket
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
    print("🔍 INVESTIGACIÓN DE ESTRUCTURA DE TABLAS OSTICKET")
    print("=" * 70)
    
    try:
        integration = get_osticket_integration()
        
        print("🔄 Investigando estructura de tablas...")
        investigation = integration.investigate_table_structure()
        
        if 'error' in investigation:
            print(f"❌ Error en investigación: {investigation['error']}")
            return False
        
        # 1. Información de tabla ticket
        print("\n1️⃣ TABLA OST_TICKET")
        print("-" * 40)
        ticket_info = investigation['ticket_table']
        print(f"   Total de registros: {ticket_info.get('total_records', 'N/A')}")
        print(f"   Columnas disponibles:")
        for col in ticket_info.get('columns', []):
            print(f"     - {col}")
        
        # 2. Información de tabla thread
        print("\n2️⃣ TABLA OST_THREAD")
        print("-" * 40)
        thread_info = investigation['thread_table']
        print(f"   Total de registros: {thread_info.get('total_records', 'N/A')}")
        print(f"   Columnas disponibles:")
        for col in thread_info.get('columns', []):
            print(f"     - {col}")
        
        # 3. Tabla de mensajes (si existe)
        if investigation.get('message_table'):
            print(f"\n3️⃣ TABLA DE MENSAJES: {investigation['message_table']}")
            print("-" * 40)
            print(f"   Total de registros: {investigation.get('message_table_records', 'N/A')}")
            print(f"   Estructura:")
            for col in investigation.get('message_table_structure', []):
                print(f"     - {col}")
        
        # 4. Todas las tablas ost_
        print(f"\n4️⃣ TODAS LAS TABLAS OST_")
        print("-" * 40)
        all_tables = investigation.get('all_ost_tables', [])
        for table in all_tables:
            print(f"   - {table}")
        
        # 5. Relaciones de ejemplo
        if investigation.get('sample_relations'):
            print(f"\n5️⃣ RELACIONES DE EJEMPLO")
            print("-" * 40)
            for rel in investigation['sample_relations'][:3]:
                print(f"   Ticket {rel['ticket_id']} -> Thread {rel['thread_id']} (Tipo: {rel['object_type']})")
        
        # 6. Muestras del campo extra
        if investigation.get('extra_samples'):
            print(f"\n6️⃣ MUESTRAS DEL CAMPO EXTRA")
            print("-" * 40)
            for i, extra in enumerate(investigation['extra_samples'][:3]):
                print(f"   {i+1}. {extra[:100]}...")
        
        # 7. Recomendaciones
        print(f"\n7️⃣ RECOMENDACIONES")
        print("-" * 40)
        recommendations = investigation.get('recommendations', [])
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
        else:
            print("   No hay recomendaciones específicas")
        
        # 8. Análisis de la estructura
        print(f"\n8️⃣ ANÁLISIS DE LA ESTRUCTURA")
        print("-" * 40)
        
        # Verificar si podemos extraer tickets
        can_extract_tickets = False
        ticket_reason = ""
        
        if 'ost_ticket' in all_tables and 'ost_thread' in all_tables:
            if 'object_id' in thread_info.get('columns', []):
                if investigation.get('message_table'):
                    can_extract_tickets = True
                    ticket_reason = "Usando tabla de mensajes separada"
                elif 'extra' in thread_info.get('columns', []):
                    can_extract_tickets = True
                    ticket_reason = "Usando campo extra de thread"
                else:
                    ticket_reason = "No se encontró campo de contenido en thread"
            else:
                ticket_reason = "No se encontró campo object_id en thread"
        else:
            ticket_reason = "Faltan tablas ticket o thread"
        
        print(f"   ¿Se pueden extraer tickets? {'✅ Sí' if can_extract_tickets else '❌ No'}")
        print(f"   Razón: {ticket_reason}")
        
        # 9. Resumen final
        print(f"\n" + "=" * 70)
        print("📊 RESUMEN DE INVESTIGACIÓN")
        print("=" * 70)
        
        summary = {
            'ticket_table_exists': 'ost_ticket' in all_tables,
            'thread_table_exists': 'ost_thread' in all_tables,
            'message_table_exists': bool(investigation.get('message_table')),
            'can_extract_tickets': can_extract_tickets,
            'total_tables': len(all_tables)
        }
        
        print(f"✅ Tabla ticket: {'Sí' if summary['ticket_table_exists'] else 'No'}")
        print(f"✅ Tabla thread: {'Sí' if summary['thread_table_exists'] else 'No'}")
        print(f"✅ Tabla mensajes: {'Sí' if summary['message_table_exists'] else 'No'}")
        print(f"✅ Extracción tickets: {'Sí' if summary['can_extract_tickets'] else 'No'}")
        print(f"✅ Total tablas ost_: {summary['total_tables']}")
        
        if can_extract_tickets:
            print(f"\n🎉 ¡ESTRUCTURA COMPATIBLE!")
            print(f"   Se pueden extraer tickets usando: {ticket_reason}")
        else:
            print(f"\n⚠️ ESTRUCTURA INCOMPATIBLE")
            print(f"   No se pueden extraer tickets: {ticket_reason}")
        
        return can_extract_tickets
        
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
