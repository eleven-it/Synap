#!/usr/bin/env python
"""
Script para verificar y corregir problemas con el Module Management
Especialmente para el módulo tiendanube_administranet
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from core.models import ModuleConfig
from core.module_registry import MODULE_CONFIGS
from core.module_manager import ModuleManager
from core.hook_manager import HookManager
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission


def check_module_registry():
    """Verificar que el módulo esté en el registro"""
    print("🔍 Verificando registro de módulos...")
    
    if 'tiendanube_administranet' in MODULE_CONFIGS:
        print("✅ tiendanube_administranet está en MODULE_CONFIGS")
        config = MODULE_CONFIGS['tiendanube_administranet']
        print(f"   - Display Name: {config['display_name']}")
        print(f"   - Dependencies: {config['dependencies']}")
        print(f"   - Permissions: {len(config['permissions'])}")
        print(f"   - Hooks: {len(config['hooks'])}")
    else:
        print("❌ tiendanube_administranet NO está en MODULE_CONFIGS")
        return False
    
    return True


def check_module_database():
    """Verificar que el módulo esté en la base de datos"""
    print("\n🔍 Verificando base de datos...")
    
    try:
        module = ModuleConfig.objects.get(name='tiendanube_administranet')
        print("✅ tiendanube_administranet está en la base de datos")
        print(f"   - Display Name: {module.display_name}")
        print(f"   - Active: {module.is_active}")
        print(f"   - Core: {module.is_core}")
        print(f"   - Required: {module.is_required}")
        print(f"   - Dependencies: {module.dependencies}")
        print(f"   - Permissions: {len(module.permissions)}")
        print(f"   - Hooks: {len(module.hooks)}")
        return module
    except ModuleConfig.DoesNotExist:
        print("❌ tiendanube_administranet NO está en la base de datos")
        return None


def check_module_manager():
    """Verificar que el módulo esté en el ModuleManager"""
    print("\n🔍 Verificando ModuleManager...")
    
    mm = ModuleManager()
    
    # Verificar si está en todos los módulos
    all_modules = mm.get_all_modules()
    if 'tiendanube_administranet' in all_modules:
        print("✅ tiendanube_administranet está en ModuleManager.get_all_modules()")
    else:
        print("❌ tiendanube_administranet NO está en ModuleManager.get_all_modules()")
        return False
    
    # Verificar si está activo
    active_modules = mm.get_active_modules()
    if 'tiendanube_administranet' in active_modules:
        print("✅ tiendanube_administranet está en ModuleManager.get_active_modules()")
    else:
        print("❌ tiendanube_administranet NO está en ModuleManager.get_active_modules()")
        return False
    
    # Verificar si se puede activar/desactivar
    can_activate = mm.can_activate_module('tiendanube_administranet')
    can_deactivate = mm.can_deactivate_module('tiendanube_administranet')
    print(f"   - Can activate: {can_activate}")
    print(f"   - Can deactivate: {can_deactivate}")
    
    return True


def check_hooks():
    """Verificar que los hooks estén cargados"""
    print("\n🔍 Verificando hooks...")
    
    try:
        hm = HookManager()
        hooks = hm.get_module_hooks('tiendanube_administranet')
        if hooks:
            print(f"✅ Hooks cargados: {len(hooks)}")
            for hook_name in hooks.keys():
                print(f"   - {hook_name}")
        else:
            print("❌ No se encontraron hooks para tiendanube_administranet")
            return False
    except Exception as e:
        print(f"❌ Error al cargar hooks: {e}")
        return False
    
    return True


def check_permissions():
    """Verificar que los permisos estén creados"""
    print("\n🔍 Verificando permisos...")
    
    try:
        from tiendanube_administranet.models import TiendanubeConfig, AdministraNETConfig, CustomerMapping, ProductMapping, OrderMapping
        
        models = [TiendanubeConfig, AdministraNETConfig, CustomerMapping, ProductMapping, OrderMapping]
        total_permissions = 0
        
        for model in models:
            ct = ContentType.objects.get_for_model(model)
            permissions = Permission.objects.filter(content_type=ct)
            print(f"   - {model.__name__}: {permissions.count()} permisos")
            total_permissions += permissions.count()
        
        print(f"✅ Total de permisos: {total_permissions}")
        return total_permissions > 0
        
    except Exception as e:
        print(f"❌ Error al verificar permisos: {e}")
        return False


def fix_module_configuration():
    """Corregir la configuración del módulo si es necesario"""
    print("\n🔧 Corrigiendo configuración del módulo...")
    
    try:
        module = ModuleConfig.objects.get(name='tiendanube_administranet')
        config = MODULE_CONFIGS['tiendanube_administranet']
        
        # Actualizar configuración para que coincida con el registro
        module.display_name = config['display_name']
        module.description = config['description']
        module.version = config['version']
        module.author = config['author']
        module.is_required = config['is_required']
        module.is_core = config['is_core']
        module.dependencies = config['dependencies']
        module.optional_dependencies = config['optional_dependencies']
        module.settings = config['settings']
        module.permissions = config['permissions']
        module.hooks = config['hooks']
        module.is_active = True
        
        module.save()
        print("✅ Configuración del módulo actualizada")
        return True
        
    except Exception as e:
        print(f"❌ Error al actualizar configuración: {e}")
        return False


def create_missing_module():
    """Crear el módulo si no existe"""
    print("\n🔧 Creando módulo faltante...")
    
    try:
        config = MODULE_CONFIGS['tiendanube_administranet']
        
        module = ModuleConfig.objects.create(
            name=config['name'],
            display_name=config['display_name'],
            description=config['description'],
            version=config['version'],
            author=config['author'],
            is_required=config['is_required'],
            is_core=config['is_core'],
            dependencies=config['dependencies'],
            optional_dependencies=config['optional_dependencies'],
            settings=config['settings'],
            permissions=config['permissions'],
            hooks=config['hooks'],
            is_active=True
        )
        
        print("✅ Módulo tiendanube_administranet creado")
        return module
        
    except Exception as e:
        print(f"❌ Error al crear módulo: {e}")
        return None


def main():
    """Función principal"""
    print("🚀 Iniciando verificación del Module Management...")
    print("=" * 60)
    
    # Verificar registro
    registry_ok = check_module_registry()
    
    # Verificar base de datos
    module = check_module_database()
    
    # Si no existe en BD, crearlo
    if not module and registry_ok:
        module = create_missing_module()
    
    # Verificar ModuleManager
    manager_ok = check_module_manager()
    
    # Verificar hooks
    hooks_ok = check_hooks()
    
    # Verificar permisos
    permissions_ok = check_permissions()
    
    # Corregir configuración si es necesario
    if module and registry_ok:
        fix_module_configuration()
    
    print("\n" + "=" * 60)
    print("📊 RESUMEN:")
    print(f"   - Registro: {'✅' if registry_ok else '❌'}")
    print(f"   - Base de datos: {'✅' if module else '❌'}")
    print(f"   - ModuleManager: {'✅' if manager_ok else '❌'}")
    print(f"   - Hooks: {'✅' if hooks_ok else '❌'}")
    print(f"   - Permisos: {'✅' if permissions_ok else '❌'}")
    
    if all([registry_ok, module, manager_ok, hooks_ok, permissions_ok]):
        print("\n🎉 ¡El módulo tiendanube_administranet está completamente integrado!")
        print("   Ahora debería aparecer en la interfaz de Module Management.")
    else:
        print("\n⚠️  Hay problemas que necesitan ser corregidos.")
        print("   Revisa los errores anteriores.")


if __name__ == '__main__':
    main() 