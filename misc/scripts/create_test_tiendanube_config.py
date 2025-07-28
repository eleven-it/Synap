#!/usr/bin/env python
"""
Script para crear una configuración de prueba de Tiendanube.
Uso: docker exec Synap_app python misc/scripts/create_test_tiendanube_config.py
"""

import os
import sys
import django

# Agregar el directorio raíz al path
sys.path.append('/app')

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from tiendanube.models_synap import TiendaNubeConfig

def create_test_config():
    """Crear configuración de prueba de Tiendanube"""
    print("🔧 CREANDO CONFIGURACIÓN DE PRUEBA DE TIENDANUBE")
    print("="*60)
    
    # Verificar si ya existe configuración
    existing_config = TiendaNubeConfig.objects.first()
    if existing_config:
        print(f"✅ Ya existe una configuración:")
        print(f"   ID: {existing_config.id}")
        print(f"   Store ID: {existing_config.store_id}")
        print(f"   API URL: {existing_config.api_url}")
        return existing_config
    
    # Crear configuración de prueba
    print("📝 Creando configuración de prueba...")
    
    config = TiendaNubeConfig.objects.create(
        store_id="test_store_123",
        access_token="test_token_456",
        api_url="https://api.tiendanube.com/v1",
        auto_sync=True,
        sync_interval=30,
        sync_products=True,
        sync_stock=True,
        sync_orders=True,
        sync_customers=True,
        webhook_active=True
    )
    
    print(f"✅ Configuración creada exitosamente:")
    print(f"   ID: {config.id}")
    print(f"   Store ID: {config.store_id}")
    print(f"   API URL: {config.api_url}")
    print(f"   Auto Sync: {config.auto_sync}")
    print(f"   Sync Interval: {config.sync_interval} minutos")
    
    return config

def main():
    """Función principal"""
    config = create_test_config()
    
    print("\n" + "="*60)
    print(" RESUMEN")
    print("="*60)
    print("✅ Configuración de Tiendanube lista para pruebas")
    print("💡 Ahora puedes ejecutar el script de métodos de pago")
    print("🔗 Script: misc/scripts/test_tiendanube_payment_methods.py")

if __name__ == "__main__":
    main() 