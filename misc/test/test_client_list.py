#!/usr/bin/env python
"""
Script de prueba para verificar el template de lista de clientes
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
sys.path.append('/app')
django.setup()

from sales.models import Client
from sales.views import ClientListView
from django.test import RequestFactory
from django.contrib.auth import get_user_model

User = get_user_model()

def test_client_list_view():
    """Probar la vista de lista de clientes"""
    print("=== Prueba de Vista de Lista de Clientes ===")
    
    # Verificar que hay clientes
    total_clients = Client.objects.count()
    print(f"Total de clientes en BD: {total_clients}")
    
    if total_clients == 0:
        print("❌ No hay clientes en la base de datos")
        return False
    
    # Mostrar algunos clientes
    print("\nPrimeros 5 clientes:")
    for client in Client.objects.all()[:5]:
        print(f"- {client.name} ({client.type}) - Activo: {client.is_active}")
    
    # Crear un usuario de prueba para la vista
    try:
        user = User.objects.first()
        if not user:
            print("❌ No hay usuarios en la base de datos")
            return False
    except Exception as e:
        print(f"❌ Error al obtener usuario: {e}")
        return False
    
    # Probar la vista
    try:
        factory = RequestFactory()
        request = factory.get('/sales/clients/')
        request.user = user
        
        view = ClientListView()
        view.request = request
        view.kwargs = {}
        
        # Obtener el queryset
        queryset = view.get_queryset()
        print(f"\nQueryset obtenido: {queryset.count()} clientes")
        
        # Configurar object_list
        view.object_list = queryset
        
        # Obtener el contexto
        context = view.get_context_data()
        print(f"Contexto obtenido con {len(context.get('clients', []))} clientes")
        
        # Verificar estadísticas
        print(f"Total: {context.get('total_clients')}")
        print(f"Activos: {context.get('active_clients')}")
        print(f"Clientes: {context.get('customer_clients')}")
        
        print("✅ Vista funcionando correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error en la vista: {e}")
        return False

def test_json_response():
    """Probar la respuesta JSON"""
    print("\n=== Prueba de Respuesta JSON ===")
    
    try:
        user = User.objects.first()
        factory = RequestFactory()
        request = factory.get('/sales/clients/?format=json')
        request.user = user
        
        view = ClientListView()
        view.request = request
        view.kwargs = {}
        
        # Obtener el queryset y configurar object_list
        queryset = view.get_queryset()
        view.object_list = queryset
        
        # Obtener el contexto
        context = view.get_context_data()
        
        # Probar render_to_response
        response = view.render_to_response(context)
        
        if response.status_code == 200:
            print("✅ Respuesta JSON funcionando")
            return True
        else:
            print(f"❌ Error en respuesta JSON: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error en respuesta JSON: {e}")
        return False

if __name__ == "__main__":
    print("Iniciando pruebas de lista de clientes...")
    
    success1 = test_client_list_view()
    success2 = test_json_response()
    
    if success1 and success2:
        print("\n🎉 Todas las pruebas pasaron correctamente!")
    else:
        print("\n❌ Algunas pruebas fallaron")
        sys.exit(1) 