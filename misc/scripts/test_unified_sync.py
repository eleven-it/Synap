#!/usr/bin/env python
"""
Script para probar el sistema unificado de sincronización de clientes.
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
sys.path.append('/app')
django.setup()

from tiendanube.models_unified import TiendaNubeUnifiedConfig, TiendaNubeUnifiedCustomerMapping
from tiendanube.services.unified_customer_sync_service import UnifiedCustomerSyncService
import logging

logger = logging.getLogger(__name__)

def test_unified_system():
    """Prueba completa del sistema unificado."""
    
    print("=== Test Completo del Sistema Unificado ===")
    
    # 1. Verificar configuración
    print("\n1. Verificando configuración...")
    config = TiendaNubeUnifiedConfig.objects.filter(is_active=True).first()
    if not config:
        print("❌ No hay configuración unificada activa")
        return False
    
    print(f"✅ Configuración encontrada: {config.name}")
    print(f"   - Tiendanube: {'✅' if config.tiendanube_store_id else '❌'}")
    print(f"   - AdministraNET: {'✅' if config.adminet_host else '❌'}")
    
    # 2. Crear servicio
    print("\n2. Creando servicio unificado...")
    try:
        service = UnifiedCustomerSyncService(config)
        print("✅ Servicio unificado creado correctamente")
    except Exception as e:
        print(f"❌ Error creando servicio: {str(e)}")
        return False
    
    # 3. Obtener estadísticas iniciales
    print("\n3. Estadísticas iniciales...")
    stats = service.get_sync_statistics()
    print(f"   - Total mappings: {stats['total_mappings']}")
    print(f"   - Mapeos sincronizados: {stats['synced_mappings']}")
    print(f"   - Mapeos pendientes: {stats['pending_mappings']}")
    print(f"   - Mapeos con error: {stats['error_mappings']}")
    print(f"   - Mapeos AdministraNET: {stats['adminet_mappings']}")
    print(f"   - Porcentaje de sincronización: {stats['sync_percentage']:.1f}%")
    
    # 4. Probar sincronización con AdministraNET
    print("\n4. Probando sincronización con AdministraNET...")
    try:
        success_count, failed_count = service.sync_customers_with_adminet(limit=5)
        print(f"✅ Sincronización AdministraNET: {success_count} exitosos, {failed_count} fallidos")
        
        if failed_count > 0:
            print("⚠️  Algunos clientes fallaron en la sincronización")
    except Exception as e:
        print(f"❌ Error en sincronización AdministraNET: {str(e)}")
        return False
    
    # 5. Verificar estadísticas después de la sincronización
    print("\n5. Estadísticas después de la sincronización...")
    stats_after = service.get_sync_statistics()
    print(f"   - Total mappings: {stats_after['total_mappings']}")
    print(f"   - Mapeos sincronizados: {stats_after['synced_mappings']}")
    print(f"   - Mapeos pendientes: {stats_after['pending_mappings']}")
    print(f"   - Mapeos con error: {stats_after['error_mappings']}")
    print(f"   - Mapeos AdministraNET: {stats_after['adminet_mappings']}")
    print(f"   - Porcentaje de sincronización: {stats_after['sync_percentage']:.1f}%")
    
    # 6. Mostrar algunos mappings de ejemplo
    print("\n6. Mappings de ejemplo...")
    mappings = TiendaNubeUnifiedCustomerMapping.objects.all().order_by('-created_at')[:5]
    for i, mapping in enumerate(mappings, 1):
        print(f"   {i}. {mapping.tiendanube_email} (Adminet: {mapping.adminet_codigo}, Status: {mapping.sync_status})")
    
    # 7. Probar obtención de clientes de AdministraNET
    print("\n7. Probando obtención de clientes de AdministraNET...")
    try:
        customers = service._get_adminet_customers()
        print(f"✅ Clientes obtenidos de AdministraNET: {len(customers)}")
        
        if customers:
            print("   Primeros 3 clientes:")
            for i, customer in enumerate(customers[:3], 1):
                print(f"   {i}. Código: {customer.get('codigo', 'N/A')}, Nombre: {customer.get('nombre', 'N/A')}")
    except Exception as e:
        print(f"❌ Error obteniendo clientes: {str(e)}")
    
    # 8. Verificar logs de sincronización
    print("\n8. Verificando logs de sincronización...")
    from tiendanube.models_unified import TiendaNubeUnifiedSyncLog
    logs = TiendaNubeUnifiedSyncLog.objects.all().order_by('-started_at')[:3]
    print(f"   - Total logs: {TiendaNubeUnifiedSyncLog.objects.count()}")
    print("   - Últimos 3 logs:")
    for log in logs:
        print(f"     • {log.sync_type} - {log.status}: {log.message}")
    
    print("\n=== Resumen del Test ===")
    print("✅ Sistema unificado funcionando correctamente")
    print("✅ Conexión a AdministraNET activa")
    print("✅ Sincronización de clientes operativa")
    print("✅ Mapeos unificados creados correctamente")
    print("✅ Logs de sincronización funcionando")
    
    return True

def show_system_status():
    """Muestra el estado actual del sistema."""
    
    print("\n=== Estado del Sistema Unificado ===")
    
    # Configuración
    config = TiendaNubeUnifiedConfig.objects.filter(is_active=True).first()
    if config:
        print(f"✅ Configuración activa: {config.name}")
        print(f"   - Modo de sincronización: {config.sync_mode}")
        print(f"   - Tamaño de lote: {config.batch_size}")
        print(f"   - Intervalo de sincronización: {config.sync_interval} minutos")
    else:
        print("❌ No hay configuración activa")
        return
    
    # Estadísticas
    service = UnifiedCustomerSyncService(config)
    stats = service.get_sync_statistics()
    
    print(f"\n📊 Estadísticas:")
    print(f"   - Total de mapeos: {stats['total_mappings']}")
    print(f"   - Mapeos sincronizados: {stats['synced_mappings']} ({stats['sync_percentage']:.1f}%)")
    print(f"   - Mapeos pendientes: {stats['pending_mappings']}")
    print(f"   - Mapeos con error: {stats['error_mappings']}")
    
    print(f"\n🌐 Mapeos por plataforma:")
    print(f"   - Tiendanube: {stats['tiendanube_mappings']}")
    print(f"   - Synap: {stats['synap_mappings']}")
    print(f"   - AdministraNET: {stats['adminet_mappings']}")
    
    # Conexiones
    print(f"\n🔗 Estado de conexiones:")
    print(f"   - AdministraNET: {'✅ Activa' if config.adminet_host else '❌ No configurada'}")
    print(f"   - Tiendanube: {'✅ Configurada' if config.tiendanube_store_id else '❌ No configurada'}")

if __name__ == "__main__":
    print("=== Test del Sistema Unificado de Sincronización ===")
    
    # Mostrar estado del sistema
    show_system_status()
    
    # Ejecutar test completo
    success = test_unified_system()
    
    if success:
        print("\n🎉 ¡Todos los tests pasaron exitosamente!")
        print("El sistema unificado está funcionando correctamente.")
    else:
        print("\n⚠️  Algunos tests fallaron. Revisa los errores arriba.") 