#!/usr/bin/env python3
"""
Test final para verificar que Settings aparezca en el navbar
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from core.models import UsuarioExtendido
from core.utils.utils import apps_visibles_para_usuario

def test_settings_final():
    """Test final para verificar Settings en el navbar"""
    print("🧪 TEST FINAL - Settings en el navbar")
    print("=" * 50)
    
    # Buscar superusuario
    superuser = UsuarioExtendido.objects.filter(is_superuser=True).first()
    if not superuser:
        print("❌ No se encontró un usuario superusuario")
        return False
    
    print(f"✅ Superusuario: {superuser.email}")
    
    # Obtener apps visibles
    apps = apps_visibles_para_usuario(superuser)
    
    # Buscar Settings
    settings_app = None
    for app in apps:
        if app['id'] == 'settings':
            settings_app = app
            break
    
    print(f"\n📊 Apps visibles ({len(apps)}):")
    for app in apps:
        print(f"  - {app['id']}: {app['nombre']}")
    
    print(f"\n🔧 Settings encontrado: {settings_app is not None}")
    
    if settings_app:
        print(f"  ✅ Nombre: {settings_app['nombre']}")
        print(f"  ✅ URL: {settings_app['url']}")
        print(f"  ✅ Submenús: {len(settings_app.get('submenus', []))}")
        
        for submenu in settings_app.get('submenus', []):
            print(f"    * {submenu['seccion']}: {len(submenu['items'])} items")
            for item in submenu['items']:
                status = "✅" if item['url'] != "#" else "❌"
                print(f"      {status} {item['label']} -> {item['url']}")
        
        print("\n🎉 ¡Settings está correctamente configurado en el navbar!")
        return True
    else:
        print("\n❌ Settings no se encontró en el navbar")
        return False

if __name__ == "__main__":
    try:
        success = test_settings_final()
        if success:
            print("\n✅ Test completado exitosamente!")
            sys.exit(0)
        else:
            print("\n❌ Test falló!")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error en el test: {e}")
        sys.exit(1) 