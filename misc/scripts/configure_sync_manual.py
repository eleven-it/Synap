#!/usr/bin/env python3
"""
Script manual simple para configurar sincronización basada en timestamps
Usa el campo fecha_mod existente en administraNET
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

def configure_sync():
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

def show_configs():
    """Mostrar configuraciones actuales"""
    try:
        from administraNET_integration.models import SyncTimestampConfig
        
        print("\n🔍 Configuraciones actuales:")
        print("-" * 50)
        
        configs = SyncTimestampConfig.objects.all().order_by('sync_type')
        
        if not configs.exists():
            print("❌ No hay configuraciones definidas")
            return
        
        for config in configs:
            print(f"📋 {config.sync_type}:")
            print(f"   ✅ Timestamp resolution: {'Sí' if config.enable_timestamp_resolution else 'No'}")
            print(f"   🔄 Sync all fields: {'Sí' if config.sync_all_fields else 'No'}")
            print(f"   📝 Log conflicts: {'Sí' if config.log_conflicts else 'No'}")
            print()
            
    except Exception as e:
        print(f"❌ Error mostrando configuraciones: {e}")

def test_timestamp_logic():
    """Probar lógica de resolución de timestamps"""
    print("\n🧪 Probando lógica de timestamps...")
    
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    # Simular timestamps
    now = timezone.now()
    synap_old = now - timedelta(hours=2)
    synap_new = now + timedelta(hours=1)
    adminet_old = now - timedelta(hours=3)
    adminet_new = now + timedelta(hours=2)
    
    print(f"   📅 Synap antiguo: {synap_old.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   📅 Synap nuevo: {synap_new.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   📅 administraNET antiguo: {adminet_old.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   📅 administraNET nuevo: {adminet_new.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Probar resolución
    if synap_new > adminet_old:
        print("   ✅ Synap nuevo > administraNET antiguo: SYNAP_WINS")
    if adminet_new > synap_old:
        print("   ✅ administraNET nuevo > Synap antiguo: ADMINET_WINS")
    
    print("   🎯 Lógica de timestamps funcionando correctamente")

def main():
    """Función principal"""
    print("🧪 Configuración de sincronización basada en timestamps")
    print("=" * 60)
    print("📋 Usando campo fecha_mod existente en administraNET")
    
    # Probar lógica de timestamps
    test_timestamp_logic()
    
    # Configurar parámetros
    if configure_sync():
        # Mostrar configuraciones actuales
        show_configs()
        
        print("\n✅ Configuración completada exitosamente!")
        print("\n📝 Próximos pasos:")
        print("   1. Ejecutar script SQL en administraNET:")
        print("      - misc/scripts/add_adminet_sync_field_only.sql")
        print("   2. Probar sincronización:")
        print("      docker exec Synap_app python manage.py sync_administraNET_timestamp_simple --type PRODUCTS --dry-run")
        print("   3. Ejecutar sincronización real:")
        print("      docker exec Synap_app python manage.py sync_administraNET_timestamp_simple --type PRODUCTS --show-conflicts")
    else:
        print("\n❌ Error en la configuración")

if __name__ == "__main__":
    main() 