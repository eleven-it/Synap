#!/usr/bin/env python
"""
Script para actualizar los eventos de webhook de Tiendanube
para incluir eventos de clientes.
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from tiendanube_administranet.models import WebhookConfig

def update_webhook_events():
    """Actualizar eventos de webhook para incluir clientes."""
    try:
        # Obtener configuración existente
        config = WebhookConfig.objects.first()
        
        if not config:
            print("❌ No se encontró configuración de webhook")
            return False
        
        # Eventos actuales
        current_events = config.events
        print(f"Eventos actuales: {current_events}")
        
        # Agregar eventos de clientes si no están presentes
        new_events = list(current_events)
        customer_events = ['customer/created', 'customer/updated']
        
        for event in customer_events:
            if event not in new_events:
                new_events.append(event)
                print(f"✅ Agregando evento: {event}")
        
        # Actualizar configuración
        config.events = new_events
        config.save()
        
        print(f"✅ Webhook actualizado exitosamente")
        print(f"Eventos configurados: {config.events}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error actualizando webhook: {str(e)}")
        return False

if __name__ == "__main__":
    success = update_webhook_events()
    sys.exit(0 if success else 1)
