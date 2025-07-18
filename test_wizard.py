#!/usr/bin/env python3
"""
Script de prueba para el wizard de clientes
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()

def test_wizard():
    """Prueba el wizard de clientes"""
    client = Client()
    
    # Crear un usuario de prueba
    user, created = User.objects.get_or_create(
        email='test@example.com',
        defaults={
            'nombre': 'Test User',
            'is_staff': True,
            'is_superuser': True
        }
    )
    
    if created:
        user.set_password('testpass123')
        user.save()
    
    # Login
    login_success = client.login(email='test@example.com', password='testpass123')
    print(f"Login exitoso: {login_success}")
    
    # Probar paso 1
    print("\n--- Probando Paso 1 ---")
    response = client.get('/sales/clients/wizard/')
    print(f"Status code: {response.status_code}")
    print(f"Template usado: {response.template_name}")
    
    if response.status_code == 200:
        # Probar envío del paso 1
        response = client.post('/sales/clients/wizard/', {
            'client_type': 'individual',
            'step': '1'
        })
        print(f"POST paso 1 - Status code: {response.status_code}")
        print(f"Redirect URL: {response.url if hasattr(response, 'url') else 'No redirect'}")
        
        if response.status_code == 302:
            # Probar paso 2
            print("\n--- Probando Paso 2 ---")
            response = client.get('/sales/clients/wizard/step/2/')
            print(f"Status code: {response.status_code}")
            print(f"Template usado: {response.template_name}")
            
            if response.status_code == 200:
                # Probar envío del paso 2
                response = client.post('/sales/clients/wizard/', {
                    'first_name': 'Juan',
                    'last_name': 'Pérez',
                    'document_number': '12345678',
                    'email': 'juan@example.com',
                    'phone': '123456789',
                    'step': '2'
                })
                print(f"POST paso 2 - Status code: {response.status_code}")
                print(f"Redirect URL: {response.url if hasattr(response, 'url') else 'No redirect'}")
    
    # Limpiar
    if created:
        user.delete()

if __name__ == '__main__':
    test_wizard() 