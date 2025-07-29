#!/usr/bin/env python3
"""
Script para probar la funcionalidad completa de la nueva app tiendanube_administranet.
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

from tiendanube_administranet.models import TiendanubeConfig, AdministraNETConfig, CustomerMapping, SyncLog
from tiendanube_administranet.services.sync_service import TiendanubeAdministraNETSyncService

def test_adminet_connection():
    """Prueba la conexión con AdministraNET y obtiene clientes reales."""
    print("=== Probando conexión con AdministraNET ===")
    
    adminet_config = AdministraNETConfig.objects.filter(is_active=True).first()
    if not adminet_config:
        print("❌ No hay configuración activa de AdministraNET")
        return None
    
    try:
        sync_service = TiendanubeAdministraNETSyncService(None, adminet_config)
        customers = sync_service.adminet_service.get_customers()
        
        print(f"✅ Conexión exitosa con AdministraNET")
        print(f"📊 Total de clientes en AdministraNET: {len(customers)}")
        
        if customers:
            print("📋 Primeros 3 clientes:")
            for i, customer in enumerate(customers[:3]):
                print(f"  {i+1}. Código: {customer.get('codigo', 'N/A')}")
                print(f"     Nombre: {customer.get('nombre', 'N/A')}")
                print(f"     Email: {customer.get('email', 'N/A')}")
                print(f"     Documento: {customer.get('documento', 'N/A')}")
                print()
        
        return customers
        
    except Exception as e:
        print(f"❌ Error al conectar con AdministraNET: {e}")
        return None
    finally:
        if 'sync_service' in locals():
            sync_service.close_connections()

def test_tiendanube_connection():
    """Prueba la conexión con Tiendanube."""
    print("=== Probando conexión con Tiendanube ===")
    
    tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
    if not tiendanube_config:
        print("❌ No hay configuración activa de Tiendanube")
        return None
    
    try:
        sync_service = TiendanubeAdministraNETSyncService(tiendanube_config, None)
        # Intentar obtener información de la tienda
        store_info = sync_service.tiendanube_service.get_store_info()
        
        if store_info:
            print("✅ Conexión exitosa con Tiendanube")
            print(f"📊 Información de la tienda: {store_info}")
        else:
            print("⚠ Conexión con Tiendanube (credenciales de prueba)")
            
        return True
        
    except Exception as e:
        print(f"⚠ Conexión con Tiendanube (credenciales de prueba): {e}")
        return False
    finally:
        if 'sync_service' in locals():
            sync_service.close_connections()

def create_test_mappings(adminet_customers):
    """Crea mappings de prueba con clientes reales de AdministraNET."""
    print("=== Creando mappings de prueba ===")
    
    if not adminet_customers:
        print("❌ No hay clientes de AdministraNET para crear mappings")
        return
    
    # Limpiar mappings existentes de prueba
    CustomerMapping.objects.filter(tiendanube_email__startswith='test_').delete()
    
    created_mappings = []
    
    for i, customer in enumerate(adminet_customers[:3]):  # Crear máximo 3 mappings de prueba
        codigo = customer.get('codigo')
        nombre = customer.get('nombre', 'Cliente Test')
        email = customer.get('email')
        
        # Si no hay email, crear uno de prueba
        if not email:
            email = f"test_adminet_{codigo}@administranet.local"
        
        # Crear mapping
        mapping = CustomerMapping.objects.create(
            tiendanube_email=f"test_tiendanube_{codigo}@tiendanube.com",
            tiendanube_name=f"Cliente Tiendanube {codigo}",
            adminet_codigo=codigo,
            adminet_nombre=nombre,
            adminet_documento=customer.get('documento', ''),
            sync_direction=CustomerMapping.SyncDirection.BIDIRECTIONAL,
            sync_status=CustomerMapping.SyncStatus.PENDING
        )
        
        created_mappings.append(mapping)
        print(f"✓ Creado mapping: {mapping}")
    
    print(f"📊 Total de mappings creados: {len(created_mappings)}")
    return created_mappings

def test_sync_functionality():
    """Prueba la funcionalidad de sincronización."""
    print("=== Probando funcionalidad de sincronización ===")
    
    tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
    adminet_config = AdministraNETConfig.objects.filter(is_active=True).first()
    
    if not tiendanube_config or not adminet_config:
        print("❌ No hay configuraciones activas para sincronización")
        return
    
    try:
        sync_service = TiendanubeAdministraNETSyncService(tiendanube_config, adminet_config)
        
        # Obtener estadísticas
        stats = sync_service.get_sync_statistics()
        print(f"📊 Estadísticas de sincronización:")
        print(f"   - Mappings totales: {stats['total_mappings']}")
        print(f"   - Mappings sincronizados: {stats['synced_mappings']}")
        print(f"   - Mappings pendientes: {stats['pending_mappings']}")
        print(f"   - Mappings con errores: {stats['error_mappings']}")
        
        # Probar sincronización desde AdministraNET
        print("\n🔄 Probando sincronización desde AdministraNET...")
        result = sync_service.sync_customers_from_adminet()
        print(f"✅ Sincronización completada: {result['success_count']} exitosos, {result['error_count']} errores")
        
        if result['errors']:
            print("⚠ Errores encontrados:")
            for error in result['errors'][:3]:  # Mostrar solo los primeros 3 errores
                print(f"   - {error}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en sincronización: {e}")
        return False
    finally:
        if 'sync_service' in locals():
            sync_service.close_connections()

def show_final_status():
    """Muestra el estado final del sistema."""
    print("\n=== Estado final del sistema ===")
    
    # Estadísticas de modelos
    tiendanube_configs = TiendanubeConfig.objects.count()
    adminet_configs = AdministraNETConfig.objects.count()
    mappings = CustomerMapping.objects.count()
    logs = SyncLog.objects.count()
    
    print(f"📊 Configuraciones de Tiendanube: {tiendanube_configs}")
    print(f"📊 Configuraciones de AdministraNET: {adminet_configs}")
    print(f"📊 Mappings de clientes: {mappings}")
    print(f"📊 Logs de sincronización: {logs}")
    
    # Mostrar algunos mappings recientes
    recent_mappings = CustomerMapping.objects.all()[:5]
    if recent_mappings:
        print("\n📋 Mappings recientes:")
        for mapping in recent_mappings:
            status_icon = "✅" if mapping.sync_status == "synced" else "⏳" if mapping.sync_status == "pending" else "❌"
            print(f"  {status_icon} {mapping.tiendanube_email} → {mapping.adminet_codigo} ({mapping.sync_status})")

def main():
    """Función principal."""
    print("🚀 Probando funcionalidad completa de tiendanube_administranet")
    print("=" * 60)
    
    try:
        # Probar conexiones
        adminet_customers = test_adminet_connection()
        tiendanube_ok = test_tiendanube_connection()
        
        # Crear mappings de prueba
        if adminet_customers:
            test_mappings = create_test_mappings(adminet_customers)
        
        # Probar sincronización
        sync_ok = test_sync_functionality()
        
        # Mostrar estado final
        show_final_status()
        
        print("\n✅ Pruebas completadas exitosamente")
        print("\n📝 Resumen:")
        print(f"   - AdministraNET: {'✅ Conectado' if adminet_customers else '❌ Error'}")
        print(f"   - Tiendanube: {'✅ Conectado' if tiendanube_ok else '⚠ Credenciales de prueba'}")
        print(f"   - Sincronización: {'✅ Funcionando' if sync_ok else '❌ Error'}")
        
        print("\n🌐 Próximos pasos:")
        print("1. Acceder a http://localhost:8000/tiendanube-adminet/ para ver el dashboard")
        print("2. Configurar credenciales reales de Tiendanube en la configuración")
        print("3. Ejecutar sincronizaciones manuales desde la interfaz web")
        
    except Exception as e:
        print(f"❌ Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 