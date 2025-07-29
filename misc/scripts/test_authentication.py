#!/usr/bin/env python3
"""
Script para probar la autenticación en detalle.
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
from django.urls import reverse
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from tiendanube_administranet.models import CustomerMapping

User = get_user_model()

def test_authentication():
    """Prueba la autenticación en detalle."""
    print("=== Probando Autenticación ===")
    
    # Obtener el usuario
    try:
        user = User.objects.get(email='admin@example.com')
        print(f"✅ Usuario encontrado: {user.email}")
        print(f"   - Es superusuario: {user.is_superuser}")
        print(f"   - Es staff: {user.is_staff}")
        print(f"   - Es activo: {user.is_active}")
    except User.DoesNotExist:
        print("❌ Usuario no encontrado")
        return
    
    # Crear cliente y hacer login
    client = Client()
    login_success = client.force_login(user)
    print(f"✅ Login forzado: {login_success}")
    
    # Verificar si el usuario está autenticado
    print(f"✅ Usuario autenticado: {client.session.get('_auth_user_id')}")
    
    # Probar diferentes URLs
    urls_to_test = [
        ('/tiendanube-adminet/', 'Dashboard'),
        ('/tiendanube-adminet/customers/', 'Customers'),
        ('/tiendanube-adminet/logs/', 'Logs'),
        ('/tiendanube-adminet/config/tiendanube/', 'Tiendanube Config'),
        ('/tiendanube-adminet/config/adminet/', 'Adminet Config'),
    ]
    
    print("\n=== Probando URLs ===")
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
    
    # Probar con follow=True
    print("\n=== Probando con follow=True ===")
    for url, name in urls_to_test[:3]:  # Solo las primeras 3
        try:
            response = client.get(url, follow=True)
            print(f"{name}: Final Status {response.status_code}")
            print(f"  → Redirect chain: {len(response.redirect_chain)} redirects")
            
        except Exception as e:
            print(f"{name}: Error - {e}")

def test_permissions():
    """Prueba los permisos específicos."""
    print("\n=== Probando Permisos ===")
    
    # Obtener permisos de la app
    ct = ContentType.objects.get_for_model(CustomerMapping)
    permissions = Permission.objects.filter(content_type=ct)
    
    print("Permisos disponibles:")
    for perm in permissions:
        print(f"  - {perm.codename}: {perm.name}")
    
    # Verificar permisos del usuario
    user = User.objects.get(email='admin@example.com')
    print(f"\nPermisos del usuario {user.email}:")
    user_perms = user.user_permissions.all()
    if user_perms:
        for perm in user_perms:
            print(f"  - {perm.codename}: {perm.name}")
    else:
        print("  - No tiene permisos específicos asignados")
        print("  - Como superusuario, tiene todos los permisos")

def test_middleware():
    """Prueba si hay middleware interfiriendo."""
    print("\n=== Probando Middleware ===")
    
    from django.conf import settings
    print("Middleware configurado:")
    for middleware in settings.MIDDLEWARE:
        print(f"  - {middleware}")

if __name__ == "__main__":
    test_authentication()
    test_permissions()
    test_middleware() 