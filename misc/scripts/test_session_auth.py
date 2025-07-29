#!/usr/bin/env python3
"""
Script para probar la autenticación usando el sistema de sesión personalizado.
"""
import os
import sys
from pathlib import Path

# Agregar el directorio del proyecto al path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

# En el contenedor Docker, el proyecto está en /app
if os.path.exists('/app'):
    sys.path.append('/app')

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
import django
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()

def test_session_auth():
    """Prueba la autenticación usando el sistema de sesión personalizado."""
    print("=== Probando Autenticación con Sesión Personalizada ===")
    
    # Obtener el usuario
    try:
        user = User.objects.get(email='admin@example.com')
        print(f"✅ Usuario encontrado: {user.email}")
        print(f"   - UID: {user.uid}")
        print(f"   - Roles: {[r.nombre for r in user.roles.all()]}")
    except User.DoesNotExist:
        print("❌ Usuario no encontrado")
        return
    
    # Crear cliente
    client = Client()
    
    # Configurar la sesión personalizada
    session_data = {
        'user': {
            'uid': user.uid,
            'email': user.email,
            'idioma': 'es'
        }
    }
    
    # Crear sesión
    session = client.session
    session.update(session_data)
    session.save()
    
    print(f"✅ Sesión configurada: {session_data}")
    
    # Probar URLs
    urls_to_test = [
        ('/tiendanube-adminet/', 'Dashboard'),
        ('/tiendanube-adminet/customers/', 'Customers'),
        ('/tiendanube-adminet/logs/', 'Logs'),
        ('/tiendanube-adminet/config/tiendanube/', 'Tiendanube Config'),
        ('/tiendanube-adminet/config/adminet/', 'Adminet Config'),
    ]
    
    print("\n=== Probando URLs con Sesión Personalizada ===")
    for url, name in urls_to_test:
        try:
            response = client.get(url)
            print(f"{name}: Status {response.status_code}")
            
            if response.status_code == 302:
                print(f"  → Redirect: {response.headers.get('Location', 'N/A')}")
            elif response.status_code == 200:
                print(f"  → Content length: {len(response.content)}")
                print(f"  → Template: {getattr(response, 'template_name', 'N/A')}")
            
        except Exception as e:
            print(f"{name}: Error - {e}")

if __name__ == "__main__":
    test_session_auth() 