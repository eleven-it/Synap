#!/usr/bin/env python
"""
Script para probar el wizard de Tiendanube y verificar que se guarden los datos
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from tiendanube_administranet.models import TiendanubeConfig
from core.models import UsuarioExtendido


def test_tiendanube_config_creation():
    """Probar la creación de una configuración de Tiendanube"""
    print("🧪 Probando creación de configuración de Tiendanube...")
    
    try:
        # Crear una configuración de prueba
        config = TiendanubeConfig.objects.create(
            name="Test Store",
            store_id="test_store_123",
            access_token="test_access_token_456",
            api_url="https://api.tiendanube.com/v1",
            is_active=True
        )
        
        print(f"✅ Configuración creada exitosamente:")
        print(f"   - ID: {config.id}")
        print(f"   - Name: {config.name}")
        print(f"   - Store ID: {config.store_id}")
        print(f"   - Access Token: {config.access_token}")
        print(f"   - API URL: {config.api_url}")
        print(f"   - Active: {config.is_active}")
        print(f"   - Created: {config.created_at}")
        
        # Verificar que se guardó en la base de datos
        saved_config = TiendanubeConfig.objects.get(id=config.id)
        print(f"✅ Configuración recuperada de la BD:")
        print(f"   - ID: {saved_config.id}")
        print(f"   - Name: {saved_config.name}")
        
        return config
        
    except Exception as e:
        print(f"❌ Error al crear configuración: {e}")
        return None


def test_wizard_simulation():
    """Simular el proceso del wizard"""
    print("\n🧪 Simulando proceso del wizard...")
    
    try:
        # Simular datos de sesión del wizard
        wizard_data = {
            'wizard_user_id': 'simulated_store_789',
            'wizard_access_token': 'simulated_token_abc',
            'wizard_auto_sync': True
        }
        
        # Crear configuración como lo haría el wizard
        config = TiendanubeConfig.objects.create(
            name=f"Store {wizard_data['wizard_user_id']}",
            store_id=wizard_data['wizard_user_id'],
            access_token=wizard_data['wizard_access_token'],
            api_url='https://api.tiendanube.com/v1',
            is_active=wizard_data['wizard_auto_sync'],
        )
        
        print(f"✅ Configuración del wizard creada exitosamente:")
        print(f"   - ID: {config.id}")
        print(f"   - Name: {config.name}")
        print(f"   - Store ID: {config.store_id}")
        print(f"   - Active: {config.is_active}")
        
        return config
        
    except Exception as e:
        print(f"❌ Error en simulación del wizard: {e}")
        return None


def list_all_configs():
    """Listar todas las configuraciones existentes"""
    print("\n📋 Listando todas las configuraciones de Tiendanube:")
    
    configs = TiendanubeConfig.objects.all()
    print(f"Total de configuraciones: {configs.count()}")
    
    for config in configs:
        print(f"   - ID: {config.id}, Name: {config.name}, Store ID: {config.store_id}, Active: {config.is_active}")


def cleanup_test_data():
    """Limpiar datos de prueba"""
    print("\n🧹 Limpiando datos de prueba...")
    
    # Eliminar configuraciones que contengan "test" o "simulated" en el nombre
    test_configs = TiendanubeConfig.objects.filter(
        name__icontains='test'
    ) | TiendanubeConfig.objects.filter(
        name__icontains='simulated'
    )
    
    count = test_configs.count()
    test_configs.delete()
    
    print(f"✅ {count} configuraciones de prueba eliminadas")


def main():
    """Función principal"""
    print("🚀 Iniciando pruebas del wizard de Tiendanube...")
    print("=" * 60)
    
    # Listar configuraciones existentes
    list_all_configs()
    
    # Probar creación básica
    config1 = test_tiendanube_config_creation()
    
    # Probar simulación del wizard
    config2 = test_wizard_simulation()
    
    # Listar configuraciones después de las pruebas
    list_all_configs()
    
    # Limpiar datos de prueba
    cleanup_test_data()
    
    # Listar configuraciones finales
    list_all_configs()
    
    print("\n" + "=" * 60)
    if config1 and config2:
        print("🎉 ¡Todas las pruebas pasaron exitosamente!")
        print("El wizard debería funcionar correctamente.")
    else:
        print("❌ Algunas pruebas fallaron.")
        print("Revisa los errores anteriores.")


if __name__ == '__main__':
    main() 