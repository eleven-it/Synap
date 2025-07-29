#!/usr/bin/env python
"""
Script para probar la conexión a AdministraNET desde el sistema unificado.
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
sys.path.append('/app')
django.setup()

from tiendanube.models_unified import TiendaNubeUnifiedConfig
from tiendanube.services.unified_customer_sync_service import UnifiedCustomerSyncService
from administraNET_integration.services.connection_service import AdministraNETConnectionService
import logging

logger = logging.getLogger(__name__)

def test_adminet_connection():
    """Prueba la conexión a AdministraNET."""
    
    print("=== Prueba de Conexión AdministraNET ===")
    
    # Obtener configuración unificada
    config = TiendaNubeUnifiedConfig.objects.filter(is_active=True).first()
    if not config:
        print("❌ No hay configuración unificada activa")
        return False
    
    print(f"✅ Configuración encontrada: {config.name}")
    print(f"   - Host: {config.adminet_host}")
    print(f"   - Puerto: {config.adminet_port}")
    print(f"   - Base de datos: {config.adminet_database}")
    print(f"   - Usuario: {config.adminet_user}")
    
    # Crear configuración temporal para el servicio
    class TempConfig:
        def __init__(self, unified_config):
            self.host = unified_config.adminet_host
            self.port = unified_config.adminet_port
            self.database_name = unified_config.adminet_database
            self.username = unified_config.adminet_user
            self.password = unified_config.adminet_password
        
        def get_connection_string(self):
            return f"{self.host}:{self.port}/{self.database_name}"
    
    temp_config = TempConfig(config)
    
    # Probar conexión directa
    try:
        mysql_service = AdministraNETConnectionService(temp_config)
        
        # Probar conexión
        test_result = mysql_service.test_connection()
        if test_result['success']:
            print("✅ Conexión directa exitosa")
            print(f"   - Base de datos: {test_result['database_info']['name']}")
            print(f"   - Versión: {test_result['version']}")
            
            # Probar consulta simple
            result = mysql_service.execute_query("SELECT COUNT(*) as total FROM clientes")
            if result['success']:
                count = result['data'][0]['total'] if result['data'] else 0
                print(f"✅ Consulta exitosa - Total clientes: {count}")
            else:
                print(f"❌ Error en consulta: {result['error']}")
            
            mysql_service.close_connection()
            return True
        else:
            print(f"❌ Error de conexión: {test_result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ Error de conexión: {str(e)}")
        return False

def test_unified_service():
    """Prueba el servicio unificado."""
    
    print("\n=== Prueba del Servicio Unificado ===")
    
    config = TiendaNubeUnifiedConfig.objects.filter(is_active=True).first()
    if not config:
        print("❌ No hay configuración unificada activa")
        return False
    
    try:
        service = UnifiedCustomerSyncService(config)
        print("✅ Servicio unificado creado correctamente")
        
        # Probar estadísticas
        stats = service.get_sync_statistics()
        print(f"✅ Estadísticas obtenidas:")
        print(f"   - Total mapeos: {stats['total_mappings']}")
        print(f"   - Mapeos sincronizados: {stats['synced_mappings']}")
        print(f"   - Mapeos pendientes: {stats['pending_mappings']}")
        print(f"   - Mapeos con error: {stats['error_mappings']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en servicio unificado: {str(e)}")
        return False

def test_adminet_customers():
    """Prueba obtener clientes de AdministraNET."""
    
    print("\n=== Prueba de Obtención de Clientes ===")
    
    config = TiendaNubeUnifiedConfig.objects.filter(is_active=True).first()
    if not config:
        print("❌ No hay configuración unificada activa")
        return False
    
    try:
        service = UnifiedCustomerSyncService(config)
        
        # Probar obtener clientes de AdministraNET
        customers = service._get_adminet_customers()
        print(f"✅ Clientes obtenidos de AdministraNET: {len(customers) if customers else 0}")
        
        if customers:
            print("   Primeros 3 clientes:")
            for i, customer in enumerate(customers[:3]):
                print(f"   {i+1}. Código: {customer.get('codigo', 'N/A')}, Nombre: {customer.get('nombre', 'N/A')}")
        else:
            print("   No se encontraron clientes activos")
        
        return True
        
    except Exception as e:
        print(f"❌ Error obteniendo clientes: {str(e)}")
        return False

if __name__ == "__main__":
    print("=== Test de Conexión AdministraNET ===")
    
    # Probar conexión directa
    connection_ok = test_adminet_connection()
    
    # Probar servicio unificado
    service_ok = test_unified_service()
    
    # Probar obtención de clientes
    customers_ok = test_adminet_customers()
    
    print("\n=== Resumen ===")
    print(f"✅ Conexión directa: {'OK' if connection_ok else 'FAIL'}")
    print(f"✅ Servicio unificado: {'OK' if service_ok else 'FAIL'}")
    print(f"✅ Obtención de clientes: {'OK' if customers_ok else 'FAIL'}")
    
    if connection_ok and service_ok and customers_ok:
        print("\n🎉 Todas las pruebas pasaron exitosamente!")
        print("El sistema unificado está funcionando correctamente.")
    else:
        print("\n⚠️  Algunas pruebas fallaron. Revisa los errores arriba.") 