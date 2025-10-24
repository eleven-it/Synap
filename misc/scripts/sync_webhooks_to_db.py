#!/usr/bin/env python3
"""
Script para sincronizar los webhooks de TiendaNube a la base de datos local.
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
sys.path.append('/app')
django.setup()

from tiendanube_administranet.models import TiendanubeConfig, WebhookConfig
from tiendanube_administranet.services.webhook_service import WebhookService
from django.utils import timezone
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sync_webhooks_to_database():
    """
    Sincronizar webhooks de TiendaNube a la base de datos local.
    """
    print("🔄 Sincronizando webhooks de TiendaNube a la base de datos local...")
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
    
    # Obtener webhooks de TiendaNube
    result = webhook_service.get_webhooks()
    
    if not result['success']:
        print(f"❌ Error obteniendo webhooks de TiendaNube: {result.get('error')}")
        return False
    
    webhooks = result.get('webhooks', [])
    print(f"📋 Webhooks en TiendaNube: {len(webhooks)}")
    print()
    
    # Filtrar solo webhooks con URLs correctas
    correct_webhooks = [wh for wh in webhooks if 'tudominio.com' not in wh.get('url', '') and 'localhost' not in wh.get('url', '')]
    print(f"📋 Webhooks con URLs correctas: {len(correct_webhooks)}")
    print()
    
    # Agrupar webhooks por URL (todos tienen la misma URL base)
    webhooks_by_url = {}
    for webhook in correct_webhooks:
        url = webhook.get('url')
        if url not in webhooks_by_url:
            webhooks_by_url[url] = []
        webhooks_by_url[url].append(webhook)
    
    created_count = 0
    updated_count = 0
    skipped_count = 0
    
    for url, webhook_group in webhooks_by_url.items():
        print(f"🔄 Procesando grupo de webhooks para URL: {url}")
        print(f"   Webhooks en el grupo: {len(webhook_group)}")
        
        # Obtener todos los eventos de este grupo
        events = [wh.get('event') for wh in webhook_group]
        webhook_ids = [wh.get('id') for wh in webhook_group]
        
        print(f"   Eventos: {events}")
        print(f"   IDs TiendaNube: {webhook_ids}")
        
        # Verificar si ya existe un webhook con esta URL
        existing_webhook = WebhookConfig.objects.filter(
            tiendanube_config=tiendanube_config,
            webhook_url=url
        ).first()
        
        if existing_webhook:
            print(f"   ⚠️  Webhook ya existe en BD local, actualizando...")
            
            # Actualizar webhook existente con todos los eventos
            existing_webhook.events = events
            existing_webhook.status = 'active'
            existing_webhook.is_active = True
            existing_webhook.last_triggered = None
            # Usar el primer webhook_id como referencia
            existing_webhook.webhook_id = webhook_ids[0]
            existing_webhook.save()
            
            print(f"   ✅ Webhook actualizado con {len(events)} eventos")
            updated_count += 1
        else:
            print(f"   🆕 Creando nuevo webhook en BD local...")
            
            # Crear nuevo webhook con todos los eventos
            new_webhook = WebhookConfig.objects.create(
                tiendanube_config=tiendanube_config,
                webhook_id=webhook_ids[0],  # Usar el primer ID como referencia
                webhook_url=url,
                events=events,
                status='active',
                is_active=True,
                webhook_secret=tiendanube_config.webhook_secret or ''
            )
            
            print(f"   ✅ Webhook creado (ID local: {new_webhook.id}) con {len(events)} eventos")
            created_count += 1
        
        print()
    
    print(f"📊 Resumen de sincronización:")
    print(f"   - Creados: {created_count}")
    print(f"   - Actualizados: {updated_count}")
    print(f"   - Omitidos: {skipped_count}")
    print()
    
    # Verificar webhooks en la BD local
    print("🔍 Verificando webhooks en la base de datos local...")
    local_webhooks = WebhookConfig.objects.filter(tiendanube_config=tiendanube_config)
    print(f"   Total de webhooks en BD local: {local_webhooks.count()}")
    print()
    
    for webhook in local_webhooks:
        print(f"🔗 {webhook.webhook_url}")
        print(f"   ID TiendaNube: {webhook.webhook_id}")
        print(f"   Eventos: {webhook.events}")
        print(f"   Estado: {webhook.status}")
        print(f"   Activo: {webhook.is_active}")
        print()
    
    if created_count > 0 or updated_count > 0:
        print("✅ Sincronización completada exitosamente")
        print("   - Los webhooks ahora aparecerán en /tiendanube-adminet/webhooks/")
        print("   - La interfaz web mostrará los webhooks configurados")
        return True
    else:
        print("ℹ️  No se necesitaron cambios")
        return True

if __name__ == "__main__":
    print("🚀 Iniciando sincronización de webhooks...")
    print()
    
    # Sincronizar webhooks
    success = sync_webhooks_to_database()
    
    if success:
        print("✅ Sincronización completada")
        print()
        print("🎯 Webhooks sincronizados")
        print("   - Los webhooks aparecerán en la interfaz web")
        print("   - Se pueden gestionar desde /tiendanube-adminet/webhooks/")
        print("   - La sincronización está completa")
    else:
        print("❌ Error en la sincronización de webhooks")
        sys.exit(1)
