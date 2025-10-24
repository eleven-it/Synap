#!/usr/bin/env python3
"""
Script para investigar específicamente el campo extra de osTicket
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
    print("🔍 INVESTIGACIÓN DEL CAMPO EXTRA DE OSTICKET")
    print("=" * 60)
    
    try:
        integration = get_osticket_integration()
        
        print("🔄 Investigando campo extra...")
        investigation = integration.investigate_extra_field()
        
        if 'error' in investigation:
            print(f"❌ Error en investigación: {investigation['error']}")
            return False
        
        # 1. Estadísticas generales
        print("\n1️⃣ ESTADÍSTICAS GENERALES")
        print("-" * 40)
        print(f"   Total de tickets: {investigation.get('total_tickets', 'N/A')}")
        print(f"   Tickets con campo extra: {investigation.get('tickets_with_extra', 'N/A')}")
        print(f"   Cobertura del campo extra: {investigation.get('extra_coverage', 'N/A'):.1f}%")
        
        # 2. Análisis del campo extra
        if investigation.get('extra_analysis'):
            print(f"\n2️⃣ ANÁLISIS DEL CAMPO EXTRA")
            print("-" * 40)
            analysis = investigation['extra_analysis']
            print(f"   Longitud mínima: {analysis.get('min_length', 'N/A')}")
            print(f"   Longitud máxima: {analysis.get('max_length', 'N/A')}")
            print(f"   Longitud promedio: {analysis.get('avg_length', 'N/A'):.1f}")
            print(f"   Contiene HTML: {'Sí' if analysis.get('contains_html') else 'No'}")
            print(f"   Porcentaje HTML: {analysis.get('html_percentage', 0):.1f}%")
            print(f"   Contiene texto: {'Sí' if analysis.get('contains_text') else 'No'}")
            print(f"   Porcentaje texto: {analysis.get('text_percentage', 0):.1f}%")
        
        # 3. Muestras del campo extra
        if investigation.get('extra_samples'):
            print(f"\n3️⃣ MUESTRAS DEL CAMPO EXTRA")
            print("-" * 40)
            samples = investigation['extra_samples']
            for i, sample in enumerate(samples[:5], 1):
                print(f"   {i}. Thread {sample['id']} -> Ticket {sample['object_id']}")
                print(f"      Longitud: {sample['extra_length']}")
                print(f"      Fecha: {sample['created']}")
                print(f"      Contenido: {sample['extra'][:100]}...")
                print()
        
        # 4. Tablas de entrada
        if investigation.get('entry_tables'):
            print(f"\n4️⃣ TABLAS DE ENTRADA DISPONIBLES")
            print("-" * 40)
            for table in investigation['entry_tables']:
                print(f"   - {table}")
        
        # 5. Estructura de ost_thread_entry
        if investigation.get('thread_entry_structure'):
            print(f"\n5️⃣ ESTRUCTURA DE OST_THREAD_ENTRY")
            print("-" * 40)
            for col in investigation['thread_entry_structure']:
                print(f"   - {col}")
        
        # 6. Muestras de ost_thread_entry
        if investigation.get('entry_samples'):
            print(f"\n6️⃣ MUESTRAS DE OST_THREAD_ENTRY")
            print("-" * 40)
            samples = investigation['entry_samples']
            for i, sample in enumerate(samples[:3], 1):
                print(f"   {i}. Entry {sample['id']} -> Thread {sample['thread_id']}")
                if sample.get('body'):
                    print(f"      Body: {sample['body'][:100]}...")
                if sample.get('message'):
                    print(f"      Message: {sample['message'][:100]}...")
                if sample.get('content'):
                    print(f"      Content: {sample['content'][:100]}...")
                print(f"      Fecha: {sample['created']}")
                print()
        
        # 7. Recomendaciones
        if investigation.get('recommendations'):
            print(f"\n7️⃣ RECOMENDACIONES")
            print("-" * 40)
            for i, rec in enumerate(investigation['recommendations'], 1):
                print(f"   {i}. {rec}")
        
        # 8. Análisis final
        print(f"\n8️⃣ ANÁLISIS FINAL")
        print("-" * 40)
        
        if investigation.get('entry_samples'):
            print("✅ Se encontró contenido en ost_thread_entry")
            print("   Recomendación: Usar ost_thread_entry para extraer mensajes")
        elif investigation.get('tickets_with_extra', 0) > 0:
            print("✅ Se encontró contenido en el campo extra")
            print("   Recomendación: Usar el campo extra de ost_thread")
        else:
            print("❌ No se encontró contenido de mensajes")
            print("   Posible causa: Estructura diferente o datos vacíos")
        
        return True
        
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
