#!/usr/bin/env python
"""
Script de prueba para verificar que las URLs de sales funcionen correctamente
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
sys.path.append('/app')
django.setup()

from django.urls import reverse
from django.test import Client

def test_sales_urls():
    """Prueba que las URLs principales de sales funcionen"""
    print("=== Prueba de URLs de Sales ===")
    
    # URLs a probar
    urls_to_test = [
        'sales:dashboard',
        'sales:client_list',
        'sales:client_create',
        'sales:sales_order_list',
        'sales:sales_order_create',
        'sales:invoice_list',
    ]
    
    client = Client()
    
    for url_name in urls_to_test:
        try:
            url = reverse(url_name)
            print(f"✓ {url_name}: {url}")
            
            # Probar que la URL se puede resolver sin errores
            response = client.get(url)
            if response.status_code in [200, 302, 403]:  # 200=OK, 302=redirect, 403=forbidden
                print(f"  → Status: {response.status_code}")
            else:
                print(f"  → WARNING: Status {response.status_code}")
                
        except Exception as e:
            print(f"✗ {url_name}: ERROR - {e}")
    
    # Probar URLs que NO deben existir
    print("\n=== URLs que NO deben existir ===")
    non_existent_urls = [
        'sales:contact_create',
        'sales:contact_list',
        'sales:contact_create_by_client',
    ]
    
    for url_name in non_existent_urls:
        try:
            url = reverse(url_name)
            print(f"✗ {url_name}: ERROR - URL existe cuando no debería: {url}")
        except:
            print(f"✓ {url_name}: Correctamente no existe")

if __name__ == '__main__':
    test_sales_urls() 