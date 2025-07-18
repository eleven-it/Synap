#!/usr/bin/env python3
"""
Script de prueba para verificar la lógica del navbar y visualización de apps
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from core.models import ModuleConfig, UsuarioExtendido
from core.utils.utils import apps_visibles_para_usuario

def test_navbar_logic():
    """Prueba la lógica del navbar y visualización de apps"""
    print("🧪 Probando lógica del navbar...")
    
    # Obtener todos los módulos
    modules = ModuleConfig.objects.all()
    print(f"📊 Total de módulos en BD: {modules.count()}")
    
    # Mostrar estado de módulos
    print("\n📋 Estado de módulos:")
    for module in modules:
        status = "✅ ACTIVO" if module.is_active else "❌ INACTIVO"
        core_status = "🔒 CORE" if module.is_core else "📦 NORMAL"
        print(f"  {status} {core_status} - {module.name}")
    
    # Crear usuario superusuario de prueba
    superuser, created = UsuarioExtendido.objects.get_or_create(
        username='test_superuser',
        defaults={
            'email': 'superuser@test.com',
            'is_staff': True,
            'is_superuser': True,
            'is_active': True
        }
    )
    
    if created:
        print(f"\n👑 Superusuario creado: {superuser.email}")
    else:
        print(f"\n👑 Superusuario existente: {superuser.email}")
    
    # Crear usuario normal de prueba
    normal_user, created = UsuarioExtendido.objects.get_or_create(
        username='test_normal_user',
        defaults={
            'email': 'normal@test.com',
            'is_staff': False,
            'is_superuser': False,
            'is_active': True
        }
    )
    
    if created:
        print(f"👤 Usuario normal creado: {normal_user.email}")
    else:
        print(f"👤 Usuario normal existente: {normal_user.email}")
    
    # Probar apps visibles para superusuario
    print(f"\n🔍 Apps visibles para SUPERUSUARIO:")
    superuser_apps = apps_visibles_para_usuario(superuser)
    print(f"  Total apps: {len(superuser_apps)}")
    
    for app in superuser_apps:
        module_status = "✅" if app.get('id') in ['core', 'login', 'dashboard', 'module_management'] else "❓"
        print(f"  {module_status} {app['id']}: {app['nombre']} -> {app['url']}")
    
    # Probar apps visibles para usuario normal
    print(f"\n🔍 Apps visibles para USUARIO NORMAL:")
    normal_user_apps = apps_visibles_para_usuario(normal_user)
    print(f"  Total apps: {len(normal_user_apps)}")
    
    for app in normal_user_apps:
        module_status = "✅" if app.get('id') in ['core', 'login', 'dashboard'] else "❓"
        print(f"  {module_status} {app['id']}: {app['nombre']} -> {app['url']}")
    
    # Verificar reglas específicas
    print(f"\n✅ Verificando reglas específicas:")
    
    # Regla 1: Module Management solo para superusuarios
    module_mgmt_super = any(app['id'] == 'module_management' for app in superuser_apps)
    module_mgmt_normal = any(app['id'] == 'module_management' for app in normal_user_apps)
    
    print(f"  📋 Module Management para superusuario: {'✅' if module_mgmt_super else '❌'}")
    print(f"  📋 Module Management para usuario normal: {'❌' if not module_mgmt_normal else '❌ ERROR'}")
    
    # Regla 2: Apps core siempre visibles
    core_apps = ['core', 'login', 'dashboard']
    for app_id in core_apps:
        super_visible = any(app['id'] == app_id for app in superuser_apps)
        normal_visible = any(app['id'] == app_id for app in normal_user_apps)
        print(f"  🔒 {app_id} - Super: {'✅' if super_visible else '❌'}, Normal: {'✅' if normal_visible else '❌'}")
    
    # Regla 3: Apps inactivas no visibles
    inactive_modules = [m.name for m in modules if not m.is_active and not m.is_core]
    for module_name in inactive_modules:
        super_visible = any(app['id'] == module_name for app in superuser_apps)
        normal_visible = any(app['id'] == module_name for app in normal_user_apps)
        if super_visible or normal_visible:
            print(f"  ⚠️ {module_name} está visible pero debería estar oculto (inactivo)")
    
    print(f"\n✅ Prueba de lógica del navbar completada!")
    
    # Resumen
    print(f"\n📊 RESUMEN:")
    print(f"  - Superusuario ve {len(superuser_apps)} apps")
    print(f"  - Usuario normal ve {len(normal_user_apps)} apps")
    print(f"  - Módulos activos: {modules.filter(is_active=True).count()}")
    print(f"  - Módulos inactivos: {modules.filter(is_active=False).count()}")

if __name__ == '__main__':
    test_navbar_logic() 