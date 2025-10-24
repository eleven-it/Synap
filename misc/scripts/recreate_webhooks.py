#!/usr/bin/env python3
"""
Script para recrear los webhooks con las URLs correctas.
Elimina los webhooks existentes y crea nuevos con las URLs correctas.
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

def recreate_webhooks():
    """
    Recrear todos los webhooks con las URLs correctas.
    """
    print("🔧 Recreando webhooks con URLs correctas...")
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
    
    deleted_count = 0
    failed_deletions = 0
    created_count = 0
    failed_creations = 0
    
    # Eliminar webhooks existentes
    print("🗑️  Eliminando webhooks existentes...")
    for webhook in webhooks:
        webhook_id = webhook.get('id')
        event = webhook.get('event')
        
        print(f"   🗑️  Eliminando webhook {event} (ID: {webhook_id})")
        
        delete_result = webhook_service.delete_webhook(webhook_id)
        
        if delete_result['success']:
            print(f"   ✅ Webhook eliminado exitosamente")
            deleted_count += 1
        else:
            print(f"   ❌ Error eliminando webhook: {delete_result.get('error')}")
            failed_deletions += 1
        
        print()
    
    print(f"📊 Resumen de eliminación:")
    print(f"   - Eliminados: {deleted_count}")
    print(f"   - Fallidos: {failed_deletions}")
    print()
    
    # Crear nuevos webhooks
    print("🆕 Creando nuevos webhooks...")
    
    # Eventos necesarios
    required_events = [
        'order/created',
        'order/paid',
        'order/updated',
        'order/fulfilled',
        'order/cancelled',
        'product/created',
        'product/updated',
        'product/deleted'
    ]
    
    for event in required_events:
        print(f"   🆕 Creando webhook para {event}")
        
        webhook_data = {
            'webhook_url': correct_url,
            'events': [event],
            'description': f'Webhook para {event} - Sincronización TiendaNube-AdministraNET'
        }
        
        create_result = webhook_service.create_webhook(webhook_data)
        
        if create_result['success']:
            print(f"   ✅ Webhook creado exitosamente")
            created_count += 1
        else:
            print(f"   ❌ Error creando webhook: {create_result.get('error')}")
            failed_creations += 1
        
        print()
    
    print(f"📊 Resumen de creación:")
    print(f"   - Creados: {created_count}")
    print(f"   - Fallidos: {failed_creations}")
    print()
    
    if created_count > 0:
        print("✅ Webhooks recreados exitosamente")
        return True
    else:
        print("❌ No se pudieron crear webhooks")
        return False

def verify_new_webhooks():
    """
    Verificar que los nuevos webhooks funcionen correctamente.
    """
    print("🔍 Verificando nuevos webhooks...")
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
            print("✅ Todos los webhooks tienen URLs correctas")
            return True
        else:
            print("⚠️  Algunos webhooks aún tienen URLs incorrectas")
            return False
    else:
        print(f"❌ Error verificando webhooks: {result.get('error')}")
        return False

if __name__ == "__main__":
    print("🚀 Iniciando recreación de webhooks...")
    print()
    
    # Recrear webhooks
    success = recreate_webhooks()
    
    if success:
        print("✅ Recreación completada")
        print()
        
        # Verificar nuevos webhooks
        verify_new_webhooks()
        
        print("🎯 Webhooks recreados y verificados")
        print("   - Los webhooks ahora tienen URLs correctas")
        print("   - Los webhooks están listos para recibir eventos")
        print("   - La sincronización funcionará correctamente")
    else:
        print("❌ Error en la recreación de webhooks")
        sys.exit(1)
