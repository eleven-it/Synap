#!/usr/bin/env python
"""
Script de diagnóstico para verificar el estado de las integraciones de Tiendanube.
Uso: docker exec Synap_app python misc/scripts/check_tiendanube_integrations.py
"""

import os
import sys
import django

# Agregar el directorio raíz al path
sys.path.append('/app')

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from tiendanube.models_synap import TiendaNubeConfig, TiendaNubeSyncLog
from tiendanube.models_adminet import TiendaNubeAdminetConfig
from django.utils import timezone
from datetime import timedelta

def print_header(title):
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_section(title):
    print(f"\n--- {title} ---")

def check_synap_integration():
    """Verificar estado de la integración Synap ↔ Tiendanube"""
    print_header("INTEGRACIÓN SYNAP ↔ TIENDANUBE")
    
    config = TiendaNubeConfig.objects.first()
    
    if not config:
        print("❌ No hay configuración de Tiendanube")
        return False
    
    print(f"✅ Configuración encontrada: Store ID {config.store_id}")
    print(f"📅 Última actualización: {config.updated_at}")
    
    print_section("Estado de Sincronización")
    print(f"🔄 Auto Sync: {'✅ Activo' if config.auto_sync else '❌ Inactivo'}")
    print(f"📦 Sync Products: {'✅ Activo' if config.sync_products else '❌ Inactivo'}")
    print(f"📊 Sync Stock: {'✅ Activo' if config.sync_stock else '❌ Inactivo'}")
    print(f"📋 Sync Orders: {'✅ Activo' if config.sync_orders else '❌ Inactivo'}")
    print(f"👥 Sync Customers: {'✅ Activo' if config.sync_customers else '❌ Inactivo'}")
    print(f"🔗 Webhook Active: {'✅ Activo' if config.webhook_active else '❌ Inactivo'}")
    
    if config.auto_sync:
        print(f"⏰ Sync Interval: {config.sync_interval} minutos")
        if config.last_sync:
            print(f"🕐 Última sincronización: {config.last_sync}")
            time_since = timezone.now() - config.last_sync
            if time_since > timedelta(minutes=config.sync_interval * 2):
                print(f"⚠️  Última sync hace {time_since.total_seconds() / 60:.1f} minutos (puede estar atrasada)")
        else:
            print("⚠️  No hay registro de última sincronización")
    
    return config.auto_sync

def check_adminet_integration():
    """Verificar estado de la integración administraNET ↔ Tiendanube"""
    print_header("INTEGRACIÓN ADMINISTRANET ↔ TIENDANUBE")
    
    config = TiendaNubeAdminetConfig.objects.filter(is_active=True).first()
    
    if not config:
        print("❌ No hay configuración activa de administraNET")
        return False
    
    print(f"✅ Configuración activa encontrada")
    print(f"🌐 Host: {config.host}:{config.port}")
    print(f"🗄️  Database: {config.database}")
    print(f"👤 User: {config.user}")
    print(f"📅 Última actualización: {config.updated_at}")
    
    # Intentar probar conexión
    try:
        from tiendanube.services.connection_service import MySQLConnectionService
        mysql_config = {
            'host': config.host,
            'port': config.port,
            'database': config.database,
            'user': config.user,
            'password': config.password,
        }
        service = MySQLConnectionService(mysql_config)
        result = service.test_connection(test_tables=False)
        
        if result.get('success'):
            print("✅ Conexión MySQL exitosa")
            if 'version' in result:
                print(f"📊 Versión MySQL: {result['version']}")
        else:
            print(f"❌ Error de conexión MySQL: {result.get('error', 'Error desconocido')}")
            return False
            
    except Exception as e:
        print(f"❌ Error probando conexión: {str(e)}")
        return False
    
    return True

def check_recent_logs():
    """Verificar logs recientes de sincronización"""
    print_header("LOGS RECIENTES DE SINCRONIZACIÓN")
    
    # Logs de las últimas 24 horas
    yesterday = timezone.now() - timedelta(days=1)
    recent_logs = TiendaNubeSyncLog.objects.filter(started_at__gte=yesterday).order_by('-started_at')[:10]
    
    if not recent_logs:
        print("📝 No hay logs de sincronización en las últimas 24 horas")
        return
    
    print(f"📝 Últimos {len(recent_logs)} logs de sincronización:")
    
    for log in recent_logs:
        status_icon = "✅" if log.status == 'success' else "❌" if log.status == 'error' else "⚠️"
        print(f"{status_icon} {log.started_at.strftime('%Y-%m-%d %H:%M')} - {log.sync_type} - {log.status}")
        if log.message and len(log.message) > 100:
            print(f"   📄 {log.message[:100]}...")
        elif log.message:
            print(f"   📄 {log.message}")

def check_product_mappings():
    """Verificar mapeos de productos"""
    print_header("MAPEOS DE PRODUCTOS")
    
    from tiendanube.models_synap import TiendaNubeProductMapping
    
    total_mappings = TiendaNubeProductMapping.objects.count()
    active_mappings = TiendaNubeProductMapping.objects.filter(sync_enabled=True).count()
    pending_mappings = TiendaNubeProductMapping.objects.filter(sync_status='pending').count()
    error_mappings = TiendaNubeProductMapping.objects.filter(sync_status='error').count()
    
    print(f"📦 Total de mapeos: {total_mappings}")
    print(f"✅ Mapeos activos: {active_mappings}")
    print(f"⏳ Mapeos pendientes: {pending_mappings}")
    print(f"❌ Mapeos con error: {error_mappings}")
    
    if error_mappings > 0:
        print_section("Productos con Error")
        error_products = TiendaNubeProductMapping.objects.filter(sync_status='error')[:5]
        for mapping in error_products:
            print(f"❌ {mapping.product.sku}: {mapping.error_message[:100]}...")

def check_cond_venta_mappings():
    """Verificar mapeos de condiciones de venta"""
    print_header("MAPEOS DE CONDICIONES DE VENTA")
    
    from tiendanube.models_adminet import TiendaNubeCondVentaMap
    
    total_mappings = TiendaNubeCondVentaMap.objects.count()
    active_mappings = TiendaNubeCondVentaMap.objects.filter(activo=True).count()
    
    print(f"💳 Total de mapeos: {total_mappings}")
    print(f"✅ Mapeos activos: {active_mappings}")
    
    if total_mappings > 0:
        print_section("Mapeos Configurados")
        mappings = TiendaNubeCondVentaMap.objects.filter(activo=True)[:10]
        for mapping in mappings:
            print(f"💳 {mapping.payment_method} → {mapping.adminet_codigo} ({mapping.adminet_descripcion})")

def main():
    """Función principal"""
    print("🔍 DIAGNÓSTICO DE INTEGRACIONES TIENDANUBE")
    print(f"🕐 Fecha y hora: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Verificar integraciones
    synap_active = check_synap_integration()
    adminet_active = check_adminet_integration()
    
    # Verificar logs
    check_recent_logs()
    
    # Verificar mapeos
    check_product_mappings()
    check_cond_venta_mappings()
    
    # Resumen final
    print_header("RESUMEN")
    print(f"🔄 Integración Synap: {'✅ Activa' if synap_active else '❌ Inactiva'}")
    print(f"🗄️  Integración administraNET: {'✅ Activa' if adminet_active else '❌ Inactiva'}")
    
    if not synap_active and not adminet_active:
        print("\n⚠️  AMBAS INTEGRACIONES ESTÁN INACTIVAS")
        print("💡 Para activar:")
        print("   - Synap: Ir a Tiendanube → Settings → Configurations")
        print("   - administraNET: Ir a Tiendanube → Integración administraNET → Conexión Adminet")
    elif synap_active and adminet_active:
        print("\n✅ AMBAS INTEGRACIONES ESTÁN ACTIVAS")
    elif synap_active:
        print("\n✅ Solo integración Synap está activa")
    else:
        print("\n✅ Solo integración administraNET está activa")

if __name__ == "__main__":
    main() 