#!/usr/bin/env python
"""
Script para identificar exactamente dónde está la referencia a contact_create_by_client
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
from django.template.loader import render_to_string
from django.template import Template, Context
from sales.views import ClientListView
from sales.models import Client

def test_contact_create_error():
    """Prueba para identificar el error de contact_create_by_client"""
    print("=== Prueba de Error contact_create_by_client ===")
    
    # Crear un cliente de prueba
    client = Client()
    
    # Simular un request
    from django.test import RequestFactory
    factory = RequestFactory()
    request = factory.get('/sales/clients/')
    request.user = None  # No necesitamos usuario para esta prueba
    
    # Crear la vista
    view = ClientListView()
    view.request = request
    
    # Obtener el queryset primero
    try:
        view.object_list = view.get_queryset()
        print("✓ Queryset obtenido correctamente")
    except Exception as e:
        print(f"✗ Error al obtener queryset: {e}")
        return
    
    # Obtener el contexto
    try:
        context = view.get_context_data()
        print("✓ Contexto obtenido correctamente")
    except Exception as e:
        print(f"✗ Error al obtener contexto: {e}")
        return
    
    # Probar renderizar el template
    try:
        template_name = 'sales/clients/client_list.html'
        rendered = render_to_string(template_name, context)
        print("✓ Template renderizado correctamente")
    except Exception as e:
        print(f"✗ Error al renderizar template: {e}")
        print(f"  Error type: {type(e)}")
        if hasattr(e, '__traceback__'):
            import traceback
            traceback.print_exc()
        return
    
    # Buscar referencias en el template renderizado
    if 'contact_create_by_client' in rendered:
        print("✗ Se encontró 'contact_create_by_client' en el template renderizado")
        # Buscar la línea específica
        lines = rendered.split('\n')
        for i, line in enumerate(lines):
            if 'contact_create_by_client' in line:
                print(f"  Línea {i+1}: {line.strip()}")
    else:
        print("✓ No se encontró 'contact_create_by_client' en el template renderizado")

if __name__ == '__main__':
    test_contact_create_error() 