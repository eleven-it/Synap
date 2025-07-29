#!/usr/bin/env python
"""
Script para configurar el sistema unificado de sincronización de clientes.
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
sys.path.append('/app')
django.setup()

from tiendanube.models_unified import TiendaNubeUnifiedConfig
from tiendanube.models_synap import TiendaNubeConfig
from tiendanube.models_adminet import TiendaNubeAdminetConfig

def setup_unified_config():
    """Configura el sistema unificado usando configuraciones existentes."""
    
    print("Configurando sistema unificado de sincronización de clientes...")
    
    # Verificar si ya existe una configuración unificada
    existing_config = TiendaNubeUnifiedConfig.objects.filter(is_active=True).first()
    if existing_config:
        print(f"Ya existe una configuración unificada activa: {existing_config.name}")
        return existing_config
    
    # Buscar configuración de Tiendanube existente
    tiendanube_config = TiendaNubeConfig.objects.filter(is_active=True).first()
    if not tiendanube_config:
        print("No se encontró configuración activa de Tiendanube")
        return None
    
    # Buscar configuración de AdministraNET existente
    adminet_config = TiendaNubeAdminetConfig.objects.filter(is_active=True).first()
    if not adminet_config:
        print("No se encontró configuración activa de AdministraNET")
        return None
    
    # Crear configuración unificada
    unified_config = TiendaNubeUnifiedConfig.objects.create(
        name="Configuración Unificada Automática",
        is_active=True,
        sync_mode='manual',
        
        # Configuración de Tiendanube
        tiendanube_store_id=tiendanube_config.store_id,
        tiendanube_access_token=tiendanube_config.access_token,
        tiendanube_api_url=tiendanube_config.api_url,
        
        # Configuración de AdministraNET
        adminet_host=adminet_config.host,
        adminet_port=adminet_config.port,
        adminet_database=adminet_config.database,
        adminet_user=adminet_config.user,
        adminet_password=adminet_config.password,
        
        # Configuración de sincronización
        sync_interval=30,
        batch_size=100,
        max_retries=3,
        
        # Configuración de notificaciones
        notify_on_error=True,
        notify_email="admin@administranet.com.ar"
    )
    
    print(f"Configuración unificada creada exitosamente: {unified_config.name}")
    print(f"Tiendanube Store ID: {unified_config.tiendanube_store_id}")
    print(f"AdministraNET Host: {unified_config.adminet_host}")
    
    return unified_config

def show_config_status():
    """Muestra el estado de las configuraciones."""
    
    print("\n=== Estado de Configuraciones ===")
    
    # Configuración unificada
    unified_config = TiendaNubeUnifiedConfig.objects.filter(is_active=True).first()
    if unified_config:
        print(f"✅ Configuración Unificada: {unified_config.name}")
        print(f"   - Tiendanube: {'✅' if unified_config.tiendanube_store_id else '❌'}")
        print(f"   - AdministraNET: {'✅' if unified_config.adminet_host else '❌'}")
    else:
        print("❌ No hay configuración unificada activa")
    
    # Configuración de Tiendanube
    tiendanube_config = TiendaNubeConfig.objects.filter(is_active=True).first()
    if tiendanube_config:
        print(f"✅ Configuración Tiendanube: {tiendanube_config.store_id}")
    else:
        print("❌ No hay configuración de Tiendanube activa")
    
    # Configuración de AdministraNET
    adminet_config = TiendaNubeAdminetConfig.objects.filter(is_active=True).first()
    if adminet_config:
        print(f"✅ Configuración AdministraNET: {adminet_config.host}")
    else:
        print("❌ No hay configuración de AdministraNET activa")

if __name__ == "__main__":
    print("=== Setup Sistema Unificado de Sincronización ===")
    
    # Mostrar estado actual
    show_config_status()
    
    # Configurar sistema unificado
    config = setup_unified_config()
    
    if config:
        print("\n✅ Sistema unificado configurado exitosamente!")
        print("Ahora puedes ejecutar la migración con:")
        print("docker exec Synap_app python manage.py migrate_to_unified_customer_sync")
    else:
        print("\n❌ No se pudo configurar el sistema unificado")
        print("Asegúrate de tener configuraciones activas de Tiendanube y AdministraNET") 