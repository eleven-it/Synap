#!/usr/bin/env python3
"""
Script para actualizar las URLs de los webhooks existentes en TiendaNube.
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
sys.path.append('/app')
django.setup()

from tiendanube_administranet.models import TiendanubeConfig
from tiendanube_administranet.services.webhook_service import WebhookService
from tiendanube_administranet.services.webhook_auto_config import WebhookAutoConfig
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_webhook_urls():
    """
    Actualizar las URLs de los webhooks existentes.
    """
    print("🔧 Actualizando URLs de webhooks existentes...")
    print()
    
    # Obtener configuración activa
    tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
    if not tiendanube_config:
        print("❌ No hay configuración activa de TiendaNube")
        return False
    
    print(f"📋 Configuración: {tiendanube_config.name}")
    print()
    
    # Crear servicios
    webhook_service = WebhookService(tiendanube_config)
    auto_config = WebhookAutoConfig(tiendanube_config)
    
    # Obtener webhooks existentes
    result = webhook_service.get_webhooks()
    
    if not result['success']:
        print(f"❌ Error obteniendo webhooks: {result.get('error')}")
        return False
    
    webhooks = result.get('webhooks', [])
    print(f"📋 Webhooks existentes: {len(webhooks)}")
    print()
    
    # URL correcta del webhook
    correct_url = auto_config.get_webhook_base_url() + "/tiendanube-adminet/webhook/"
    print(f"🔗 URL correcta: {correct_url}")
    print()
    
    updated_count = 0
    failed_count = 0
    
    for webhook in webhooks:
        webhook_id = webhook.get('id')
        event = webhook.get('event')
        current_url = webhook.get('url')
        
        print(f"🔄 Actualizando webhook {event} (ID: {webhook_id})")
        print(f"   URL actual: {current_url}")
        
        # Verificar si la URL necesita actualización
        if 'tudominio.com' in current_url or 'localhost' in current_url:
            print(f"   ⚠️  URL necesita actualización")
            
            # Actualizar webhook
            update_data = {
                'webhook_url': correct_url,
                'events': [event],
                'description': f'Webhook para {event}'
            }
            
            update_result = webhook_service.update_webhook(webhook_id, update_data)
            
            if update_result['success']:
                print(f"   ✅ Webhook actualizado exitosamente")
                updated_count += 1
            else:
                print(f"   ❌ Error actualizando webhook: {update_result.get('error')}")
                failed_count += 1
        else:
            print(f"   ✅ URL ya es correcta")
        
        print()
    
    print(f"📊 Resumen de actualización:")
    print(f"   - Actualizados: {updated_count}")
    print(f"   - Fallidos: {failed_count}")
    print()
    
    if updated_count > 0:
        print("✅ URLs de webhooks actualizadas exitosamente")
        return True
    else:
        print("ℹ️  No se necesitaron actualizaciones")
        return True

def verify_updated_webhooks():
    """
    Verificar que los webhooks actualizados funcionen correctamente.
    """
    print("🔍 Verificando webhooks actualizados...")
    print()
    
    # Obtener configuración activa
    tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
    if not tiendanube_config:
        print("❌ No hay configuración activa de TiendaNube")
        return False
    
    # Crear servicio de webhooks
    webhook_service = WebhookService(tiendanube_config)
    
    # Verificar webhooks
    result = webhook_service.get_webhooks()
    
    if result['success']:
        webhooks = result.get('webhooks', [])
        print(f"✅ Webhooks verificados: {len(webhooks)}")
        print()
        
        correct_urls = 0
        incorrect_urls = 0
        
        for webhook in webhooks:
            event = webhook.get('event')
            url = webhook.get('url')
            
            print(f"🔗 {event}: {url}")
            
            # Verificar si la URL es correcta
            if 'tudominio.com' in url or 'localhost' in url:
                print(f"   ❌ URL incorrecta")
                incorrect_urls += 1
            else:
                print(f"   ✅ URL correcta")
                correct_urls += 1
        
        print()
        print(f"📊 Verificación:")
        print(f"   - URLs correctas: {correct_urls}")
        print(f"   - URLs incorrectas: {incorrect_urls}")
        
        if incorrect_urls == 0:
            print("✅ Todas las URLs están correctas")
            return True
        else:
            print("⚠️  Algunas URLs aún necesitan corrección")
            return False
    else:
        print(f"❌ Error verificando webhooks: {result.get('error')}")
        return False

if __name__ == "__main__":
    print("🚀 Iniciando actualización de URLs de webhooks...")
    print()
    
    # Actualizar URLs
    success = update_webhook_urls()
    
    if success:
        print("✅ Actualización completada")
        print()
        
        # Verificar webhooks actualizados
        verify_updated_webhooks()
        
        print("🎯 Webhooks actualizados y verificados")
        print("   - Las URLs ahora apuntan al servidor correcto")
        print("   - Los webhooks están listos para recibir eventos")
        print("   - La sincronización funcionará correctamente")
    else:
        print("❌ Error en la actualización de webhooks")
        sys.exit(1)
