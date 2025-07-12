#!/usr/bin/env python3
"""
Script para probar que las URLs del módulo reports funcionen correctamente
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from django.urls import reverse, NoReverseMatch
from core.models import UsuarioExtendido
from core.utils.utils import apps_visibles_para_usuario

def test_reports_urls():
    """Prueba que las URLs del módulo reports funcionen correctamente"""
    print("🧪 Probando URLs del módulo reports...")
    
    # URLs a probar
    urls_to_test = [
        'reports:dashboard',
        'reports:report_list',
        'reports:report_create',
        'reports:template_list',
        'reports:template_create',
        'reports:component_library',
        'reports:schedule_list',
        'reports:schedule_create',
    ]
    
    results = {}
    
    for url_name in urls_to_test:
        try:
            url = reverse(url_name)
            results[url_name] = {'status': '✅ OK', 'url': url}
            print(f"  {url_name}: {url}")
        except NoReverseMatch as e:
            results[url_name] = {'status': '❌ ERROR', 'error': str(e)}
            print(f"  {url_name}: ❌ ERROR - {e}")
        except Exception as e:
            results[url_name] = {'status': '❌ ERROR', 'error': str(e)}
            print(f"  {url_name}: ❌ ERROR - {e}")
    
    return results

def test_navbar_reports():
    """Prueba que el módulo reports aparezca correctamente en el navbar"""
    print("\n🧪 Probando navbar del módulo reports...")
    
    try:
        # Buscar un usuario administrador
        admin_user = UsuarioExtendido.objects.filter(is_superuser=True).first()
        if not admin_user:
            print("❌ No se encontró un usuario administrador")
            return False
        
        print(f"✅ Usuario administrador encontrado: {admin_user.email}")
        
        # Obtener apps visibles para el usuario
        apps_visibles = apps_visibles_para_usuario(admin_user)
        
        # Buscar el módulo reports
        reports_app = None
        for app in apps_visibles:
            if app['id'] == 'reports':
                reports_app = app
                break
        
        if not reports_app:
            print("❌ Módulo reports no encontrado en el navbar")
            return False
        
        print(f"✅ Módulo reports encontrado en el navbar!")
        print(f"   Nombre: {reports_app['nombre']}")
        print(f"   URL principal: {reports_app['url']}")
        
        # Verificar submenús
        if reports_app.get('submenus'):
            print(f"   Submenús: {len(reports_app['submenus'])}")
            for submenu in reports_app['submenus']:
                print(f"     - {submenu['seccion']}: {len(submenu['items'])} items")
                for item in submenu['items']:
                    status = "✅" if item['url'] != "#" else "❌"
                    print(f"       {status} {item['label']} -> {item['url']}")
        else:
            print("   ⚠️ No hay submenús configurados")
        
        return True
        
    except Exception as e:
        print(f"❌ Error probando navbar: {e}")
        return False

def main():
    """Función principal"""
    print("🚀 Iniciando pruebas de URLs del módulo reports...")
    
    # Prueba 1: Verificar URLs individuales
    url_results = test_reports_urls()
    
    # Prueba 2: Verificar navbar
    navbar_ok = test_navbar_reports()
    
    # Resumen
    print("\n📊 Resumen de pruebas:")
    
    # Contar resultados de URLs
    ok_count = sum(1 for result in url_results.values() if result['status'] == '✅ OK')
    error_count = len(url_results) - ok_count
    
    print(f"   URLs: {ok_count}/{len(url_results)} OK")
    print(f"   Navbar: {'✅ OK' if navbar_ok else '❌ FALLO'}")
    
    if error_count > 0:
        print("\n❌ URLs con errores:")
        for url_name, result in url_results.items():
            if result['status'] == '❌ ERROR':
                print(f"   - {url_name}: {result['error']}")
    
    if ok_count == len(url_results) and navbar_ok:
        print("\n🎉 ¡Todas las pruebas pasaron! El módulo reports está completamente funcional.")
        return 0
    else:
        print("\n💥 Algunas pruebas fallaron. Revisar configuración.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code) 