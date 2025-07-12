#!/usr/bin/env python3
"""
Test simple de configuración de menús de ventas
Verifica la configuración sin depender de Firebase
"""

import os
import sys

def test_sales_menu_config():
    """Test de configuración del menú de sales"""
    print("🔍 Verificando configuración del menú de Sales...")
    
    try:
        # Verificar que el archivo existe
        menu_config_path = 'sales/menu_config.py'
        if not os.path.exists(menu_config_path):
            print(f"❌ No se encontró el archivo {menu_config_path}")
            return False
        
        print(f"✅ Archivo {menu_config_path} encontrado")
        
        # Leer el archivo y verificar contenido
        with open(menu_config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar elementos clave
        key_elements = [
            'MENU_CONFIG',
            'payment_configuration',
            'payment_methods',
            'payment_processors',
            'tpv_main',
            'dashboard'
        ]
        
        missing_elements = []
        for element in key_elements:
            if element not in content:
                missing_elements.append(element)
        
        if missing_elements:
            print(f"⚠️  Elementos faltantes: {missing_elements}")
            return False
        else:
            print("✅ Todos los elementos clave están presentes")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verificando menú estático: {e}")
        return False

def test_dynamic_menu_config():
    """Test de configuración del menú dinámico"""
    print("\n🔍 Verificando configuración del menú dinámico...")
    
    try:
        # Verificar que el archivo existe
        utils_path = 'core/utils/utils.py'
        if not os.path.exists(utils_path):
            print(f"❌ No se encontró el archivo {utils_path}")
            return False
        
        print(f"✅ Archivo {utils_path} encontrado")
        
        # Leer el archivo y verificar contenido
        with open(utils_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar elementos clave
        key_elements = [
            'APPS_MENU',
            'Payment Configuration',
            'Payment Methods',
            'Payment Processors',
            'Point of Sale (TPV)',
            'sales:payment_method_list',
            'sales:payment_processor_list'
        ]
        
        missing_elements = []
        for element in key_elements:
            if element not in content:
                missing_elements.append(element)
        
        if missing_elements:
            print(f"⚠️  Elementos faltantes: {missing_elements}")
            return False
        else:
            print("✅ Todos los elementos clave están presentes")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verificando menú dinámico: {e}")
        return False

def test_urls_exist():
    """Test de existencia de URLs"""
    print("\n🔍 Verificando existencia de URLs...")
    
    try:
        # Verificar que el archivo existe
        urls_path = 'sales/urls.py'
        if not os.path.exists(urls_path):
            print(f"❌ No se encontró el archivo {urls_path}")
            return False
        
        print(f"✅ Archivo {urls_path} encontrado")
        
        # Leer el archivo y verificar contenido
        with open(urls_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar URLs clave
        key_urls = [
            'payment_method_list',
            'payment_processor_list',
            'tpv_main',
            'dashboard',
            'client_list',
            'sales_order_list'
        ]
        
        missing_urls = []
        for url in key_urls:
            if url not in content:
                missing_urls.append(url)
        
        if missing_urls:
            print(f"⚠️  URLs faltantes: {missing_urls}")
            return False
        else:
            print("✅ Todas las URLs clave están definidas")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verificando URLs: {e}")
        return False

def test_templates_exist():
    """Test de existencia de templates"""
    print("\n🔍 Verificando existencia de templates...")
    
    try:
        # Verificar templates clave
        template_paths = [
            'sales/templates/sales/payment_methods/payment_method_list.html',
            'sales/templates/sales/payment_methods/payment_method_form.html',
            'sales/templates/sales/payment_methods/payment_method_detail.html',
            'sales/templates/sales/payment_processors/processor_list.html',
            'sales/templates/sales/payment_processors/processor_form.html',
            'sales/templates/sales/payment_processors/processor_confirm_delete.html',
        ]
        
        missing_templates = []
        for template_path in template_paths:
            if not os.path.exists(template_path):
                missing_templates.append(template_path)
            else:
                print(f"✅ {template_path}")
        
        if missing_templates:
            print(f"⚠️  Templates faltantes: {missing_templates}")
            return False
        else:
            print("✅ Todos los templates están presentes")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verificando templates: {e}")
        return False

def main():
    """Función principal de pruebas"""
    print("🚀 Iniciando pruebas simples de menús de ventas...\n")
    
    tests = [
        ("Configuración de menú estático", test_sales_menu_config),
        ("Configuración de menú dinámico", test_dynamic_menu_config),
        ("Existencia de URLs", test_urls_exist),
        ("Existencia de templates", test_templates_exist),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"🧪 Ejecutando: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Error en {test_name}: {e}")
            results.append((test_name, False))
        print()
    
    # Resumen final
    print("📊 RESUMEN DE PRUEBAS")
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
        print("🎉 ¡Todas las pruebas pasaron! Los menús están correctamente configurados.")
    else:
        print("⚠️  Algunas pruebas fallaron. Revisar la configuración de menús.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 