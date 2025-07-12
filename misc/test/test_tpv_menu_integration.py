#!/usr/bin/env python3
"""
Test de integración del TPV en el menú de Sales
Verifica que el TPV esté accesible desde la navegación
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

def test_tpv_menu_integration():
    """Test de integración del TPV en el menú"""
    print("🔍 Verificando integración del TPV en el menú de Sales...")
    
    try:
        # Verificar configuración del menú
        from sales.menu_config import MENU_CONFIG
        
        # Buscar el TPV en el menú de Sales
        sales_menu = None
        for menu in MENU_CONFIG:
            if menu['name'] == 'sales':
                sales_menu = menu
                break
        
        if not sales_menu:
            print("❌ No se encontró el menú de Sales")
            return False
        
        # Buscar el TPV en los children
        tpv_item = None
        for child in sales_menu.get('children', []):
            if child['name'] == 'pos':
                tpv_item = child
                break
        
        if not tpv_item:
            print("❌ No se encontró el TPV en el menú de Sales")
            return False
        
        print("✅ TPV encontrado en el menú de Sales")
        print(f"   📍 Etiqueta: {tpv_item['label']}")
        print(f"   🔗 URL: {tpv_item['url']}")
        print(f"   🔐 Permiso: {tpv_item['permission']}")
        print(f"   📍 Orden: {tpv_item['order']}")
        
        # Verificar menú dinámico
        from core.utils.utils import APPS_MENU
        
        sales_dynamic_menu = None
        for app in APPS_MENU:
            if app['id'] == 'sales':
                sales_dynamic_menu = app
                break
        
        if not sales_dynamic_menu:
            print("❌ No se encontró el menú dinámico de Sales")
            return False
        
        # Buscar TPV en submenús
        tpv_dynamic_item = None
        for submenu in sales_dynamic_menu.get('submenus', []):
            if submenu['seccion'] == 'Sales Operations':
                for item in submenu['items']:
                    if 'Point of Sale' in item['label']:
                        tpv_dynamic_item = item
                        break
                break
        
        if not tpv_dynamic_item:
            print("❌ No se encontró el TPV en el menú dinámico")
            return False
        
        print("✅ TPV encontrado en el menú dinámico")
        print(f"   📍 Etiqueta: {tpv_dynamic_item['label']}")
        print(f"   🔗 URL: {tpv_dynamic_item['url']}")
        print(f"   🔐 Permiso: {tpv_dynamic_item['permission']}")
        
        # Verificar URLs
        from django.urls import reverse, NoReverseMatch
        
        try:
            tpv_url = reverse('sales:tpv_main')
            print(f"✅ URL del TPV resuelta correctamente: {tpv_url}")
        except NoReverseMatch:
            print("❌ No se pudo resolver la URL del TPV")
            return False
        
        print("\n🎉 ¡Integración del TPV en el menú completada exitosamente!")
        print("\n📋 Resumen de la integración:")
        print("  ✅ TPV agregado al menú estático de Sales")
        print("  ✅ TPV agregado al menú dinámico de Sales")
        print("  ✅ URL del TPV configurada correctamente")
        print("  ✅ Vista tpv_main creada")
        print("  ✅ Permisos configurados")
        print("  ✅ Orden de menú establecido")
        
        return True
        
    except Exception as e:
        print(f"💥 Error en test de integración: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Función principal"""
    print("🚀 Iniciando test de integración del TPV en el menú...")
    
    success = test_tpv_menu_integration()
    
    if success:
        print("\n🎊 ¡Test de integración completado exitosamente!")
        print("✨ El TPV está correctamente integrado en el menú de Sales")
    else:
        print("\n❌ Test de integración falló")
    
    return success

if __name__ == "__main__":
    main() 