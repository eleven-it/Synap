#!/usr/bin/env python3
"""
Script simple para verificar URLs del menú sin depender de Firebase
"""

import os
import sys

def check_urls_in_menu_config():
    """Verificar URLs en la configuración del menú"""
    print("🔍 Verificando URLs en la configuración del menú...")
    
    try:
        # Leer el archivo de configuración del menú dinámico
        with open('core/utils/utils.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Buscar la sección de Payment Configuration
        if 'Payment Configuration' in content:
            print("✅ Sección 'Payment Configuration' encontrada")
        else:
            print("❌ Sección 'Payment Configuration' no encontrada")
            return False
        
        # Buscar URLs específicas
        urls_to_check = [
            'sales:payment_method_list',
            'sales:payment_processor_list',
            'sales:tpv_main',
            'sales:dashboard'
        ]
        
        found_urls = []
        missing_urls = []
        
        for url in urls_to_check:
            if url in content:
                found_urls.append(url)
                print(f"✅ {url} encontrada en configuración")
            else:
                missing_urls.append(url)
                print(f"❌ {url} no encontrada en configuración")
        
        print(f"\n📊 URLs en configuración:")
        print(f"   ✅ Encontradas: {len(found_urls)}")
        print(f"   ❌ Faltantes: {len(missing_urls)}")
        
        return len(missing_urls) == 0
        
    except Exception as e:
        print(f"❌ Error verificando configuración: {e}")
        return False

def check_urls_in_sales_urls():
    """Verificar URLs en sales/urls.py"""
    print("\n🔍 Verificando URLs en sales/urls.py...")
    
    try:
        with open('sales/urls.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # URLs que deberían estar definidas
        expected_urls = [
            'payment_method_list',
            'payment_processor_list',
            'tpv_main',
            'dashboard'
        ]
        
        found_urls = []
        missing_urls = []
        
        for url in expected_urls:
            if url in content:
                found_urls.append(url)
                print(f"✅ {url} encontrada en sales/urls.py")
            else:
                missing_urls.append(url)
                print(f"❌ {url} no encontrada en sales/urls.py")
        
        print(f"\n📊 URLs en sales/urls.py:")
        print(f"   ✅ Encontradas: {len(found_urls)}")
        print(f"   ❌ Faltantes: {len(missing_urls)}")
        
        return len(missing_urls) == 0
        
    except Exception as e:
        print(f"❌ Error verificando sales/urls.py: {e}")
        return False

def check_menu_structure():
    """Verificar estructura del menú"""
    print("\n🔍 Verificando estructura del menú...")
    
    try:
        with open('core/utils/utils.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Buscar la estructura del menú de sales
        sales_section_start = content.find('"id": "sales"')
        if sales_section_start == -1:
            print("❌ No se encontró la sección de sales en APPS_MENU")
            return False
        
        print("✅ Sección de sales encontrada en APPS_MENU")
        
        # Buscar submenús
        if '"submenus"' in content:
            print("✅ Submenús encontrados")
        else:
            print("❌ No se encontraron submenús")
            return False
        
        # Buscar Payment Configuration específicamente
        if '"Payment Configuration"' in content:
            print("✅ Payment Configuration encontrada en submenús")
        else:
            print("❌ Payment Configuration no encontrada en submenús")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error verificando estructura: {e}")
        return False

def main():
    """Función principal"""
    print("🚀 Verificando configuración de URLs del menú...\n")
    
    tests = [
        ("Estructura del menú", check_menu_structure),
        ("URLs en configuración", check_urls_in_menu_config),
        ("URLs en sales/urls.py", check_urls_in_sales_urls),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"🧪 {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Error en {test_name}: {e}")
            results.append((test_name, False))
        print()
    
    # Resumen
    print("📊 RESUMEN")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASÓ" if result else "❌ FALLÓ"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n📈 Resultado: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        print("🎉 La configuración parece estar correcta")
        print("💡 El problema podría estar en la resolución de URLs en tiempo de ejecución")
    else:
        print("⚠️  Hay problemas en la configuración que necesitan atención")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 