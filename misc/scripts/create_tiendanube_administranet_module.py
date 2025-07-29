#!/usr/bin/env python
"""
Script para crear el módulo tiendanube_administranet en un nuevo servidor
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from core.models import ModuleConfig
from core.module_registry import MODULE_CONFIGS


def create_tiendanube_administranet_module():
    """Crear el módulo tiendanube_administranet"""
    print("🚀 Creando módulo tiendanube_administranet...")
    
    # Verificar si ya existe
    if ModuleConfig.objects.filter(name='tiendanube_administranet').exists():
        print("✅ El módulo tiendanube_administranet ya existe")
        module = ModuleConfig.objects.get(name='tiendanube_administranet')
        print(f"   - Display Name: {module.display_name}")
        print(f"   - Active: {module.is_active}")
        return module
    
    # Obtener configuración del registro
    if 'tiendanube_administranet' not in MODULE_CONFIGS:
        print("❌ tiendanube_administranet no está en MODULE_CONFIGS")
        return None
    
    config = MODULE_CONFIGS['tiendanube_administranet']
    
    try:
        # Crear el módulo
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
        
        print("✅ Módulo tiendanube_administranet creado exitosamente")
        print(f"   - Display Name: {module.display_name}")
        print(f"   - Active: {module.is_active}")
        print(f"   - Dependencies: {module.dependencies}")
        print(f"   - Permissions: {len(module.permissions)}")
        print(f"   - Hooks: {len(module.hooks)}")
        
        return module
        
    except Exception as e:
        print(f"❌ Error al crear el módulo: {e}")
        return None


def verify_module_creation():
    """Verificar que el módulo se creó correctamente"""
    print("\n🔍 Verificando creación del módulo...")
    
    try:
        module = ModuleConfig.objects.get(name='tiendanube_administranet')
        print("✅ Módulo encontrado en la base de datos")
        print(f"   - ID: {module.id}")
        print(f"   - Name: {module.name}")
        print(f"   - Display Name: {module.display_name}")
        print(f"   - Active: {module.is_active}")
        print(f"   - Core: {module.is_core}")
        print(f"   - Required: {module.is_required}")
        print(f"   - Dependencies: {module.dependencies}")
        print(f"   - Permissions: {len(module.permissions)}")
        print(f"   - Hooks: {len(module.hooks)}")
        
        return True
        
    except ModuleConfig.DoesNotExist:
        print("❌ Módulo no encontrado en la base de datos")
        return False


def main():
    """Función principal"""
    print("=" * 60)
    print("🔧 CREACIÓN DEL MÓDULO TIENDANUBE_ADMINISTRANET")
    print("=" * 60)
    
    # Crear el módulo
    module = create_tiendanube_administranet_module()
    
    if module:
        # Verificar creación
        verify_module_creation()
        
        print("\n" + "=" * 60)
        print("🎉 ¡MÓDULO CREADO EXITOSAMENTE!")
        print("=" * 60)
        print("El módulo tiendanube_administranet ahora debería aparecer")
        print("en la interfaz de Module Management en /core/modules/")
        print("\nPróximos pasos:")
        print("1. Accede a /core/modules/ en tu navegador")
        print("2. Verifica que el módulo aparezca en la lista")
        print("3. Si es necesario, activa el módulo usando el switch")
    else:
        print("\n" + "=" * 60)
        print("❌ ERROR AL CREAR EL MÓDULO")
        print("=" * 60)
        print("Revisa los errores anteriores y vuelve a intentar")


if __name__ == '__main__':
    main() 