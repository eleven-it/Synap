#!/usr/bin/env python3
"""
Test simple para verificar que Settings aparezca en el navbar para superusuarios
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from core.models import UsuarioExtendido
from core.utils.utils import apps_visibles_para_usuario

def test_settings_navbar():
    """Prueba que Settings aparezca en el navbar para superusuarios"""
    print("🧪 Probando que Settings aparezca en el navbar...")
    
    # Buscar un usuario superusuario
    superuser = UsuarioExtendido.objects.filter(is_superuser=True).first()
    if not superuser:
        print("❌ No se encontró un usuario superusuario")
        return False
    
    print(f"✅ Usuario superusuario encontrado: {superuser.email}")
    
    # Obtener apps visibles para el superusuario
    apps_visibles = apps_visibles_para_usuario(superuser)
    
    # Buscar la app Settings
    settings_app = None
    for app in apps_visibles:
        if app['id'] == 'settings':
            settings_app = app
            break
    
    if not settings_app:
        print("❌ Settings no encontrado en el navbar")
        print(f"   Apps visibles: {[app['id'] for app in apps_visibles]}")
        return False
    
    print(f"✅ Settings encontrado en el navbar!")
    print(f"   Nombre: {settings_app['nombre']}")
    print(f"   URL principal: {settings_app['url']}")
    
    # Verificar submenús
    if settings_app.get('submenus'):
        print(f"   Submenús: {len(settings_app['submenus'])}")
        for submenu in settings_app['submenus']:
            print(f"     - {submenu['seccion']}: {len(submenu['items'])} items")
            for item in submenu['items']:
                status = "✅" if item['url'] != "#" else "❌"
                print(f"       {status} {item['label']} -> {item['url']}")
    else:
        print("   ⚠️ No hay submenús configurados")
    
    return True

if __name__ == "__main__":
    try:
        success = test_settings_navbar()
        if success:
            print("\n🎉 Test completado exitosamente!")
        else:
            print("\n❌ Test falló!")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error en el test: {e}")
        sys.exit(1) 