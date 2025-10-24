#!/usr/bin/env python
"""
Script para sincronizar clientes de Tiendanube a Synap.
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from tiendanube_administranet.models import TiendanubeConfig
from tiendanube.models_synap import TiendaNubeCustomerMapping
from sales.models import Client
from core.models import Contact
from decimal import Decimal
import requests

def sync_customers_from_tiendanube():
    """Sincronizar clientes desde Tiendanube a Synap."""
    try:
        # Obtener configuración
        config = TiendanubeConfig.objects.filter(is_active=True).first()
        
        if not config:
            print("❌ No se encontró configuración activa de Tiendanube")
            return False
        
        print(f"✅ Configuración encontrada: Store ID {config.store_id}")
        
        headers = {
            'Content-Type': 'application/json',
            'Authentication': f'bearer {config.access_token}',
            'User-Agent': 'Synap-Administranet/1.0'
        }
        
        # Obtener clientes de Tiendanube
        print("🔄 Obteniendo clientes de Tiendanube...")
        response = requests.get(f'https://api.tiendanube.com/v1/{config.store_id}/customers?limit=50', headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Error obteniendo clientes: {response.status_code} - {response.text}")
            return False
        
        customers = response.json()
        print(f"📋 Clientes encontrados en Tiendanube: {len(customers)}")
        
        success_count = 0
        failed_count = 0
        
        for customer_data in customers:
            try:
                tiendanube_id = customer_data.get('id')
                
                # Verificar si ya existe el mapping
                if TiendaNubeCustomerMapping.objects.filter(tiendanube_id=tiendanube_id).exists():
                    print(f"⏭️  Cliente {tiendanube_id} ya sincronizado, saltando...")
                    continue
                
                # Crear cliente en Synap
                client = Client.objects.create(
                    name=customer_data.get('name', 'Cliente Tiendanube'),
                    email=customer_data.get('email', ''),
                    document_number=customer_data.get('document', ''),
                    type='individual' if not customer_data.get('document') else 'company',
                    credit_limit=Decimal('0.00'),
                    tags='tiendanube'
                )
                
                # Crear contacto
                contact = Contact.objects.create(
                    name=customer_data.get('name', 'Cliente Tiendanube'),
                    email=customer_data.get('email', ''),
                    phone=customer_data.get('phone', ''),
                    address=customer_data.get('address', ''),
                    city=customer_data.get('city', ''),
                    state=customer_data.get('state', ''),
                    country=customer_data.get('country', 'Argentina'),
                    notes=customer_data.get('document', ''),
                    tags='tiendanube'
                )
                
                # Relacionar cliente con contacto
                client.add_contact_relationship(contact, relationship_type='primary')
                
                # Crear mapping
                TiendaNubeCustomerMapping.objects.create(
                    client=client,
                    tiendanube_id=tiendanube_id,
                    tiendanube_email=customer_data.get('email', ''),
                    tiendanube_document=customer_data.get('document', ''),
                    sync_status=TiendaNubeCustomerMapping.SyncStatus.SYNCED
                )
                
                print(f"✅ Cliente sincronizado: {client.name} ({client.email})")
                success_count += 1
                
            except Exception as e:
                print(f"❌ Error sincronizando cliente {customer_data.get('id', 'N/A')}: {str(e)}")
                failed_count += 1
        
        print(f"\n📊 Resumen de sincronización:")
        print(f"✅ Exitosos: {success_count}")
        print(f"❌ Fallidos: {failed_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en sincronización: {str(e)}")
        return False

if __name__ == "__main__":
    success = sync_customers_from_tiendanube()
    sys.exit(0 if success else 1)
