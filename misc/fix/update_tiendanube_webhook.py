#!/usr/bin/env python
"""
Script para actualizar el webhook en Tiendanube para incluir eventos de clientes.
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from tiendanube_administranet.models import TiendanubeConfig
from tiendanube.services_main import TiendaNubeService

def update_tiendanube_webhook():
    """Actualizar webhook en Tiendanube para incluir eventos de clientes."""
    try:
        # Obtener configuración
        config = TiendanubeConfig.objects.filter(is_active=True).first()
        
        if not config:
            print("❌ No se encontró configuración activa de Tiendanube")
            return False
        
        print(f"✅ Configuración encontrada: Store ID {config.store_id}")
        
        # Crear servicio
        service = TiendaNubeService(config)
        
        # URL del webhook (usando la configuración actual)
        webhook_url = "https://synap.administranet.com.ar/tiendanube/webhook/"
        print(f"📡 URL del webhook: {webhook_url}")
        
        # Crear/actualizar webhook
        print("🔄 Creando webhook en Tiendanube...")
        result = service.create_webhook(webhook_url)
        
        if result:
            print("✅ Webhook creado/actualizado exitosamente en Tiendanube")
            print(f"📋 Respuesta: {result}")
            return True
        else:
            print("❌ Error creando webhook en Tiendanube")
            return False
        
    except Exception as e:
        print(f"❌ Error actualizando webhook: {str(e)}")
        return False

if __name__ == "__main__":
    success = update_tiendanube_webhook()
    sys.exit(0 if success else 1)
