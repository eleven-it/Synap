#!/usr/bin/env python3
"""
Script para configurar inicialmente los parámetros de sincronización basada en timestamps
"""

import os
import django
import sys

# Configuración de Django
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from administraNET_integration.models import SyncTimestampConfig
from django.utils.translation import gettext_lazy as _

def setup_timestamp_configs():
    """Configurar parámetros de sincronización basada en timestamps"""
    
    configs = [
        {
            'sync_type': 'PRODUCTS',
            'enable_timestamp_resolution': True,
            'sync_all_fields': True,
            'log_conflicts': True,
        },
        {
            'sync_type': 'CUSTOMERS',
            'enable_timestamp_resolution': True,
            'sync_all_fields': True,
            'log_conflicts': True,
        },
        {
            'sync_type': 'STOCK',
            'enable_timestamp_resolution': True,
            'sync_all_fields': True,
            'log_conflicts': True,
        },
        {
            'sync_type': 'ORDERS',
            'enable_timestamp_resolution': True,
            'sync_all_fields': True,
            'log_conflicts': True,
        },
    ]
    
    created_count = 0
    updated_count = 0
    
    for config_data in configs:
        config, created = SyncTimestampConfig.objects.get_or_create(
            sync_type=config_data['sync_type'],
            defaults=config_data
        )
        
        if created:
            print(f"✅ Configuración creada para {config_data['sync_type']}")
            created_count += 1
        else:
            # Actualizar configuración existente
            for key, value in config_data.items():
                setattr(config, key, value)
            config.save()
            print(f"🔄 Configuración actualizada para {config_data['sync_type']}")
            updated_count += 1
    
    print(f"\n📊 Resumen:")
    print(f"   ➕ Configuraciones creadas: {created_count}")
    print(f"   🔄 Configuraciones actualizadas: {updated_count}")
    print(f"   📋 Total configuraciones: {SyncTimestampConfig.objects.count()}")

def show_current_configs():
    """Mostrar configuraciones actuales"""
    print("\n🔍 Configuraciones actuales:")
    print("-" * 60)
    
    configs = SyncTimestampConfig.objects.all().order_by('sync_type')
    
    if not configs.exists():
        print("❌ No hay configuraciones definidas")
        return
    
    for config in configs:
        print(f"📋 {config.sync_type}:")
        print(f"   ✅ Timestamp resolution: {'Habilitado' if config.enable_timestamp_resolution else 'Deshabilitado'}")
        print(f"   🔄 Sync all fields: {'Sí' if config.sync_all_fields else 'No'}")
        print(f"   📝 Log conflicts: {'Sí' if config.log_conflicts else 'No'}")
        print(f"   📅 Última actualización: {config.updated_at.strftime('%Y-%m-%d %H:%M')}")
        print()

def main():
    """Función principal"""
    print("🚀 Configurando sincronización basada en timestamps...")
    print("=" * 60)
    
    # Configurar parámetros
    setup_timestamp_configs()
    
    # Mostrar configuraciones actuales
    show_current_configs()
    
    print("✅ Configuración completada exitosamente!")
    print("\n📝 Próximos pasos:")
    print("   1. Ejecutar migraciones de Django")
    print("   2. Ejecutar script SQL en administraNET")
    print("   3. Probar sincronización con --dry-run")
    print("   4. Ejecutar sincronización real")

if __name__ == "__main__":
    main() 