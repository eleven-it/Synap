#!/usr/bin/env python3
"""
Script para configurar las configuraciones reales en la nueva app tiendanube_administranet.
Migra configuraciones existentes y crea nuevas para testing.
"""
import os
import sys
from pathlib import Path

# Agregar el directorio del proyecto al path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

# En el contenedor Docker, el proyecto está en /app
if os.path.exists('/app'):
    sys.path.append('/app')

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
import django
django.setup()

from tiendanube_administranet.models import TiendanubeConfig, AdministraNETConfig
from tiendanube.models import TiendaNubeConfig, TiendaNubeAdminetConfig

def migrate_existing_configs():
    """Migra configuraciones existentes a la nueva app."""
    print("=== Migrando configuraciones existentes ===")
    
    # Migrar configuraciones de Tiendanube
    old_tiendanube_configs = TiendaNubeConfig.objects.all()
    for old_config in old_tiendanube_configs:
        if not TiendanubeConfig.objects.filter(store_id=old_config.store_id).exists():
            new_config = TiendanubeConfig.objects.create(
                name=f"Tiendanube Store {old_config.store_id}",
                store_id=old_config.store_id,
                access_token=old_config.access_token,
                api_url=old_config.api_url or "https://api.tiendanube.com/v1",
                is_active=old_config.is_active if hasattr(old_config, 'is_active') else True
            )
            print(f"✓ Migrada configuración de Tiendanube: {new_config.name}")
        else:
            print(f"⚠ Configuración de Tiendanube ya existe: {old_config.store_id}")
    
    # Migrar configuraciones de AdministraNET
    old_adminet_configs = TiendaNubeAdminetConfig.objects.all()
    for old_config in old_adminet_configs:
        if not AdministraNETConfig.objects.filter(host=old_config.host, database=old_config.database).exists():
            new_config = AdministraNETConfig.objects.create(
                name=f"AdministraNET {old_config.host}/{old_config.database}",
                host=old_config.host,
                port=old_config.port or 3306,
                database=old_config.database,
                user=old_config.user,
                password=old_config.password,
                is_active=old_config.is_active
            )
            print(f"✓ Migrada configuración de AdministraNET: {new_config.name}")
        else:
            print(f"⚠ Configuración de AdministraNET ya existe: {old_config.host}/{old_config.database}")

def create_test_configs():
    """Crea configuraciones de prueba si no existen."""
    print("\n=== Creando configuraciones de prueba ===")
    
    # Crear configuración de Tiendanube de prueba
    if not TiendanubeConfig.objects.exists():
        tiendanube_config = TiendanubeConfig.objects.create(
            name="Tiendanube Test Store",
            store_id="123456",
            access_token="test_token_123456789",
            api_url="https://api.tiendanube.com/v1",
            is_active=True
        )
        print(f"✓ Creada configuración de prueba de Tiendanube: {tiendanube_config.name}")
    else:
        print("⚠ Ya existen configuraciones de Tiendanube")
    
    # Crear configuración de AdministraNET de prueba
    if not AdministraNETConfig.objects.exists():
        adminet_config = AdministraNETConfig.objects.create(
            name="AdministraNET Test Database",
            host="mysql",
            port=3306,
            database="administranet",
            user="testuser",
            password="testpass",
            is_active=True
        )
        print(f"✓ Creada configuración de prueba de AdministraNET: {adminet_config.name}")
    else:
        print("⚠ Ya existen configuraciones de AdministraNET")

def test_connections():
    """Prueba las conexiones de las configuraciones activas."""
    print("\n=== Probando conexiones ===")
    
    from tiendanube_administranet.services.sync_service import TiendanubeAdministraNETSyncService
    
    # Obtener configuraciones activas
    tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
    adminet_config = AdministraNETConfig.objects.filter(is_active=True).first()
    
    if not tiendanube_config:
        print("❌ No hay configuración activa de Tiendanube")
        return
    
    if not adminet_config:
        print("❌ No hay configuración activa de AdministraNET")
        return
    
    print(f"Probando conexión con Tiendanube: {tiendanube_config.name}")
    print(f"Probando conexión con AdministraNET: {adminet_config.name}")
    
    try:
        sync_service = TiendanubeAdministraNETSyncService(tiendanube_config, adminet_config)
        connections_ok = sync_service.test_connections()
        
        if connections_ok:
            print("✅ Conexiones exitosas")
            
            # Obtener estadísticas
            stats = sync_service.get_sync_statistics()
            print(f"📊 Estadísticas de sincronización:")
            print(f"   - Mappings totales: {stats['total_mappings']}")
            print(f"   - Mappings sincronizados: {stats['synced_mappings']}")
            print(f"   - Mappings pendientes: {stats['pending_mappings']}")
            print(f"   - Mappings con errores: {stats['error_mappings']}")
            
        else:
            print("❌ Error en las conexiones")
            
    except Exception as e:
        print(f"❌ Error al probar conexiones: {e}")
    finally:
        if 'sync_service' in locals():
            sync_service.close_connections()

def show_current_configs():
    """Muestra las configuraciones actuales."""
    print("\n=== Configuraciones actuales ===")
    
    tiendanube_configs = TiendanubeConfig.objects.all()
    adminet_configs = AdministraNETConfig.objects.all()
    
    print(f"Configuraciones de Tiendanube ({tiendanube_configs.count()}):")
    for config in tiendanube_configs:
        status = "✅ Activa" if config.is_active else "❌ Inactiva"
        print(f"  - {config.name} (Store ID: {config.store_id}) - {status}")
    
    print(f"\nConfiguraciones de AdministraNET ({adminet_configs.count()}):")
    for config in adminet_configs:
        status = "✅ Activa" if config.is_active else "❌ Inactiva"
        print(f"  - {config.name} ({config.host}:{config.port}/{config.database}) - {status}")

def main():
    """Función principal."""
    print("🚀 Configurando nueva app tiendanube_administranet")
    print("=" * 50)
    
    try:
        # Migrar configuraciones existentes
        migrate_existing_configs()
        
        # Crear configuraciones de prueba si es necesario
        create_test_configs()
        
        # Mostrar configuraciones actuales
        show_current_configs()
        
        # Probar conexiones
        test_connections()
        
        print("\n✅ Configuración completada exitosamente")
        print("\n📝 Próximos pasos:")
        print("1. Acceder a /tiendanube-adminet/ para ver el dashboard")
        print("2. Configurar las credenciales reales en las configuraciones")
        print("3. Ejecutar una sincronización de prueba")
        
    except Exception as e:
        print(f"❌ Error durante la configuración: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 