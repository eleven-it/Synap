#!/usr/bin/env python3
"""
Test de integración de menús dinámicos de ventas
Verifica que todos los menús estén correctamente configurados y accesibles
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

def test_sales_menu_config():
    """Test de configuración del menú de sales"""
    print("🔍 Verificando configuración del menú de Sales...")
    
    try:
        # Verificar configuración del menú estático
        from sales.menu_config import MENU_CONFIG
        
        sales_menu = None
        for menu in MENU_CONFIG:
            if menu['name'] == 'sales':
                sales_menu = menu
                break
        
        if not sales_menu:
            print("❌ No se encontró el menú de Sales")
            return False
        
        print("✅ Menú de Sales encontrado")
        print(f"   📍 Etiqueta: {sales_menu['label']}")
        print(f"   🔐 Permiso: {sales_menu['permission']}")
        print(f"   📍 Orden: {sales_menu['order']}")
        
        # Verificar children
        children = sales_menu.get('children', [])
        print(f"   📋 Número de elementos: {len(children)}")
        
        # Verificar elementos específicos
        expected_items = [
            'dashboard', 'clients', 'create_client', 'pos', 'orders', 
            'create_order', 'invoices', 'payments', 'deliveries', 
            'returns', 'credit_notes', 'payment_configuration', 
            'reports', 'configuration'
        ]
        
        found_items = [item['name'] for item in children]
        missing_items = [item for item in expected_items if item not in found_items]
        
        if missing_items:
            print(f"⚠️  Elementos faltantes: {missing_items}")
        else:
            print("✅ Todos los elementos esperados están presentes")
        
        # Verificar configuración de pagos
        payment_config = None
        for child in children:
            if child['name'] == 'payment_configuration':
                payment_config = child
                break
        
        if payment_config:
            print("✅ Configuración de pagos encontrada")
            payment_children = payment_config.get('children', [])
            payment_items = [item['name'] for item in payment_children]
            print(f"   📋 Elementos de configuración: {payment_items}")
            
            if 'payment_methods' in payment_items and 'payment_processors' in payment_items:
                print("✅ Métodos de pago y procesadores configurados")
            else:
                print("❌ Faltan elementos de configuración de pagos")
        else:
            print("❌ No se encontró la configuración de pagos")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verificando menú estático: {e}")
        return False

def test_dynamic_menu_config():
    """Test de configuración del menú dinámico"""
    print("\n🔍 Verificando configuración del menú dinámico...")
    
    try:
        from core.utils.utils import APPS_MENU
        
        sales_dynamic_menu = None
        for app in APPS_MENU:
            if app['id'] == 'sales':
                sales_dynamic_menu = app
                break
        
        if not sales_dynamic_menu:
            print("❌ No se encontró el menú dinámico de Sales")
            return False
        
        print("✅ Menú dinámico de Sales encontrado")
        print(f"   📍 Nombre: {sales_dynamic_menu['nombre']}")
        print(f"   🔐 Permiso: {sales_dynamic_menu['permiso']}")
        print(f"   📍 Orden: {sales_dynamic_menu['orden']}")
        
        # Verificar submenús
        submenus = sales_dynamic_menu.get('submenus', [])
        print(f"   📋 Número de secciones: {len(submenus)}")
        
        # Verificar secciones específicas
        expected_sections = [
            'Main', 'Customer Management', 'Sales Operations', 
            'Invoices & Payments', 'Logistics', 'Payment Configuration', 
            'Reports & Configuration'
        ]
        
        found_sections = [section['seccion'] for section in submenus]
        missing_sections = [section for section in expected_sections if section not in found_sections]
        
        if missing_sections:
            print(f"⚠️  Secciones faltantes: {missing_sections}")
        else:
            print("✅ Todas las secciones esperadas están presentes")
        
        # Verificar sección de configuración de pagos
        payment_section = None
        for section in submenus:
            if section['seccion'] == 'Payment Configuration':
                payment_section = section
                break
        
        if payment_section:
            print("✅ Sección de configuración de pagos encontrada")
            payment_items = [item['label'] for item in payment_section['items']]
            print(f"   📋 Elementos: {payment_items}")
            
            if 'Payment Methods' in payment_items and 'Payment Processors' in payment_items:
                print("✅ Métodos de pago y procesadores en menú dinámico")
            else:
                print("❌ Faltan elementos de configuración de pagos en menú dinámico")
        else:
            print("❌ No se encontró la sección de configuración de pagos")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verificando menú dinámico: {e}")
        return False

def test_url_resolution():
    """Test de resolución de URLs"""
    print("\n🔍 Verificando resolución de URLs...")
    
    try:
        from django.urls import reverse, NoReverseMatch
        
        # URLs a verificar
        urls_to_test = [
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
        
        resolved_urls = []
        failed_urls = []
        
        for url_name in urls_to_test:
            try:
                url = reverse(url_name)
                resolved_urls.append((url_name, url))
                print(f"✅ {url_name} -> {url}")
            except NoReverseMatch:
                failed_urls.append(url_name)
                print(f"❌ {url_name} -> No se pudo resolver")
            except Exception as e:
                failed_urls.append(url_name)
                print(f"❌ {url_name} -> Error: {e}")
        
        print(f"\n📊 Resumen de URLs:")
        print(f"   ✅ Resueltas: {len(resolved_urls)}")
        print(f"   ❌ Fallidas: {len(failed_urls)}")
        
        if failed_urls:
            print(f"   📋 URLs fallidas: {failed_urls}")
            return False
        else:
            print("✅ Todas las URLs se resolvieron correctamente")
            return True
            
    except Exception as e:
        print(f"❌ Error verificando URLs: {e}")
        return False

def test_menu_permissions():
    """Test de permisos del menú"""
    print("\n🔍 Verificando permisos del menú...")
    
    try:
        from core.models import UsuarioExtendido
        from core.utils.utils import apps_visibles_para_usuario
        
        # Crear usuario de prueba
        user, created = UsuarioExtendido.objects.get_or_create(
            username='test_menu_user',
            defaults={
                'email': 'test_menu@example.com',
                'first_name': 'Test',
                'last_name': 'Menu User',
                'is_active': True
            }
        )
        
        if created:
            print("👤 Usuario de prueba creado")
        else:
            print("👤 Usuario de prueba existente")
        
        # Verificar menús visibles
        visible_apps = apps_visibles_para_usuario(user)
        
        sales_app = None
        for app in visible_apps:
            if app['id'] == 'sales':
                sales_app = app
                break
        
        if sales_app:
            print("✅ App de Sales visible para el usuario")
            submenus = sales_app.get('submenus', [])
            print(f"   📋 Número de secciones visibles: {len(submenus)}")
            
            for section in submenus:
                items = section.get('items', [])
                print(f"   📍 {section['seccion']}: {len(items)} elementos")
        else:
            print("❌ App de Sales no visible para el usuario")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error verificando permisos: {e}")
        return False

def main():
    """Función principal de pruebas"""
    print("🚀 Iniciando pruebas de integración de menús de ventas...\n")
    
    tests = [
        ("Configuración de menú estático", test_sales_menu_config),
        ("Configuración de menú dinámico", test_dynamic_menu_config),
        ("Resolución de URLs", test_url_resolution),
        ("Permisos del menú", test_menu_permissions),
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