#!/usr/bin/env python3
"""
Script para probar la resolución de URLs específicas del menú de sales
"""

import os
import sys

def test_url_resolution():
    """Probar resolución de URLs específicas"""
    print("🔍 Probando resolución de URLs específicas...")
    
    # URLs que están en el menú de sales
    test_urls = [
        'sales:dashboard',
        'sales:client_list', 
        'sales:client_create',
        'sales:tpv_main',
        'sales:sales_order_list',
        'sales:sales_order_create',
        'sales:invoice_list',
        'sales:payment_list',
        'sales:delivery_list',
        'sales:return_delivery_list',
        'sales:credit_note_list',
        'sales:payment_method_list',
        'sales:payment_processor_list',
        'sales:reports_dashboard',
        'sales:price_list_list',
        'sales:payment_term_list',
    ]
    
    print("📋 URLs a probar:")
    for url in test_urls:
        print(f"   - {url}")
    
    print("\n💡 Para probar estas URLs, ejecuta el servidor Django y visita:")
    print("   http://localhost:8002/core/dashboard/")
    print("\n🔧 Luego revisa los logs del servidor para ver los mensajes de debug:")
    print("   - 'Successfully resolved URL...'")
    print("   - 'Warning: Could not resolve URL...'")
    print("   - 'Error processing item...'")
    
    print("\n🎯 URLs más probables de estar fallando:")
    print("   - sales:payment_method_list")
    print("   - sales:payment_processor_list") 
    print("   - sales:tpv_main")
    print("   - sales:client_create")
    
    return True

def check_url_patterns():
    """Verificar patrones de URL en sales/urls.py"""
    print("\n🔍 Verificando patrones de URL en sales/urls.py...")
    
    try:
        with open('sales/urls.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Buscar patrones de URL específicos
        patterns_to_find = [
            'payment_method_list',
            'payment_processor_list',
            'tpv_main',
            'dashboard',
            'client_list',
            'sales_order_list'
        ]
        
        found_patterns = []
        missing_patterns = []
        
        for pattern in patterns_to_find:
            if pattern in content:
                found_patterns.append(pattern)
                print(f"✅ {pattern} encontrado en sales/urls.py")
            else:
                missing_patterns.append(pattern)
                print(f"❌ {pattern} NO encontrado en sales/urls.py")
        
        print(f"\n📊 Patrones encontrados: {len(found_patterns)}/{len(patterns_to_find)}")
        
        if missing_patterns:
            print(f"⚠️  Patrones faltantes: {missing_patterns}")
            return False
        else:
            print("✅ Todos los patrones están definidos")
            return True
            
    except Exception as e:
        print(f"❌ Error verificando patrones: {e}")
        return False

def main():
    """Función principal"""
    print("🚀 Análisis de resolución de URLs del menú de sales...\n")
    
    test_url_resolution()
    check_url_patterns()
    
    print("\n📋 PRÓXIMOS PASOS:")
    print("1. Ejecuta el servidor Django: python manage.py runserver 8002")
    print("2. Visita http://localhost:8002/core/dashboard/")
    print("3. Abre el dropdown de 'Sales' en el navbar")
    print("4. Revisa los logs del servidor para ver los mensajes de debug")
    print("5. Identifica qué URLs específicas están fallando")
    
    print("\n🔧 SOLUCIÓN TEMPORAL:")
    print("Si quieres que todos los enlaces funcionen inmediatamente, podemos:")
    print("1. Modificar la función obtener_submenus_por_app para usar URLs hardcodeadas")
    print("2. O corregir las URLs específicas que están fallando")
    
    return True

if __name__ == "__main__":
    main() 