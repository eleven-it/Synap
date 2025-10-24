#!/usr/bin/env python3
"""
Script para configurar automáticamente los webhooks necesarios para la sincronización
entre TiendaNube y AdministraNET.
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
sys.path.append('/app')
django.setup()

from tiendanube_administranet.models import TiendanubeConfig, WebhookConfig
from tiendanube_administranet.services.webhook_auto_config import WebhookAutoConfig
from tiendanube_administranet.services.webhook_service import WebhookService
from django.utils import timezone
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def configure_webhooks():
    """
    Configurar todos los webhooks necesarios para la sincronización.
    """
    print("🔧 Configurando webhooks para sincronización TiendaNube-AdministraNET")
    print()
    
    # Obtener configuración activa
    tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
    if not tiendanube_config:
        print("❌ No hay configuración activa de TiendaNube")
        return False
    
    print(f"📋 Configuración: {tiendanube_config.name}")
    print()
    
    # Crear servicio de configuración automática
    auto_config = WebhookAutoConfig(tiendanube_config)
    
    # Configurar webhooks automáticamente
    result = auto_config.configure_all_webhooks()
    
    if result['success']:
        print("✅ Webhooks configurados exitosamente")
        print()
        
        # Mostrar resumen
        created = result.get('created_webhooks', [])
        skipped = result.get('skipped_webhooks', [])
        failed = result.get('failed_webhooks', [])
        
        print(f"📊 Resumen:")
        print(f"   - Creados: {len(created)}")
        print(f"   - Omitidos: {len(skipped)}")
        print(f"   - Fallidos: {len(failed)}")
        print()
        
        if created:
            print("🆕 Webhooks creados:")
            for webhook in created:
                print(f"   - {webhook.get('event')}: {webhook.get('url')}")
            print()
        
        if skipped:
            print("⏭️  Webhooks omitidos (ya existían):")
            for webhook in skipped:
                print(f"   - {webhook.get('event')}")
            print()
        
        if failed:
            print("❌ Webhooks fallidos:")
            for webhook in failed:
                print(f"   - {webhook.get('event')}: {webhook.get('error')}")
            print()
        
        # Verificar webhooks en la base de datos
        print("🔍 Verificando webhooks en la base de datos...")
        webhooks = WebhookConfig.objects.filter(tiendanube_config=tiendanube_config)
        print(f"   Total de webhooks: {webhooks.count()}")
        
        for webhook in webhooks:
            print(f"   - {webhook.webhook_url}")
            print(f"     Eventos: {webhook.events}")
            print(f"     Estado: {webhook.status}")
            print(f"     Activo: {webhook.is_active}")
            print()
        
        return True
    else:
        print(f"❌ Error configurando webhooks: {result.get('error')}")
        return False

def verify_webhook_functionality():
    """
    Verificar que los webhooks estén funcionando correctamente.
    """
    print("🔍 Verificando funcionalidad de webhooks...")
    print()
    
    # Obtener configuración activa
    tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
    if not tiendanube_config:
        print("❌ No hay configuración activa de TiendaNube")
        return False
    
    # Crear servicio de webhooks
    webhook_service = WebhookService(tiendanube_config)
    
    # Verificar webhooks en TiendaNube
    result = webhook_service.get_webhooks()
    
    if result['success']:
        webhooks = result.get('webhooks', [])
        print(f"✅ Webhooks verificados en TiendaNube: {len(webhooks)}")
        
        for webhook in webhooks:
            print(f"   - {webhook.get('event')}: {webhook.get('url')}")
            print(f"     Estado: {webhook.get('status', 'unknown')}")
            print()
        
        return True
    else:
        print(f"❌ Error verificando webhooks: {result.get('error')}")
        return False

if __name__ == "__main__":
    print("🚀 Iniciando configuración de webhooks...")
    print()
    
    # Configurar webhooks
    success = configure_webhooks()
    
    if success:
        print("✅ Configuración completada exitosamente")
        print()
        
        # Verificar funcionalidad
        verify_webhook_functionality()
        
        print("🎯 Webhooks configurados y verificados")
        print("   - Los webhooks están listos para recibir eventos de TiendaNube")
        print("   - La sincronización automática está habilitada")
        print("   - Los eventos se procesarán en tiempo real")
    else:
        print("❌ Error en la configuración de webhooks")
        sys.exit(1)
