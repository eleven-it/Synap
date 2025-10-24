#!/usr/bin/env python3
"""
Script para limpiar webhooks antiguos y mantener solo los nuevos con URLs correctas.
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
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_old_webhooks():
    """
    Limpiar webhooks antiguos que tienen URLs incorrectas.
    """
    print("🧹 Limpiando webhooks antiguos...")
    print()
    
    # Obtener configuración activa
    tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
    if not tiendanube_config:
        print("❌ No hay configuración activa de TiendaNube")
        return False
    
    print(f"📋 Configuración: {tiendanube_config.name}")
    print()
    
    # Crear servicio de webhooks
    webhook_service = WebhookService(tiendanube_config)
    
    # Obtener webhooks existentes
    result = webhook_service.get_webhooks()
    
    if not result['success']:
        print(f"❌ Error obteniendo webhooks: {result.get('error')}")
        return False
    
    webhooks = result.get('webhooks', [])
    print(f"📋 Webhooks existentes: {len(webhooks)}")
    print()
    
    # Identificar webhooks antiguos (con URLs incorrectas)
    old_webhooks = []
    new_webhooks = []
    
    for webhook in webhooks:
        url = webhook.get('url', '')
        if 'tudominio.com' in url or 'localhost' in url:
            old_webhooks.append(webhook)
        else:
            new_webhooks.append(webhook)
    
    print(f"📊 Análisis de webhooks:")
    print(f"   - Webhooks antiguos (URLs incorrectas): {len(old_webhooks)}")
    print(f"   - Webhooks nuevos (URLs correctas): {len(new_webhooks)}")
    print()
    
    if len(old_webhooks) == 0:
        print("✅ No hay webhooks antiguos para limpiar")
        return True
    
    # Mostrar webhooks antiguos
    print("🗑️  Webhooks antiguos identificados:")
    for webhook in old_webhooks:
        event = webhook.get('event')
        url = webhook.get('url')
        webhook_id = webhook.get('id')
        print(f"   - {event} (ID: {webhook_id}): {url}")
    print()
    
    # Intentar eliminar webhooks antiguos
    deleted_count = 0
    failed_deletions = 0
    
    print("🗑️  Intentando eliminar webhooks antiguos...")
    for webhook in old_webhooks:
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
    
    print(f"📊 Resumen de limpieza:")
    print(f"   - Eliminados: {deleted_count}")
    print(f"   - Fallidos: {failed_deletions}")
    print()
    
    # Verificar webhooks restantes
    print("🔍 Verificando webhooks restantes...")
    result = webhook_service.get_webhooks()
    
    if result['success']:
        remaining_webhooks = result.get('webhooks', [])
        print(f"✅ Webhooks restantes: {len(remaining_webhooks)}")
        print()
        
        correct_urls = 0
        incorrect_urls = 0
        
        for webhook in remaining_webhooks:
            event = webhook.get('event')
            url = webhook.get('url')
            
            print(f"🔗 {event}: {url}")
            
            if 'tudominio.com' in url or 'localhost' in url:
                print(f"   ❌ URL incorrecta")
                incorrect_urls += 1
            else:
                print(f"   ✅ URL correcta")
                correct_urls += 1
        
        print()
        print(f"📊 Verificación final:")
        print(f"   - URLs correctas: {correct_urls}")
        print(f"   - URLs incorrectas: {incorrect_urls}")
        
        if incorrect_urls == 0:
            print("✅ Todos los webhooks restantes tienen URLs correctas")
            return True
        else:
            print("⚠️  Algunos webhooks aún tienen URLs incorrectas")
            return False
    else:
        print(f"❌ Error verificando webhooks: {result.get('error')}")
        return False

if __name__ == "__main__":
    print("🚀 Iniciando limpieza de webhooks antiguos...")
    print()
    
    # Limpiar webhooks antiguos
    success = cleanup_old_webhooks()
    
    if success:
        print("✅ Limpieza completada exitosamente")
        print()
        print("🎯 Webhooks optimizados")
        print("   - Solo quedan webhooks con URLs correctas")
        print("   - Los webhooks están listos para recibir eventos")
        print("   - La sincronización funcionará correctamente")
    else:
        print("❌ Error en la limpieza de webhooks")
        sys.exit(1)
