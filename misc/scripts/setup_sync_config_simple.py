#!/usr/bin/env python3
"""
Script simple para configurar sincronización basada en timestamps
"""

import os
import sys
import django

# Configuración de Django
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')

try:
    django.setup()
    print("✅ Django configurado correctamente")
except Exception as e:
    print(f"❌ Error configurando Django: {e}")
    sys.exit(1)

def setup_sync_config():
    """Configurar parámetros de sincronización"""
    
    try:
        from administraNET_integration.models import SyncTimestampConfig
        
        print("🚀 Configurando sincronización basada en timestamps...")
        print("📋 Usando campo fecha_mod existente en administraNET")
        
        # Configuraciones a crear
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
        
        return True
        
    except ImportError as e:
        print(f"❌ Error importando modelos: {e}")
        print("💡 Asegúrate de que las migraciones estén aplicadas")
        return False
    except Exception as e:
        print(f"❌ Error configurando: {e}")
        return False

def main():
    """Función principal"""
    print("🧪 Configuración de sincronización basada en timestamps")
    print("=" * 60)
    
    # Configurar parámetros
    if setup_sync_config():
        print("\n✅ Configuración completada exitosamente!")
        print("\n📝 Próximos pasos:")
        print("   1. Ejecutar script SQL en administraNET:")
        print("      - misc/scripts/add_sync_field_safe.sql")
        print("   2. Probar sincronización:")
        print("      docker exec Synap_app python manage.py sync_administraNET_timestamp_simple --type PRODUCTS --dry-run")
    else:
        print("\n❌ Error en la configuración")

if __name__ == "__main__":
    main() 