#!/usr/bin/env python3
"""
Script de debug para verificar la resolución de URLs del menú dinámico
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

def debug_menu_urls():
    """Debug de URLs del menú dinámico"""
    print("🔍 Debug de URLs del menú dinámico...")
    
    try:
        from core.utils.utils import APPS_MENU, obtener_submenus_por_app
        from core.models import UsuarioExtendido
        
        # Crear usuario de prueba o usar uno existente
        user, created = UsuarioExtendido.objects.get_or_create(
            username='debug_user',
            defaults={
                'email': 'debug@example.com',
                'first_name': 'Debug',
                'last_name': 'User',
                'is_active': True
            }
        )
        
        print(f"👤 Usuario de prueba: {user.username}")
        
        # Obtener permisos del usuario
        permisos_usuario = user.get_permisos_totales()
        print(f"🔐 Permisos del usuario: {list(permisos_usuario)[:5]}...")  # Mostrar solo los primeros 5
        
        # Verificar menú de sales específicamente
        sales_app = None
        for app in APPS_MENU:
            if app['id'] == 'sales':
                sales_app = app
                break
        
        if not sales_app:
            print("❌ No se encontró la app de sales en APPS_MENU")
            return
        
        print(f"✅ App de sales encontrada: {sales_app['nombre']}")
        
        # Verificar submenús de sales
        submenus = obtener_submenus_por_app('sales', permisos_usuario)
        print(f"📋 Número de submenús: {len(submenus)}")
        
        for i, submenu in enumerate(submenus):
            print(f"\n📍 Submenú {i+1}: {submenu['seccion']}")
            items = submenu.get('items', [])
            print(f"   📋 Número de items: {len(items)}")
            
            for j, item in enumerate(items):
                print(f"   🔗 Item {j+1}: {item['label']}")
                print(f"      URL: {item['url']}")
                print(f"      Icon: {item['icon']}")
                print(f"      Permission: {item['permission']}")
                
                # Verificar si la URL es válida
                if item['url'] == '#':
                    print(f"      ⚠️  URL no resuelta!")
                else:
                    print(f"      ✅ URL resuelta correctamente")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en debug: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_specific_urls():
    """Test de URLs específicas que podrían estar fallando"""
    print("\n🔍 Test de URLs específicas...")
    
    try:
        from django.urls import reverse, NoReverseMatch
        
        # URLs que deberían estar en el menú de sales
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
        
        failed_urls = []
        successful_urls = []
        
        for url_name in test_urls:
            try:
                url = reverse(url_name)
                successful_urls.append((url_name, url))
                print(f"✅ {url_name} -> {url}")
            except NoReverseMatch:
                failed_urls.append(url_name)
                print(f"❌ {url_name} -> No se pudo resolver")
            except Exception as e:
                failed_urls.append(url_name)
                print(f"❌ {url_name} -> Error: {e}")
        
        print(f"\n📊 Resumen:")
        print(f"   ✅ URLs exitosas: {len(successful_urls)}")
        print(f"   ❌ URLs fallidas: {len(failed_urls)}")
        
        if failed_urls:
            print(f"   📋 URLs fallidas: {failed_urls}")
        
        return len(failed_urls) == 0
        
    except Exception as e:
        print(f"❌ Error en test de URLs: {e}")
        return False

def main():
    """Función principal"""
    print("🚀 Iniciando debug de menú dinámico...\n")
    
    # Test 1: Debug del menú
    print("🧪 Test 1: Debug del menú dinámico")
    result1 = debug_menu_urls()
    
    # Test 2: URLs específicas
    print("\n🧪 Test 2: URLs específicas")
    result2 = test_specific_urls()
    
    # Resumen
    print("\n📊 RESUMEN")
    print("=" * 50)
    print(f"✅ Debug del menú: {'PASÓ' if result1 else 'FALLÓ'}")
    print(f"✅ URLs específicas: {'PASÓ' if result2 else 'FALLÓ'}")
    
    if result1 and result2:
        print("\n🎉 Todo está funcionando correctamente")
    else:
        print("\n⚠️  Hay problemas que necesitan atención")
    
    return result1 and result2

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 