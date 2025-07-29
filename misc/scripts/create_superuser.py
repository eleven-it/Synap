#!/usr/bin/env python3
"""
Script para crear un superusuario para testing.
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

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

User = get_user_model()

def create_superuser():
    """Crea un superusuario para testing."""
    email = 'admin@example.com'
    password = 'admin123'
    
    # Verificar si el usuario ya existe
    if User.objects.filter(email=email).exists():
        print(f"✅ Usuario '{email}' ya existe")
        return
    
    # Crear el superusuario
    user = User.objects.create(
        email=email,
        password=make_password(password),
        is_staff=True,
        is_superuser=True,
        is_active=True
    )
    
    print(f"✅ Superusuario creado exitosamente:")
    print(f"   Email: {email}")
    print(f"   Contraseña: {password}")
    print(f"   ID: {user.id}")

if __name__ == "__main__":
    create_superuser() 